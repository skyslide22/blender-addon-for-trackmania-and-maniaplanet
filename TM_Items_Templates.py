import bpy
import os.path
import re
import math
from bpy.props import EnumProperty
from bpy.types import (
    Panel,
    Operator,
)
from .TM_Functions      import *
from .TM_Materials      import * 
from .TM_Items_Import   import *



class TM_OT_Items_Cars_Import(Operator):
    """import a dummy car for checkpoint spawn use..."""
    bl_idname = "view3d.tm_importwaypointspawnhelper"
    bl_description = "Execute Order 66"
    bl_icon = 'MATERIAL'
    bl_label = "Car Spawns"
    bl_options = {"REGISTER", "UNDO"} #without, ctrl+Z == crash

    cars: EnumProperty(items=[
        ("CAR_StadiumCar_Lowpoly",  "Stadium Car",  "", "AUTO", 0),
        ("CAR_CanyonCar_Lowpoly",   "Canyon Car",   "", "AUTO", 1),
        ("CAR_ValleyCar_Lowpoly",   "Valley Car",   "", "AUTO", 2),
        ("CAR_LagoonCar_Lowpoly",   "Lagoon Car",   "", "AUTO", 3),
    ])

    def execute(self, context):
        car     = self.properties.cars
        carPath = f"""{getAddonPath()}assets/item_cars/{car}.fbx"""
        deselectAll()
        
        bpy.ops.import_scene.fbx(
            filepath=carPath 
        )

        for obj in bpy.context.selected_objects:
            if "_car_" in obj.name.lower():
                obj.location = getCursorLocation()


        return {"FINISHED"}
        

    @staticmethod
    def addMenuPoint_CAR_SPAWN(self, context):
        layout = self.layout
        layout.operator_menu_enum("view3d.tm_importwaypointspawnhelper", "cars", icon="AUTO")








class TM_OT_Items_Envi_Template_Import(Operator):
    """import a template for an environment, for example a StadiumPlatform object with proper materials"""
    bl_idname = "view3d.tm_importenvitemplate"
    bl_description = "Execute Order 66"
    bl_icon = 'MATERIAL'
    bl_label = "Envi Templates"
    bl_options = {"REGISTER", "UNDO"} #without, ctrl+Z == crash

    enviTemplates: EnumProperty(items=[
        ("VANILLA_Platform_Stadium",  "Platform: Stadium", "", "CUBE", 0),
        ("VANILLA_Platform_Canyon",   "Platform: Canyon",  "", "CUBE", 1),
        ("VANILLA_Platform_Valley",   "Platform: Valley",  "", "CUBE", 2),
        ("VANILLA_Platform_Lagoon",   "Platform: Lagoon",  "", "CUBE", 3),
    ])

    def execute(self, context):
        envi    = self.properties.enviTemplates
        template= f"""{getAddonPath()}assets/item_vanilla_platforms/{envi}.fbx"""
        deselectAll()

        abspath = template
        relpath = f"Templates/{envi}"
        name    = envi
        
        filepath_list= [
            (name, abspath, relpath)
        ]
        importFBXfilesMain(filepath_list=filepath_list)
        return {"FINISHED"}
        

    @staticmethod
    def addMenuPoint_ENVI_TEMPLATE(self, context):
        layout = self.layout
        layout.operator_menu_enum("view3d.tm_importenvitemplate", "enviTemplates", icon="CUBE")