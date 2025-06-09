import numpy as np
import traceback
from PIL import Image
from noise import pnoise2  # Perlin noise
from scipy.ndimage import gaussian_filter

from marching_cubes import marching_cubes  

def generate_terrain(height, noise_type, seed, res_str, texture_path=None):
    resolution_map = {
        "Low (32x32)": 32,
        "Medium (64x64)": 64,
        "High (128x128)": 128
    }
    resolution = resolution_map[res_str]
    np.random.seed(seed)

    if texture_path and texture_path.strip() != "":
        heightmap = load_heightmap_from_texture(texture_path, resolution)
    else:
        heightmap = generate_noise_map(resolution, noise_type, seed)

    # Normalize heightmap
    heightmap = heightmap / np.max(heightmap) * height

    # Create a 3D scalar field for marching cubes
    scalar_field = heightmap_to_scalar_field(heightmap)
    print(f"Scalar field min: {scalar_field.min()}, max: {scalar_field.max()}")

    # Define voxel and bounding box parameters
    voxel_size = 0.5
    bbox_min = [0.0, 0.0, 0.0]
    iso_value = 0

    print(">>> Starting Marching Cubes for terrain")
    try:
        terrain_mesh = marching_cubes(scalar_field, bbox_min, voxel_size, iso_value)
    except Exception as e:
        print('failed', e)
        traceback.print_exc()

# ============================= UTILITY FUNCS =============================

def generate_noise_map(res, noise_type, seed):
    print(f">>> Generating {noise_type} noise map at {res}x{res}")
    scale = 10.0
    noise_map = np.zeros((res, res), dtype=np.float32)
    for x in range(res):
        for y in range(res):
            nx = x / res
            ny = y / res
            if noise_type == "Perlin":
                noise_val = pnoise2(nx * scale, ny * scale, octaves=4, base=seed)
            else:
                noise_val = np.random.rand()  
            noise_map[x][y] = noise_val
    # Normalize 
    noise_map = (noise_map - np.min(noise_map)) / (np.max(noise_map) - np.min(noise_map))

    noise_map = gaussian_filter(noise_map, sigma=1.0)
    return noise_map

def load_heightmap_from_texture(path, target_res):
    print(f">>> Loading texture: {path}")
    image = Image.open(path).convert("L")  # Greyscale
    image = image.resize((target_res, target_res))
    heightmap = np.array(image, dtype=np.float32)

    # Normalize and apply gaussian blur for smoothing
    heightmap = heightmap / 255.0
    heightmap = gaussian_filter(heightmap, sigma=1.0)
    return heightmap

def heightmap_to_scalar_field(heightmap, resolution_y = 64):
    res_x, res_z = heightmap.shape
    scalar_field = np.zeros((res_x, resolution_y, res_z), dtype=np.float32)
    
    for x in range(res_x):
        for z in range(res_z):
            terrain_height = heightmap[x][z]
            for y in range(resolution_y):
                norm_y = y / resolution_y
                scalar_field[x][y][z] = terrain_height - norm_y # signed distance formula

    return scalar_field