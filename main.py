import sys
import os
import maya.cmds as cmds

project_root = cmds.workspace(q=True, rootDirectory=True)

scripts_dir = os.path.join(project_root, "scripts")

if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

import gui
    
def run_ui():
    gui_window = gui.GUI_Window() # create instance of GUI_Window

run_ui()