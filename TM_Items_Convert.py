from sys import path
import bpy
import os.path
import re
import subprocess
from threading import Thread
import xml.etree.ElementTree as ET
from .TM_Functions import *


class CONVERT_ITEM(Thread):
    
    def __init__(self, fbxfilepath: str, game: str) -> None:
        super(CONVERT_ITEM, self).__init__() #need to call init from Thread, otherwise error
        self.fbxfilepath    = fixSlash( fbxfilepath ) 
        self.fbxfilepathREL = "Items/" + fbxfilepath.split("/Work/Items/")[-1] 
        self.convertIsDone  = False
        self.convertFailed  = False
        self.meshInfos = None   #error or success msg of mesh/shape.gbx
        self.itemInfos = None   #error or success msg of item.gbx
        self.itemRcode = 0      #0 good, 1 and above bad
        self.meshRcode = 0      #0 good, 1 and above bad
        self.name      = self.fbxfilepath.split("/")[-1]
        self.nameRAW   = self.name.replace(".fbx", "")
        self.progress  = []
        self.game      = game

        self.meshparamsXMLFilepath  = self.fbxfilepath.replace(".fbx", ".MeshParams.xml")
        self.itemXMLFilepath        = self.fbxfilepath.replace(".fbx", ".Item.xml")
        self.itemXMLFilepathREL     = self.fbxfilepathREL.replace(".fbx", ".Item.xml")
        
        self.gbxfilepath         = self.fbxfilepath.replace("/Work/Items/", "/Items/")
        self.meshGBXFilepath     = self.gbxfilepath.replace(".fbx", ".Mesh.gbx")
        self.itemGBXFilepath     = self.gbxfilepath.replace(".fbx", ".Item.gbx")
        self.shapeGBXFilepath    = self.gbxfilepath.replace(".fbx", ".Shape.gbx")
        self.shapeGBXFilepathOLD = self.gbxfilepath.replace(".fbx", ".Shape.gbx.old")
        
        
    
    def run(self) -> None:
        """method called when method start() is called on an instance of this class"""

        self.progress.append(f"""Start convert of <{self.fbxfilepath}> for {self.game}""")

        if isGameTypeManiaPlanet():
            self.convertMeshAndShapeGBX()
            if not self.convertFailed:    self.hackShapeGBX(action="MAKE_OLD") #rename shape.gbx += .old
            #convert again but replace "BaseMaterial" with "Link" in meshparams.xml of each item
            if not self.convertFailed:    self.convertMeshAndShapeGBX()
            if not self.convertFailed:    self.hackShapeGBX(action="USE_OLD") #delte current shape.gbx, rename shape.gbx.old (-old)
            
        if not self.convertFailed:    self.convertItemGBX() #tm2020 only needs one convert
        if not self.convertFailed:    self.progress.append(f"Convert of <{self.nameRAW}> successfully")
        if     self.convertFailed:    self.progress.append(f"Convert of <{self.nameRAW}> failed")
               
        updateConvertStatusNumbers(result=not self.convertFailed, objname=self.name)


    

    def convertMeshAndShapeGBX(self) -> None:
        """convert fbx to shape/mesh.gbx"""
        self.progress.append(f"""Convert <{self.nameRAW}.Mesh and Shape.gbx>""")
        
        cmd = f"{getNadeoImporterPath()} Mesh {self.fbxfilepathREL}" # ex: NadeoImporter.exe Mesh /Items/myblock.fbx
        convertProcess  = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        mesh_output     = convertProcess.communicate()  # is blocking, => blender not frozen cuz this func runs in a new thread
        mesh_returncode = convertProcess.returncode
        convertProcess.wait()
        
        self.meshInfos = str(mesh_output[0])
        self.meshRcode = mesh_returncode
        self.convertFailed = True if mesh_returncode > 0 else False
        self.progress.append(f"""Convert <{self.nameRAW}.Mesh and Shape.gbx> {"failed" if self.convertFailed else "success"}""")

    
    
    def convertItemGBX(self) -> None:
        """convert fbx to item.gbx"""
        self.progress.append(f"Convert <{self.nameRAW}>.Item.gbx")
        
        cmd = f"{getNadeoImporterPath()} Item {self.itemXMLFilepathREL}" # ex: NadeoImporter.exe Mesh /Items/myblock.fbx
        debug(cmd)
        convertProcess  = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        item_output     = convertProcess.communicate()  # is blocking, => blender not frozen cuz this func runs in a new thread
        item_returncode = convertProcess.returncode
        convertProcess.wait()

        self.itemInfos = str(item_output[0])
        self.itemRcode = item_returncode
        self.convertFailed = True if item_returncode > 0 else False
        self.progress.append(f"""Convert <{self.nameRAW}>.Item.gbx {"failed" if self.convertFailed else "success"}""")

    
    
    def hackShapeGBX(self, action: str="MAKE_OLD" or "USE_OLD") -> None:
        """hack the shape.gbx of the given filename, call this function 2 times!
            --- 1st call: action='MAKE_OLD', this will rename the shape.gbx to shape.gbx.old
                and change meshParams.xml.
            --- 2nd call: action='USE_OLD',  replace shape.gbx with shape.gbx.old
        """
        
        #create shape.gbx.old file, should be used in first call
        if action == "MAKE_OLD":
            
            self.progress.append(f"Hacking <{self.nameRAW}.Shape.gbx>, rename to <{self.nameRAW}.Shape.gbx.old>")
            
            if doesFileExist(self.shapeGBXFilepathOLD):
                os.remove(self.shapeGBXFilepathOLD)
            
            try:
                os.rename(
                self.shapeGBXFilepath,
                self.shapeGBXFilepathOLD
                )
                self.progress.append(f"Hacking <{self.nameRAW}.Shape.gbx> success")

            except FileNotFoundError:
                self.progress.append(f"Hacking <{self.nameRAW}.Shape.gbx> failed, file not found")
            
            
            self.progress.append(f"Parsing <{self.nameRAW}.Item.xml>")
            tree = ET.parse(self.meshparamsXMLFilepath)
            root = tree.getroot()
            data = root.findall(".Materials/Material")
            for mat in data:
                if "BaseTexture" in mat.attrib:
                    if not "/" in mat.get("BaseTexture", ""):
                        mat.set("Link", mat.get("BaseTexture"))
                        del mat.attrib["BaseTexture"]
                        del mat.attrib["Model"]
                        del mat.attrib["PhysicsId"]

            # xmlstr = ET.tostring(root, encoding='utf8', method='xml')
            # pro__print(xmlstr)
                        
            self.progress.append(f"Write changes to <{self.nameRAW}.Item.xml>")
            tree.write(self.meshparamsXMLFilepath)


        
        #replace shape.gbx with shape.old.gbx
        if action == "USE_OLD":
            
            self.progress.append(f"Hacking <{self.nameRAW}.Shape.gbx>, replace with <{self.nameRAW}.Shape.gbx.old>")
        
            try:    os.remove(self.shapeGBXFilepath)
            except: pass #doesn't work sometimes, for some unknown reason..

            try:
                os.rename(
                    self.shapeGBXFilepathOLD,
                    self.shapeGBXFilepath
                )
                self.progress.append(f"Hacking <{self.nameRAW}.Shape.gbx> success")

            except FileNotFoundError:
                self.progress.append(f"Hacking <{self.nameRAW}.Shape.gbx> failed, file not found")
        
        


        

def updateConvertStatusNumbers(result: bool, objname: str) -> None:
    """updates the numbers for converting which are displaed in the ui panel"""
    tm_props = bpy.context.scene.tm_props

    if result:
        tm_props.NU_convertedSuccess += 1
    
    else:       
        tm_props.NU_convertedError += 1
        tm_props.ST_convertedErrorList += f"%%%{objname}"

    tm_props.NU_convertedRaw += 1
    tm_props.NU_converted     = tm_props.NU_convertedRaw / tm_props.NU_convertCount * 100

        
        


def startBatchConvert(fbxfilepaths: list) -> None:
    """convert each fbx one after one, create a new thread for it"""
    tm_props = bpy.context.scene.tm_props
    results  = []
    fails    = tm_props.NU_convertedError
    report   = tm_props.CB_notifyPopupWhenDone

    tm_props.CB_showConvertPanel = True
    game = "ManiaPlanet" if isGameTypeManiaPlanet() else "TrackMania2020"

    for fbx in fbxfilepaths:
        convertTheFBX = CONVERT_ITEM(fbxfilepath=fbx[0], game=game)
        convertTheFBX.start() #start the convert (call internal run())
        convertTheFBX.join()  #waits until the thread terminated (function/convert is done..)
        
        results.append({
            "path":         convertTheFBX.fbxfilepathREL,
            "nameRAW":      convertTheFBX.nameRAW,
            "meshRcode":    convertTheFBX.meshRcode,
            "itemRcode":    convertTheFBX.itemRcode,
            "itemInfos":    convertTheFBX.itemInfos,
            "meshInfos":    convertTheFBX.meshInfos,
            "progress":     convertTheFBX.progress
        })
        
        for step in convertTheFBX.progress:
            debug(step)

        if tm_props.CB_stopAllNextConverts is True:
            debug("Convert stopped, aborted by user (UI CHECKBOX)")
            break

    tm_props.CB_converting = False
    writeConvertReport(results=results)
    
    if report:
        ...#not working yet -> appears in background...
        # makeWindowsReportPopup("Converting done", [f"fails: {fails}"])





def writeConvertReport(results: list) -> None:
    """genertate status html file of converted fbx files"""
    errors      = 0
    converted   = len(results)
    
    for result in results:
        if result["meshRcode"] > 0 or result["itemRcode"] > 0:
            errors += 1
    try:
        with open( fixSlash(PATH_CONVERT_REPORT), "w", encoding="utf-8") as f:
            
            resultList = ""
            for result in results:

                progressLIs = ""
                for progress in result["progress"]:
                    progress = progress.replace("<", "&lt;")
                    progress = progress.replace(">", "&gt;")
                    progressLIs += f"""<li class="">{progress}</li> """

                objName = result["path"]
                objName = objName.replace(result["nameRAW"], f"""<i>{result["nameRAW"]}</i>""")

                error_msg_mesh_pretty, \
                error_msg_mesh_original = beautifyError(result["meshInfos"]) if result["meshRcode"] > 0 else ("No Error", "No Error")
                
                error_msg_item_pretty,\
                error_msg_item_original = beautifyError(result["itemInfos"]) if result["itemRcode"] > 0 else ("No Error", "No Error")

                resultList += f"""
                    <li class="{"error" if result["meshRcode"] > 0 or result["itemRcode"] > 0 else "success"}">
                        <ul class="result-object">
                            <li class="item"><b>Item:</b> {objName}  </li>
                            <hr>
                            <li class="mesh-error"><b>Mesh Errors Pretty:</b> <br />{error_msg_mesh_pretty} </li>
                            <li class="mesh-error original"><b>Original NadeoImporter.exe response:</b> <br />{error_msg_mesh_original} </li>
                            <hr>
                            <li class="item-error"><b>Item Errors Pretty:</b> <br />{error_msg_item_pretty} </li>
                            <li class="item-error original"><b>Original NadeoImporter.exe response:</b> <br />{error_msg_item_original} </li>
                            <hr>
                            <li class="item-error"><b>Convert steps until convert failed:</b></li>
                            <ul class="progress-steps">
                                {progressLIs}
                            </ul>
                        </ul>    
                    </li>
                    """
            
            fullHTML = f"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Convert Report</title>
                    <link rel="stylesheet" href="file://{getAddonPath()}assets/report.css">
                </head>
                <body>
                    <header>
                        <div>
                            Failed converts: {errors} of {converted}
                        </div>
                    </header>
                    <ul id="result-list">
                    {resultList}           
                    </ul>
                </body>
                </html>
                """
            f.write(fullHTML)
        
    except FileNotFoundError as e:
        makeReportPopup(
            "Writing file failed", 
            [
                "Can not write report file on desktop",
                "Try to run Blender once as admindistator" 
            ])


        
        
def beautifyError(error: str):
    """proper description from nadeoimporter return string"""
    LMMissing       = "lightmap"
    BMMissing       = "basematerial"
    MatMissing      = "no material"
    noInfos         = ""
    missingUV       = "uvlayers"
    commonNotFound  = "common"
    itemXMLMissing  = "item.xml"       
    
    error = error.replace("(b'", "")
    error = error.replace("\\r",  "<br />")
    error = error.replace("\\n'", "<br />")
    error = error.replace("\\n",  "<br />")
    error = error.replace("\\",   "/")
    error = error.replace(", None)", "")
        
    prettymsg = ""
    if LMMissing        in error.lower(): prettymsg="Lightmap uv layer is missing"
    if BMMissing        in error.lower(): prettymsg="Basematerial uv layer is missing"
    if MatMissing       in error.lower(): prettymsg="No material found, use atleast 1"
    if LMMissing        in error.lower(): prettymsg="Not enough UvLayers, BaseMaterial/Lightmap missing?"
    if missingUV        in error.lower(): prettymsg="Not enough UvLayers, BaseMaterial/Lightmap/Decal missing?"
    if commonNotFound   in error.lower(): prettymsg="Collection COMMON not found, does meshParams.xml exist?"
    if itemXMLMissing   in error.lower(): prettymsg="Item.xml not found, does it exists?"
    if prettymsg == "":                   prettymsg=error 

    return prettymsg, error

    
    
    



















        
        
        
        