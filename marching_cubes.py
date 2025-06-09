import maya.cmds as cmds
import numpy as np
import maya.api.OpenMaya as om

from edge_and_tri_tables import edge_table, tri_table

# The 8 corner coordinate offset for the cube
CUBE_CORNERS = [
    [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
    [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]
]
# 12 edge pairs of the cube (start_index, end_index)
EDGE_VERTICES = [
    [0, 1], [1, 2], [2, 3], [3, 0],  # bottom square edges
    [4, 5], [5, 6], [6, 7], [7, 4],  # top square edges
    [0, 4], [1, 5], [2, 6], [3, 7]   # vertical edges
]

def marching_cubes(scalar_field, bbox_min, voxel_size, iso_value):
    triangles = []
    edge_vertex_cache = {}

    nx = len(scalar_field)
    ny = len(scalar_field[0])
    nz = len(scalar_field[0][0])

    for i in range(nx - 1):
        for j in range(ny -1):
            for k in range(nz - 1):
                # Sample cube corner values
                cube_values = []
                for corner in CUBE_CORNERS:
                    x = i + corner[0]
                    y = j + corner[1]
                    z = k + corner[2]
                    cube_values.append(scalar_field[x][y][z])
                print(f"Cube values at ({i}, {j}, {k}): {cube_values}")

                # Generate a bitmask that we can return to get a case
                cube_index = 0 # start with 00000000 mask

                for n, val in enumerate(cube_values):
                    if val > iso_value:
                        cube_index |= 1 << n # bitshift at position n in mask if value is greater than iso_value
                
                print(f"Evaluating cube_index: {cube_index}")
                
                # If we get 00000000 or 11111111 back - entirely outside or inside mesh - ignore
                if cube_index == 0 or cube_index == 255:
                    print(f"Skipping irrelivant cube_index: {cube_index}")
                    continue
                if cube_index < 0 or cube_index >= len(tri_table):
                    print(f"Invalid cube_index: {cube_index}")
                    continue

                cube_origin = [
                    bbox_min[0] + i * voxel_size,
                    bbox_min[1] + j * voxel_size,
                    bbox_min[2] + k * voxel_size
                ]

                # Interpolate vertices on edges
                vert_list = [None] * 12
                edge_flags = edge_table[cube_index]
                print(f"edge_flags for cube_index {cube_index}: {bin(edge_flags)}")

                for edge in range(12):
                    if edge_flags & (1 << edge): # check if is 'active' edge
                        v1_index, v2_index = EDGE_VERTICES[edge]
                        
                        # Avoiding issues with shared edges by sorting tuple - unique key per edge
                        edge_key = (i, j, k, edge)

                        if edge_key not in edge_vertex_cache:

                            p1 = [
                                cube_origin[0] + CUBE_CORNERS[v1_index][0] * voxel_size,
                                cube_origin[1] + CUBE_CORNERS[v1_index][1] * voxel_size,
                                cube_origin[2] + CUBE_CORNERS[v1_index][2] * voxel_size
                            ]
                            p2 = [
                                cube_origin[0] + CUBE_CORNERS[v2_index][0] * voxel_size,
                                cube_origin[1] + CUBE_CORNERS[v2_index][1] * voxel_size,
                                cube_origin[2] + CUBE_CORNERS[v2_index][2] * voxel_size
                            ]

                            val_p1 = cube_values[v1_index]
                            val_p2 = cube_values[v2_index]

                            # Scalar interpolation to the midpoint between the two voxels
                            t = (iso_value - val_p1) / (val_p2 - val_p1 + 1e-6)  # avoid dividing by 0 error
                            interp = [p1[m] + t * (p2[m] - p1[m]) for m in range(3)]

                            # Check for NaN values in result
                            if any(np.isnan(v) for v in interp):
                                print(f"Invalid interpolation at edge {edge}: {interp}")
                                edge_vertex_cache[edge_key] = None
                            else:
                                # Hold in cache if its a valid interpolated value
                                edge_vertex_cache[edge_key] = interp

                        # Finally, store vertex after interpolation
                        vert_list[edge] = edge_vertex_cache[edge_key]
                
                print("EDGES HAVE BEEN INTERPOLATED AND STORED")
                print(f"cube_index {cube_index} → tri_table entry: {tri_table[cube_index]}")

                # Create triangles from tri_table
                edge_indices = tri_table[cube_index]
                print(f"tri_table for cube_index {cube_index}: {edge_indices}")

                for t in range(0, 16, 3):
                    if edge_indices[t] == -1: # Break out of loop if -1 value
                        break
                    
                    tri = []
                    for n in range(3):
                        edge = edge_indices[t + n]
                        
                        if edge < 0 or edge >= len(vert_list):
                            print(f"Warning: edge index {edge} is out of bounds")
                            tri.append(None)
                        else:
                            v_pos = vert_list[edge]
                            if v_pos is None:
                                print(f"Warning: edge {edge} has no vertex, cannot create triangle")
                                tri.append(None)
                            else:
                                tri.append(v_pos)

                    # Only add a triangle if all vertices are valid & we have 3 verts
                    if len(tri) == 3 and all(v is not None for v in tri):
                        triangles.append(tri)
                    else:
                        print(f"Skipping triangle with invalid vertex data: {tri}")
                
    
    if triangles:
        return create_mesh_from_triangles(triangles)
    else:
        print("No triangles generated.")
        return None
    
def create_mesh_from_triangles(triangles, name="terrain_mesh"):
    mpoint_array = om.MPointArray()
    vertex_map = {} # maya doesnt like duplicate vertices - using this to store unique verts to index into

    face_counts = []
    face_connects = []
    
    # Loop through triangles and fill the lists
    for tri in triangles:
        face_counts.append(3)  # One triangle (always 3 vertices)
        tri_valid = True  # Flag to check if the triangle is valid
        face_indices = []

        for vert in tri:
            if vert is not None:  # Ensure vertex is valid
                try:
                    # Check if the vertex is valid and convert it into an MPoint
                    vert_key = tuple(round(c, 6) for c in vert) # rounding the floats help with duplication issues
                    # Unique key for storing vertex positions
                    if vert_key not in vertex_map:
                        x, y, z = map(float, vert)
                        index = len(mpoint_array)
                        mpoint_array.append(om.MPoint(x, y, z))
                        vertex_map[vert_key] = index

                    face_indices.insert(0, vertex_map[vert_key])

                except Exception as e:
                    print(f"Unexpected error processing vertex {vert}: {e}")
                    tri_valid = False  # Mark the triangle as invalid
                    break
            else:
                print(f"Warning: Invalid vertex {vert}. Skipping this triangle.")
                tri_valid = False  # Mark the triangle as invalid
                break
        
        # Skip invalid triangles if it doesnt pass checks
        if tri_valid and len(face_indices) == 3:
            face_connects.extend(face_indices)
        else:
            print(f"Skipping triangle with invalid data: {tri}")
            face_counts.pop() # remove face_count that was added for bad triangle

    # Check arrays are populated
    if not len(mpoint_array) or not len(face_counts) or not len(face_connects):
        print("Aborting mesh creation: mesh data is empty.")
        return None
    
    # Checking lengths match
    if sum(face_counts) != len(face_connects):
        print(f"Mismatch: face counts do not match face connects")
        return None
    
    # Convert face_counts to MIntArray for mesh creation
    m_face_counts = om.MIntArray([int(count) for count in face_counts])
    
    # Convert face_connects to MIntArray for mesh creation
    m_face_connects = om.MIntArray([int(conn) for conn in face_connects])

    # Debugging: Print sample of vertices, face counts, and face connects
    print("Preparing mesh...")
    print("Vertices:", mpoint_array.__len__())
    print("Faces:", face_counts.__len__())
    print("Connects:", face_connects.__len__())

    try:
        mesh_fn = om.MFnMesh()
        mesh_obj = mesh_fn.create(
            mpoint_array,             
            m_face_counts,
            m_face_connects
        )
        mesh_fn.setName(name)

        mesh_fn.updateSurface()

        # Add to scene with transform node
        dag_modifier = om.MDagModifier()
        transform = dag_modifier.createNode("transform")
        dag_modifier.renameNode(transform, f"{name}_transform")
        dag_modifier.reparentNode(mesh_obj, transform)
        dag_modifier.doIt()

        cmds.setAttr(f"{name}_transform.translate", -8, -32, -8, type="double3")

        shading_group = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=f"{name}_SG")
        shader = cmds.shadingNode("lambert", asShader=True, name=f"{name}_shader")
        cmds.connectAttr(f"{shader}.outColor", f"{shading_group}.surfaceShader", force=True)
        cmds.sets(name, e=True, forceElement=shading_group)

        return mesh_fn.name()

    except Exception as e:
        print("Mesh creation failed:", e)
        return None