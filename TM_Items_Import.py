import bpy
import os.path
from bpy.types import (
    Panel,
    Operator,
    AddonPreferences,
    PropertyGroup,
    OperatorFileListElement
)
from bpy_extras.io_utils import ImportHelper
from bpy.props import CollectionProperty



from .TM_Functions      import *
from .TM_Items_Convert  import *
from .TM_Items_XML      import *
from .TM_Items_UVMaps   import *
from .TM_Settings       import *
from .TM_Items_Icon     import *
from .TM_Materials      import *





class TM_OT_Items_ClearMatImportFailList(Operator):
    """import fbx files"""
    bl_idname = "view3d.tm_clearmatimportfails"
    bl_description = "Execute Order 66"
    bl_icon = 'MATERIAL'
    bl_label = "Clear failed material import list"

    def execute(self, context):
        context.scene.tm_props.LI_importMatFailed = ""
        return {"FINISHED"}


class TM_OT_Items_Import(Operator):
    """import fbx files"""
    bl_idname = "view3d.tm_importfbx"
    bl_description = "Execute Order 66"
    bl_icon = 'MATERIAL'
    bl_label = "Import FBX files"
    bl_options = {"UNDO"}

    #https://docs.blender.org/api/current/bpy.types.FileSelectParams.html
    #‘filepath’, ‘filename’, ‘directory’ and a ‘files’
    directory:  StringProperty()
    filename:   StringProperty()
    filepath:   StringProperty()
    files:      CollectionProperty(type=OperatorFileListElement)
    filter_glob: StringProperty(default='*.fbx', options={'HIDDEN'})
        
    def execute(self, context):
        if saveBlendFile():
            importFBXfilesMain(self)
        else:
            makeReportPopup("FILE NOT SAVED!", ["Save your blend file!"], "ERROR")
        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
        

class TM_PT_Items_Import(Panel):
    # region bl_
    """Creates a Panel in the Object properties window"""
    bl_label = "Import FBX"
    bl_idname = "TM_PT_Items_Import"
    locals().update( panelClassDefaultProps )

    # endregion
    def draw(self, context):

        layout = self.layout
        tm_props  = context.scene.tm_props
        action    = tm_props.LI_importType
        recursive = tm_props.CB_importFolderRecursive
        failedMats= tm_props.LI_importMatFailed

        if requireValidNadeoINI(self) is False: return

        row = layout.row(align=True)
        row.prop(tm_props, "LI_importType",            expand=False, text="Type", )
        row.prop(tm_props, "CB_importFolderRecursive", expand=False, text="",    icon="FOLDER_REDIRECT")


        btnText = "Import Files" if action == "FILES" else "Import Folder & Subfolders" if recursive else "Import Folder"
        row=layout.row()
        row.scale_y = 1.5
        row.operator("view3d.tm_importfbx", text=btnText, icon="IMPORT")


        if failedMats:
            layout.separator(factor=UI_SPACER_FACTOR)
            
            row = layout.row()
            row.alert = True
            row.operator("view3d.tm_clearmatimportfails", text="OK, clear list")
            
            layout.label(text="Invalid imported materials:")
            for matName in failedMats.split(";;;"): 
                row=layout.row()
                row.alert = True
                row.label(text=matName)
        








def importFBXfilesMain(self=None, filepath_list=None, recursive=False) -> None:
    """main func for fbx import"""
    tm_props    = bpy.context.scene.tm_props
    action      = tm_props.LI_importType
    recursive   = recursive or tm_props.CB_importFolderRecursive
    fileList    = [] #name, relpath, abspath
    invalidMats = []
    importedCols= []
    importedColRows = {}

    if filepath_list:
        fileList = filepath_list

    elif action == "FILES":        
        folder= self.directory
        files = self.files

        for file in files:
            isInWorkItems = "Work/Items" in fixSlash(folder) 
            name   = file.name
            abspath= fixSlash(os.path.join(folder, name))
            relpath= abspath.split("Work/Items/")[-1] if isInWorkItems else f"imported/{name}"
            fileList.append((
                name,
                abspath,
                relpath
            ))
    
    #FOLDERS
    else:
        folder  = self.directory
        files   = getFilesOfFolder(path=folder, recursive=recursive, ext="fbx")
        
        for file in files:
            isInWorkItems = "Work/Items" in fixSlash(file) 
            name    = getFilenameOfPath(file)
            abspath = fixSlash(file)
            relpath = abspath.split("Work/Items/")[-1] if isInWorkItems else f"imported/{name}"
            fileList.append((
                name,
                abspath,
                relpath
            ))

    for file in fileList:
        name, abspath, relpath = file
        relpath = fixSlash(relpath).split("/")
        
        deselectAll()
        setMasterCollectionAsActive()
        importFBXFile(filepath=abspath)
        
        acol = getActiveCollection()
        objs = bpy.context.selected_objects
        mats = bpy.data.materials

        waypoint       = getWaypointTypeOfFBXfile(abspath)
        waypoint_color = None
        if waypoint is not None:
            waypoint = waypoint.upper()
            if waypoint == "CHECKPOINT":    waypoint_color = COLOR_CHECKPOINT
            if waypoint == "START":         waypoint_color = COLOR_START
            if waypoint == "FINISH":        waypoint_color = COLOR_FINISH
            if waypoint == "STARTFINISH":   waypoint_color = COLOR_STARTFINISH
        
        #remove ext..
        filecol = relpath[-1]
        filecol = re.sub(r"\.\w+$", "", filecol, re.IGNORECASE)
        relpath[-1] = filecol

        col  = createCollectionHierachy(relpath)
        importedCols.append(col)
        
        #each path is a list with cols
        col_path = "/".join(relpath[:-1])
        if col_path not in importedColRows:
            importedColRows[ col_path ] = []
            importedColRows[ col_path ].append(col)
        else:
            importedColRows[ col_path ].append(col)
            
        
        

        if waypoint_color is not None:
            col.color_tag = waypoint_color


        for obj in objs:
            
            if "delete" in obj.name.lower():
                deleteObj(obj)
                continue

            acol.objects.unlink(obj)
            col .objects.link(obj)

            for slot in obj.material_slots:
                mat    = slot.material
                if mat is None: continue

                #mat has .001
                regex = r"\.\d+$"
                if re.search(regex, mat.name):
                    noCountName = re.sub(regex, "", mat.name, re.IGNORECASE)
                    if noCountName in mats:
                        slot.material = mats[ noCountName ]
                        del mat
                        continue

                fixMat = assignMatJSONpropsToMat(mat=mat)
                debug(f"Importing <{mat.name}> successfully: {fixMat}")
                if fixMat is False and mat not in invalidMats:
                    invalidMats.append(mat)
            
            fixMaterialNames(obj)
                    

    matNames = []
    for mat in invalidMats:
        try: 
            matName = mat.name
            matNames.append(matName)
        except ReferenceError:
            pass

    tm_props.LI_importMatFailed = ";;;".join(matNames)
    alignCollectionsInRows(importedColRows)




def alignCollectionsInRows(col_dict):
    """align collection in x axis with gap, new folder, new row(y)"""
    BLOCK_SIZE      = 32
    BLOCK_SIZE_MAX  = BLOCK_SIZE * 64

    pos_x_current    = 0
    pos_y_current    = 0
    pos_y_current_max= 0

    for path in col_dict:

        cols  = col_dict[path]
        for col in cols:
            
            dim_x,\
            dim_y,\
            dim_z = getDimensionOfCollection(col)

            #round obj dim to clostest 32^x
            pos_x = roundInterval(dim_x, BLOCK_SIZE) + BLOCK_SIZE
            pos_y = roundInterval(dim_y, BLOCK_SIZE) + BLOCK_SIZE

            pos_y_current_max = max(
                pos_y, 
                pos_y_current_max
            )

            #move objs to x and y
            for obj in col.all_objects:
                obj.location[0] += pos_x_current
                obj.location[1] += pos_y_current

            pos_x_current += pos_x

        #next row start Y is:
        pos_y_current    += pos_y_current_max
        pos_x_current     = 0
        pos_y_current_max = 0

        

    



def importFBXFile(filepath):
    bpy.ops.import_scene.fbx(
        filepath=filepath,
        use_custom_props=True
    )