from posixpath import dirname
from PySide6 import QtWidgets
from PySide6 import QtCore
from PySide6.QtWidgets import (
    QWidget,
    QMainWindow,
    QApplication,
    QFileDialog,
    QStyle,
    QColorDialog,
    QMenu, QMenuBar, QVBoxLayout
)
from PySide6.QtCore import QPoint, Qt, QDir, Slot, QStandardPaths
from PySide6.QtGui import (
    QMouseEvent,
    QPaintEvent,
    QPen,
    QAction,
    QPainter,
    QColor,
    QPixmap,
    QIcon,
    QKeySequence,
    QVector3D
)
import sys
import os

from pyqtgraph.parametertree import Parameter, ParameterTree
from pyqtgraph.parametertree import types as pTypes

import pyqtgraph as pg
import pyqtgraph.opengl as gl
from pyqtgraph import LayoutWidget 

import trimesh
import numpy as np

from MeshViewerWidget import MeshViewerWidget

class ObjectGroupParam(pTypes.GroupParameter):
    def __init__(self):
        pTypes.GroupParameter.__init__(self, name="Objects", addText="Add New..", addList=['Clock', 'Grid'])
        
    def addNew(self, typ):
        if typ == 'Clock':
            self.addChild(ClockParam())
        elif typ == 'Grid':
            self.addChild(GridParam())


class MainWindow(QMainWindow):
    """An Application example to draw using a pen """

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.resize(1200,800)

        self.graphics_viewer = MeshViewerWidget()

        self.bar = self.addToolBar("Menu")
        self.bar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._save_action = self.bar.addAction(
            qApp.style().standardIcon(QStyle.SP_DialogSaveButton), "Save", self.on_save
        )
        self._save_action.setShortcut(QKeySequence.Save)
        self._open_action = self.bar.addAction(
            qApp.style().standardIcon(QStyle.SP_DialogOpenButton), "Open", self.on_open
        )
        self._open_action.setShortcut(QKeySequence.Open)
        self.bar.addAction(
            # qApp.style().standardIcon(QStyle.SP_DialogResetButton),
            qApp.style().standardIcon(QStyle.SP_DialogOpenButton),
            "Load Mesh",
            self.on_load_mesh,
        )
        self.bar.addAction(
            qApp.style().standardIcon(QStyle.SP_DialogOpenButton),
            "Load Points",
            self.on_load_points,
        )
        self.bar.addAction(
            qApp.style().standardIcon(QStyle.SP_DialogOpenButton),
            "Load Path",
            self.on_load_path,
        )
        self.bar.addSeparator()

        self.color_action = QAction(self)
        self.color_action.triggered.connect(self.on_color_clicked)
        self.bar.addAction(self.color_action)

        self.set_color(Qt.black)
        self.mime_type_filters = ["image/png", "image/jpeg"]

        # self.setCentralWidget(self.painter_widget)

        # self.setCentralWidget(self.graphics_views )

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.create_menu()
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0,0,0,0)
        self.main_layout.setMenuBar(self._menu_bar)
        self.splitter = QtWidgets.QSplitter()
        self.splitter.setContentsMargins(0,0,0,0)
        self.splitter2 = QtWidgets.QSplitter()
        self.splitter2.setContentsMargins(0,0,0,0,)
        self.splitter.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.splitter2.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.main_layout.addWidget(self.splitter)
        # self.main_layout.addWidget(self.graphics_views)
        self.main_widget.setLayout(self.main_layout)

        self.tree = ParameterTree(showHeader=False)
        self.tree2 = ParameterTree(showHeader=False)
        self.splitter.addWidget(self.tree2)
        self.splitter.addWidget(self.splitter2)
        self.splitter2.addWidget(self.graphics_viewer)
        self.splitter2.addWidget(self.tree)

        self.objectGroup = ObjectGroupParam()
        
        self.params = Parameter.create(name='params', type='group', children=[
            dict(name='Load Preset..', type='list', limits=[]),
            #dict(name='Unit System', type='list', limits=['', 'MKS']),
            dict(name='Duration', type='float', value=10.0, step=0.1, limits=[0.1, None]),
            dict(name='Reference Frame', type='list', limits=[]),
            dict(name='Animate', type='bool', value=True),
            dict(name='Animation Speed', type='float', value=1.0, dec=True, step=0.1, limits=[0.0001, None]),
            dict(name='Recalculate Worldlines', type='action'),
            dict(name='Save', type='action'),
            dict(name='Load', type='action'),
            self.objectGroup,
            ])
        self.tree.setParameters(self.params, showTop=False)
        self.params.param('Recalculate Worldlines').sigActivated.connect(self.set_color())
        # self.params.param('Save').sigActivated.connect(self.save())
        # self.params.param('Load').sigActivated.connect(self.load())
        # self.params.param('Load Preset..').sigValueChanged.connect(self.loadPreset)
        self.params.sigTreeStateChanged.connect(self.treeChanged)
        
        ## read list of preset configs
        presetDir = os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), 'presets')
        if os.path.exists(presetDir):
            presets = [os.path.splitext(p)[0] for p in os.listdir(presetDir)]
            self.params.param('Load Preset..').setLimits(['']+presets)
    
    def create_menu(self):
        self._menu_bar = QMenuBar()

        self._file_menu = QMenu("&File", self)
        self._exit_action = self._file_menu.addAction("E&xit")
        self._menu_bar.addMenu(self._file_menu)
        # self.addMenu(self._file_menu)

        # self._exit_action.triggered.connect(self.accept)
        # self._exit_action.triggered.connect(self.color_action)

    def treeChanged(self, *args):
        clocks = []
        for c in self.params.param('Objects'):
            clocks.extend(c.clockNames())
        #for param, change, data in args[1]:
            #if change == 'childAdded':
        self.params.param('Reference Frame').setLimits(clocks)
        # self.setAnimation(self.params['Animate'])
        
    def save(self):
        filename = pg.QtWidgets.QFileDialog.getSaveFileName(self, "Save State..", "untitled.cfg", "Config Files (*.cfg)")
        if isinstance(filename, tuple):
            filename = filename[0]  # Qt4/5 API difference
        if filename == '':
            return
        state = self.params.saveState()
        configfile.writeConfigFile(state, str(filename)) 
        
    def load(self):
        filename = pg.QtWidgets.QFileDialog.getOpenFileName(self, "Save State..", "", "Config Files (*.cfg)")
        if isinstance(filename, tuple):
            filename = filename[0]  # Qt4/5 API difference
        if filename == '':
            return
        state = configfile.readConfigFile(str(filename)) 
        self.loadState(state)
        
    def loadPreset(self, param, preset):
        if preset == '':
            return
        path = os.path.abspath(os.path.dirname(__file__))
        fn = os.path.join(path, 'presets', preset+".cfg")
        state = configfile.readConfigFile(fn)
        self.loadState(state)
        
    def loadState(self, state):
        if 'Load Preset..' in state['children']:
            del state['children']['Load Preset..']['limits']
            del state['children']['Load Preset..']['value']
        self.params.param('Objects').clearChildren()
        self.params.restoreState(state, removeChildren=False)
        self.recalculate()
        
    @Slot()
    def on_load_mesh(self):
        dialog = QFileDialog(self, "Load Mesh")
        # dialog.setMimeTypeFilters(['mesh/ply', 'mesh/obj'])
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        # dialog.setDefaultSuffix("ply")
        dialog.setDirectory(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

        if dialog.exec() == QFileDialog.Accepted:
            if dialog.selectedFiles():
                self.graphics_viewer.load_mesh(dialog.selectedFiles()[0])

    @Slot()
    def on_load_points(self):
        dialog = QFileDialog(self, "Load Points")
        # dialog.setMimeTypeFilters(['mesh/ply', 'mesh/obj'])
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        # dialog.setDefaultSuffix("ply")
        dialog.setDirectory(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

        if dialog.exec() == QFileDialog.Accepted:
            if dialog.selectedFiles():
                self.graphics_viewer.load_sample(dialog.selectedFiles()[0])

    @Slot()
    def on_load_path(self):
        dialog = QFileDialog(self, "Load Path")
        # dialog.setMimeTypeFilters(['mesh/ply', 'mesh/obj'])
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        # dialog.setDefaultSuffix(".log")
        dialog.setDirectory(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

        if dialog.exec() == QFileDialog.Accepted:
            if dialog.selectedFiles():
                self.graphics_viewer.load_path(dialog.selectedFiles()[0])

    @Slot()
    def on_save(self):

        dialog = QFileDialog(self, "Save File")
        dialog.setMimeTypeFilters(self.mime_type_filters)
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setDefaultSuffix("png")
        dialog.setDirectory(
            QStandardPaths.writableLocation(QStandardPaths.PicturesLocation)
        )

        # if dialog.exec() == QFileDialog.Accepted:
        #     if dialog.selectedFiles():
        #         self.painter_widget.save(dialog.selectedFiles()[0])

    @Slot()
    def on_open(self):

        dialog = QFileDialog(self, "Save File")
        dialog.setMimeTypeFilters(self.mime_type_filters)
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        dialog.setDefaultSuffix("png")
        dialog.setDirectory(
            QStandardPaths.writableLocation(QStandardPaths.PicturesLocation)
        )

        # if dialog.exec() == QFileDialog.Accepted:
        #     if dialog.selectedFiles():
        #         self.painter_widget.load(dialog.selectedFiles()[0])

    @Slot()
    def on_color_clicked(self):

        color = QColorDialog.getColor(Qt.black, self)
        if color:
            self.set_color(color)

    def set_color(self, color: QColor = Qt.black):

        # Create color icon
        pix_icon = QPixmap(32, 32)
        pix_icon.fill(color)

        self.color_action.setIcon(QIcon(pix_icon))
        # self.painter_widget.pen.setColor(color)
        self.color_action.setText(QColor(color).name())


if __name__ == "__main__":

    app = QApplication(sys.argv)

    w = MainWindow()
    w.show()
    sys.exit(app.exec())
