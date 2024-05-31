import os
from PySide2 import QtCore, QtGui, QtWidgets

BASE_DIR = "E:/VISUALNOOBS_TD/Practica_2/anims/"

class CreateGifs:
    def __init__(self):
        """Initialize the CreateGifs class."""
        self.sv = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
        self.vp = self.sv.curViewport()
        self.output_path = f"{BASE_DIR}render/"
        grid = self.sv.referencePlane()
        grid.setIsVisible(False)

    def createFbx(self):
        """Create a geometry node and import an FBX file."""
        geo = hou.node('/obj').createNode('geo', 'GIF_geo')
        fbx_node = geo.createNode('kinefx::fbxcharacterimport', 'GIF_fbx_import')
        bone_deform = fbx_node.createOutputNode("bonedeform", "bonedeform")
        bone_deform.setInput(2, fbx_node, 2)
        bone_deform.createOutputNode("output")

    def topNet(self):
        """Create a top network to process FBX files and generate GIFs."""
        lista_nodos = hou.node('/obj').children()
        if hou.node('/obj/topnet_gif_gen') in lista_nodos:
            hou.node('/obj/topnet_gif_gen').destroy()
            topnet = hou.node('/obj').createNode('topnet', "topnet_gif_gen")
        else:
            topnet = hou.node('/obj').createNode('topnet', "topnet_gif_gen")

        hou.node('/obj/topnet_gif_gen/localscheduler').parm("maxprocsmenu").set(-1)
        wedge_node = topnet.createNode("wedge")
        wedge_node.move((0, -2))
        open_gl = wedge_node.createOutputNode("ropopengl", "ropopengl1")
        partition = open_gl.createOutputNode("partitionbyattribute")
        ffmpeg = partition.createOutputNode("ffmpegencodevideo", "ffmpegencodevideo1")
        wfa = ffmpeg.createOutputNode("waitforall")
        ps = wfa.createOutputNode("pythonscript")

        # Destroy all nodes after finishing script
        ps.parm("script").set('''
import hou

node = hou.pwd()
parent = node.parent().parent()

for n in parent.children():
    name = n.name()
    if name.startswith("GIF"):
        n.destroy()
''')

        ps.createOutputNode("output")

        # Change Wedge Node parameters
        wedge_node.parm("wedgeattributes").set(2)
        wedge_node.parm("exportchannel1").set(1)
        wedge_node.parm("exportchannel2").set(1)
        wedge_node.parm("channel1").set("/obj/GIF_geo/GIF_fbx_import/fbxfile")
        wedge_node.parm("channel2").set("/obj/topnet_gif_gen/ropopengl1/camera")
        wedge_node.parm("name1").set("fbxfile")
        wedge_node.parm("name2").set("camera")
        wedge_node.parm("type1").set(4)
        wedge_node.parm("type2").set(4)

        # Iterate for each fbx
        count = 0
        for file in os.listdir(BASE_DIR):
            extension = os.path.splitext(file)[1]
            if extension == ".fbx":
                count += 1
                # add fbx file path for each fbx (wedge attr 1)
                wedge_node.parm("values1").set(count)
                wedge_node.parm(f"strvalue1_{count}").set(BASE_DIR + file)

                # create a different camera for each fbx (wedge attr 2)
                self.createCam(file, count)
                wedge_node.parm("values2").set(count)
                wedge_node.parm(f"strvalue2_{count}").set(f"/obj/GIF_camera{count}")

        wedge_node.parm("wedgecount").set(count)  # Set number of wedges, same as number of fbx files

        # Change Open GL Node parameters
        open_gl.parm("framegeneration").set(1)
        open_gl.parmTuple("res").set((200, 200))
        open_gl.parm("picture").set(f"{self.output_path}anim`@wedgeindex`/anim`@wedgeindex`.$F4.jpg")
        open_gl.parmTuple("f").deleteAllKeyframes()
        open_gl.parmTuple("f").set((1, 48, 1))

        # Change Partition by attr Node parameters
        partition.parm("attributes").set(1)
        partition.parm("name1").set("wedgeindex")

        # Change ffmpeg Node parameters
        ffmpeg.parm("framelistfile").set(f"{BASE_DIR}render/framelist/framelist`@wedgeindex`.txt")
        ffmpeg.parm("enablevideocodec").set(0)
        ffmpeg.parm("enablemovflags").set(0)
        ffmpeg.parm("ffmpegbinary").set(0)
        # Change ffmpeg Node parameters (save file)
        ffmpeg.parm("movflags").set("`@wedgeindex+1`")
        expression = """hou.parm(f"/obj/topnet_gif_gen/wedge1/strvalue1_{hou.parm('/obj/topnet_gif_gen/ffmpegencodevideo1/movflags').eval()}").eval().replace(".fbx",".gif")"""
        hou.parm('/obj/topnet_gif_gen/ffmpegencodevideo1/outputfilepath').setExpression(expression, hou.exprLanguage.Python)

    def addLight(self):
        """Add lights to the scene."""
        light = hou.node("/obj").createNode("hlight", "GIF_light")
        light2 = hou.node("/obj").createNode("hlight", "GIF_fill_light")
        light.parm("light_type").set(7)
        light.parm("light_intensity").set(2)
        light2.parm("light_type").set(7)
        light2.parm("light_intensity").set(1)
        light2.parm("rx").set(-120)

    def createCam(self, file, count):
        """Create camera for each FBX file."""
        hou.parm('/obj/GIF_geo/GIF_fbx_import/fbxfile').set(BASE_DIR + file)

        geo = hou.node('/obj/GIF_geo/GIF_fbx_import').geometry()
        bb = geo.boundingBox()
        self.vp.changeType(hou.geometryViewportType.Front)
        self.vp.frameBoundingBox(bb)
        vp_transform = self.vp.viewTransform()

        cam = hou.node('/obj').createNode('cam', f"GIF_camera{count}")
        cam.setWorldTransform(vp_transform)
        cam.parmTuple("res").set((480, 480))
        cam.parm("aperture").set(30)

    def cook(self):
        """Cook the top network."""
        hou.parm('/obj/topnet_gif_gen/cookbutton').pressButton()

    def main(self):
        """Main function to run the process."""
        self.createFbx()
        self.topNet()
        self.addLight()
        self.cook()
        self.vp.changeType(hou.geometryViewportType.Perspective)

class Ui(QtWidgets.QWidget):
    def __init__(self):
        """Initialize the UI."""
        super().__init__()
        self.build_layout()
        self.setWindowTitle("FBX Animations Browser")
        self.setMinimumSize(910, 600)

    def build_layout(self):
        """Build the layout for the UI."""
        self.lyt = QtWidgets.QGridLayout()
        self.setLayout(self.lyt)

        # QLineEdit
        self.field = QtWidgets.QLineEdit()
        self.lyt.addWidget(self.field)
        self.field.setPlaceholderText("Search your fbx here")
        self.field.textChanged.connect(self.showResults)

        # Create the content widget and its layout
        content_widget = QtWidgets.QWidget()
        self.content_layout = QtWidgets.QGridLayout(content_widget)

        # Add GIFs
        self.loadGifs()

        # Scroll Area
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(content_widget)
        self.lyt.addWidget(scroll_area)

        # Button
        btn = QtWidgets.QPushButton("Update Browser")
        self.lyt.addWidget(btn)
        btn.clicked.connect(self.updateButton)  # Button signal

    def loadGifs(self):
        """Load GIFs into the UI."""
        self.button_group = QtWidgets.QButtonGroup()  # Initialize group of buttons
        v, h = 1, 0
        for gif in os.listdir(BASE_DIR):
            if gif.endswith('.gif'):
                button = AnimatedButton(os.path.join(BASE_DIR, gif))
                button.setIconSize(QtCore.QSize(200, 200))
                button.setText(gif.removesuffix(".gif"))  # The text on the button will be the Fbx name.
                self.button_group.addButton(button)  # Add buttons to a group

                self.content_layout.addWidget(button, v, h)
                button.clicked.connect(lambda checked=False, gif=gif: self.create_import_node(gif))  # Activate signal
                h += 1
                if h == 4:
                    h = 0
                    v += 1

    def showResults(self, text):
        """Show search results based on input text."""
        # Iterate every button in the group.
        for button in self.button_group.buttons():
            if text.lower() in button.text().lower():
                button.show()
            else:
                button.hide()

    def updateButton(self):
        """Update the browser with new GIFs."""
        self.loadGifs()
        x = CreateGifs()
        x.main()

    def create_import_node(self, gif):
        """Create fbx import node for the selected file."""
        # Create node and add the name of the fbx file
        name = gif.removesuffix(".gif")
        clean_name = name.replace(" ", "_")
        geo = hou.node('/obj').createNode('geo', f'import_{clean_name}_fbx')
        import_node = geo.createNode('kinefx::fbxcharacterimport', f'{clean_name}_GIF_fbx_import')
        import_node.parm("fbxfile").set(BASE_DIR + name + ".fbx")
        # Change color and position of the nodes
        geo.setColor(hou.Color((0.451, 0.369, 0.796)))
        geo.moveToGoodPosition()

        # Display message
        popup = PopupMessage(f"{name}.fbx imported")
        popup.exec_()

class AnimatedButton(QtWidgets.QToolButton):
    def __init__(self, gif):
        """Initialize the animated button with a GIF."""
        super().__init__()
        self.movie = QtGui.QMovie(gif)

        self.default_icon = QtGui.QIcon(self.movie.currentPixmap())
        self.setIcon(self.default_icon)
        self.setIconSize(QtCore.QSize(50, 50))

        self.movie.frameChanged.connect(self.update_icon)
        self.movie.jumpToFrame(0)
        self.movie.setPaused(True)

        self.installEventFilter(self)
        self.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)  # Change style of the button

    def update_icon(self, frame):
        """Update the icon for the button."""
        self.setIcon(QtGui.QIcon(self.movie.currentPixmap()))

    def eventFilter(self, widget, event):
        """Handle events for the button."""
        if event.type() == QtCore.QEvent.Enter:
            self.movie.setPaused(False)
            return True
        elif event.type() == QtCore.QEvent.Leave:
            self.movie.setPaused(True)
            return True
        return False

class PopupMessage(QtWidgets.QMessageBox):
    def __init__(self, message):
        """Initialize the popup message."""
        super().__init__()
        self.setText(message)
        self.setWindowTitle("Import Message")
        self.setStandardButtons(QtWidgets.QMessageBox.Ok)

ui = Ui()
ui.show()
