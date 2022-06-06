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
    QMenu, QMenuBar, QVBoxLayout, QHBoxLayout
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
from pip import main

from pyqtgraph.parametertree import Parameter, ParameterTree
from pyqtgraph.parametertree import types as pTypes

import pyqtgraph as pg
import pyqtgraph.opengl as gl
from pyqtgraph import LayoutWidget 

import trimesh
import numpy as np

from MeshViewerWidget import MeshViewerWidget, ViewerItemContainer

class ObjectGroupParam(pTypes.GroupParameter):
    def __init__(self, main_windows):
        pTypes.GroupParameter.__init__(self, name="Objects", addText="Add New..", addList=['Mesh', 'Points', 'Path'])
        self.main_windows = main_windows
        
    def addNew(self, typ):
        if typ == 'Mesh':
            self.addChild(MeshParam(self.main_windows))
        elif typ == 'Points':
            self.addChild(SampleParam(self.main_windows))
        elif typ == 'Path':
            self.addChild(PathParam(self.main_windows))
    
class ViewerItemParam(pTypes.GroupParameter):
    def __init__(self, main_windows, **kwds):
        self.main_windows = main_windows
        self.setup()
        defs = dict(name=self.itemtype, autoIncrementName=True, renamable=False, removable=True, children=[
            dict(name='filename', type='str', value=self.item_container.name),
            dict(name='show', type='bool', value=bool(self.item_container.display)),
            ])
        pTypes.GroupParameter.__init__(self, **defs)
        self.restoreState(kwds, removeChildren=False)

    def setup(self):
        self.mesh_viewer_widget, self.container_list, self.item_container = None, None, None
        self.itemtype = None

    def remove(self):
        self.mesh_viewer_widget.removeItemContainer(self.item_container)
        self.container_list.remove(self.item_container)
        super().remove()

    def set_display(self):
        if self['show'] == self.item_container.display:
            return
        self.item_container.display = self['show']
        if self['show'] == True:
            self.mesh_viewer_widget.addItemContainer(self.item_container)
        else:
            self.mesh_viewer_widget.removeItemContainer(self.item_container)
    
    def set_select(self, param):
        limits = self.main_windows.object_options.param(param).opts['limits']
        name = self.name() 
        name += str(len(self.main_windows.object_options.param(param).opts['limits']))
        limits.append(name)
        self.main_windows.object_options.param(param).setLimits([''])
        self.main_windows.object_options.param(param).setLimits(limits)
        pass
    
class MeshParam(ViewerItemParam):
    def __init__(self, main_windows, **kwds):
        super().__init__(main_windows, **kwds)
        self.set_select('selected mesh')

    def setup(self):
        self.mesh_viewer_widget, self.container_list, self.item_container = self.main_windows.on_load_mesh()
        self.itemtype = 'Mesh'

pTypes.registerParameterType('Mesh', MeshParam)
    
class SampleParam(ViewerItemParam):
    def __init__(self, main_windows, **kwds):
        super().__init__(main_windows, **kwds)
        self.set_select('selected samples')

    def setup(self):
        self.mesh_viewer_widget, self.container_list, self.item_container = self.main_windows.on_load_sample()
        self.itemtype = 'Points'

pTypes.registerParameterType('Points', SampleParam)
    
class PathParam(ViewerItemParam):
    def __init__(self, main_windows, **kwds):
        super().__init__(main_windows, **kwds)
        self.set_select('selected path')

    def setup(self):
        self.mesh_viewer_widget, self.container_list, self.item_container = self.main_windows.on_load_path()
        self.itemtype = 'Path'
            
pTypes.registerParameterType('Path', MeshParam)


class MainWindow(QMainWindow):
    """An Application example to draw using a pen """

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.resize(1200,600)

        self.setup_toolbar()
        self.set_color(Qt.black)
        self.mime_type_filters = ["image/png", "image/jpeg"]

        self.graphics_viewer = MeshViewerWidget()

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.setup_menu()
        self.main_layout = QHBoxLayout()
        self.main_layout.setContentsMargins(0,0,0,0)
        self.main_layout.setMenuBar(self._menu_bar)
        self.splitter = QtWidgets.QSplitter()
        self.splitter.setSizes([1000,2000])
        self.splitter.setContentsMargins(0,0,0,0)
        self.splitter2 = QtWidgets.QSplitter()
        self.splitter2.setContentsMargins(0,0,0,0,)
        self.splitter.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.splitter2.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.main_layout.addWidget(self.splitter)
        self.main_widget.setLayout(self.main_layout)

        self.setup_object_list_tree()
        self.setup_parameter_tree()

        self.splitter.addWidget(self.object_list_tree)
        self.splitter.addWidget(self.splitter2)
        self.splitter2.addWidget(self.graphics_viewer)
        self.splitter2.addWidget(self.parameter_tree)
        self.splitter.setStretchFactor(0, 2)
        self.splitter.setStretchFactor(1, 3)

    def setup_toolbar(self):
        self.bar = self.addToolBar("Tool Bar")
        self.bar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.bar.addAction(
            # qApp.style().standardIcon(QStyle.SP_DialogResetButton),
            qApp.style().standardIcon(QStyle.SP_DialogOpenButton),
            "Load Mesh",
            self.on_load_mesh,
        )
        self.bar.addAction(
            qApp.style().standardIcon(QStyle.SP_DialogOpenButton),
            "Load Points",
            self.on_load_sample,
        )
        self.bar.addAction(
            qApp.style().standardIcon(QStyle.SP_DialogOpenButton),
            "Load Path",
            self.on_load_path,
        )
        self.bar.addSeparator()

        self._save_action = self.bar.addAction(
            qApp.style().standardIcon(QStyle.SP_DialogSaveButton), "Save", self.on_save
        )
        self._save_action.setShortcut(QKeySequence.Save)
        self._open_action = self.bar.addAction(
            qApp.style().standardIcon(QStyle.SP_DialogOpenButton), "Open", self.on_open
        )
        self._open_action.setShortcut(QKeySequence.Open)

        self.color_action = QAction(self)
        self.color_action.triggered.connect(self.on_color_clicked)
        self.bar.addAction(self.color_action)

    def setup_menu(self):
        self._menu_bar = QMenuBar()

        self._file_menu = QMenu("&File", self)
        self._exit_action = self._file_menu.addAction("E&xit")
        self._menu_bar.addMenu(self._file_menu)
        # self.addMenu(self._file_menu)

        # self._exit_action.triggered.connect(self.accept)
        # self._exit_action.triggered.connect(self.color_action)

    def setup_object_list_tree(self):
        self.object_list_tree = ParameterTree(showHeader=False)
        self.object_objeGroupParam = ObjectGroupParam(self)
        
        self.object_options = Parameter.create(name='params', type='group', children=[
            dict(name='Load Preset..', type='list', limits=[]),
            dict(name='selected mesh', type='list', limits=['']),
            dict(name='selected samples', type='list', limits=['']),
            dict(name='selected path', type='list', limits=['']),
            # dict(name='Duration', type='float', value=10.0, step=0.1, limits=[0.1, None]),
            # dict(name='Reference Frame', type='list', limits=[]),
            # dict(name='Animate', type='bool', value=True),
            # dict(name='Animation Speed', type='float', value=1.0, dec=True, step=0.1, limits=[0.0001, None]),
            # dict(name='Save', type='action'),
            # dict(name='Load', type='action'),
            self.object_objeGroupParam,
            ])
        self.object_list_tree.setParameters(self.object_options, showTop=False)
        # self.object_options.param('Recalculate Worldlines').sigActivated.connect(self.set_color())
        # self.object_options.param('Save').sigActivated.connect(self.save())
        # self.object_options.param('Load').sigActivated.connect(self.load())
        # self.object_options.param('Load Preset..').sigValueChanged.connect(self.loadPreset)
        self.selected_mesh = None
        self.selected_mesh_name = None
        self.selected_sample = None
        self.selected_sample_name = None
        self.selected_path = None
        self.selected_path_name = None
        self.object_options.param('selected mesh').sigValueChanged.connect(self.on_select_mesh)
        self.object_options.param('selected samples').sigValueChanged.connect(self.on_select_sample)
        self.object_options.param('selected path').sigValueChanged.connect(self.on_select_path)
        self.object_options.sigTreeStateChanged.connect(self.on_objectTree_change)
        
        ## read list of preset configs
        # presetDir = os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), 'presets')
        # if os.path.exists(presetDir):
        #     presets = [os.path.splitext(p)[0] for p in os.listdir(presetDir)]
        #     self.object_options.param('Load Preset..').setLimits(['']+presets)

    def on_objectTree_change(self, *args):
        for object in self.object_options.param('Objects'):
            object.set_display()

        for param, change, data in args[1]:
            if change == 'childAdded':
                if self.object_options.param('selected mesh').value() == '' and \
                        len(self.object_options.param('selected mesh').opts['limits']) > 1:
                    if self.selected_mesh_name == None:
                        self.selected_mesh_name = self.object_options.param('selected mesh').opts['limits'][1]
                    self.object_options.param('selected mesh').setValue(self.selected_mesh_name)
                if self.object_options.param('selected samples').value() == '' and \
                        len(self.object_options.param('selected samples').opts['limits']) > 1:
                    if self.selected_sample_name == None:
                        self.selected_sample_name = self.object_options.param('selected samples').opts['limits'][1]
                    self.object_options.param('selected samples').setValue(self.selected_sample_name)
                if self.object_options.param('selected path').value() == '' and \
                        len(self.object_options.param('selected path').opts['limits']) > 1:
                    if self.selected_path_name == None:
                        self.selected_path_name = self.object_options.param('selected path').opts['limits'][1]
                    self.object_options.param('selected path').setValue(self.selected_path_name)

    def on_select_mesh(self, param, selected_mesh_name):
        self.selected_mesh_name = selected_mesh_name
        mesh_num = len(self.object_options.param('selected mesh').opts['limits'])-1
        for obj in self.object_options.param('Objects'):
            if obj.itemtype == 'Mesh':
                if obj.name()+str(mesh_num) == selected_mesh_name:
                    self.selected_mesh = obj.item_container.mesh
                    break

    def on_select_sample(self, param, selected_sample_name):
        self.selected_sample_name = selected_sample_name
        sample_num = len(self.object_options.param('selected samples').opts['limits'])-1
        for obj in self.object_options.param('Objects'):
            if obj.itemtype == 'Points':
                if obj.name()+str(sample_num) == selected_sample_name:
                    self.selected_sample = obj.item_container.sample
                    break

    def on_select_path(self, param, selected_path_name):
        self.selected_mesh_name = selected_path_name
        path_num = len(self.object_options.param('selected path').opts['limits'])-1
        for obj in self.object_options.param('Objects'):
            if obj.itemtype == 'Path':
                if obj.name()+str(path_num) == selected_path_name:
                    self.selected_path = obj.item_container.path
                    break
    
    def setup_parameter_tree(self):
        self.parameter_tree = ParameterTree(showHeader=False)
        objectGroup = ObjectGroupParam(self)
        
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
            objectGroup,
            ])
        self.parameter_tree.setParameters(self.params, showTop=False)
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
        # dialog.setDirectory(str(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))

        if dialog.exec() == QFileDialog.Accepted:
            if dialog.selectedFiles():
                return self.graphics_viewer.load_mesh(dialog.selectedFiles()[0])

    @Slot()
    def on_load_sample(self):
        dialog = QFileDialog(self, "Load Points")
        # dialog.setMimeTypeFilters(['mesh/ply', 'mesh/obj'])
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        # dialog.setDefaultSuffix("ply")
        # dialog.setDirectory(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

        if dialog.exec() == QFileDialog.Accepted:
            if dialog.selectedFiles():
                return self.graphics_viewer.load_sample(dialog.selectedFiles()[0])

    @Slot()
    def on_load_path(self):
        dialog = QFileDialog(self, "Load Path")
        # dialog.setMimeTypeFilters(['mesh/ply', 'mesh/obj'])
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        # dialog.setDefaultSuffix(".log")
        # dialog.setDirectory(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

        if dialog.exec() == QFileDialog.Accepted:
            if dialog.selectedFiles():
                return self.graphics_viewer.load_path(dialog.selectedFiles()[0])

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
