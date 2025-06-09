from maya import cmds
import generate_terrain

class GUI_Window(object):
    # ========================================== Constructor Start
    def __init__(self):
        self.window = "TerrainUI"
        self.title = "Terrain Generator"
        self.size = (400, 500)
    
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window, window=True)

        self.window = cmds.window(self.window, title=self.title, widthHeight=self.size)
        
        cmds.columnLayout(adjustableColumn=True, rowSpacing=10, columnAlign="center")
        cmds.text(label="Terain Generator", align="center", h=20)
        cmds.separator(h=10)

        self.heightIntensity = cmds.floatSliderGrp( 
            label="Height Intensity", 
            field=True, 
            minValue=0.1, maxValue=10.0, 
            value=2.5)
        cmds.text(label="Noise Type")
        self.noiseType = cmds.optionMenu()
        cmds.menuItem(label="Perlin")
        cmds.menuItem(label="Simplex")

        self.seedField = cmds.intFieldGrp(label="Random Seed", value1=42)


        self.textureField = cmds.textFieldButtonGrp(
            label="Custom Heightmap",
            buttonLabel="Browse",
            buttonCommand=self.load_texture
        )
        cmds.text(label="(Leave blank to use noise + seed)", align="center", height=20)

        # Resolution selector
        cmds.text(label="Resolution")
        self.resolution = cmds.optionMenu()
        cmds.menuItem(label="Low (32x32)")
        cmds.menuItem(label="Medium (64x64)")
        cmds.menuItem(label="High (128x128)")

        cmds.separator(h=10)

        self.generateBtn = cmds.button(label="Generate Terrain", height=40, command=self.generate_terrain_ui)

        cmds.button(label="Clear Terrain", height=30, command=self.clear_terrain)

        cmds.showWindow(self.window)
    # ========================================== Constructor End

    def load_texture(self, *args):
        texture_path = cmds.fileDialog2(fileMode=1, caption="Select Heightmap Image")
        if texture_path:
            cmds.textFieldButtonGrp(self.textureField, edit=True, text=texture_path[0])

    def generate_terrain_ui(self, *args):
        height = cmds.floatSliderGrp(self.heightIntensity, query=True, value=True)
        noise = cmds.optionMenu(self.noiseType, query=True, value=True)
        seed = cmds.intFieldGrp(self.seedField, query=True, value1=True)
        res = cmds.optionMenu(self.resolution, query=True, value=True)
        texture = cmds.textFieldButtonGrp(self.textureField, query=True, text=True)

        print(f"Generating terrain: height={height}, noise_type={noise}, seed={seed}, res={res}, texture={texture}")

        generate_terrain.generate_terrain(
            height=height,
            noise_type=noise,
            seed=seed,
            res_str=res,
            texture_path=texture if texture.strip() != "" else None
        )
    
    def clear_terrain(self, *args):
        meshes = cmds.ls("terrain_mesh*", type="mesh")
        for mesh in meshes:
            parent = cmds.listRelatives(mesh, parent=True)
            if parent:
                cmds.delete(parent)

terrain_window = GUI_Window()