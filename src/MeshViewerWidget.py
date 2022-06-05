from http.client import INSUFFICIENT_STORAGE
from re import A
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
from pyqtgraph.opengl.GLGraphicsItem import GLGraphicsItem
from pyqtgraph import LayoutWidget

import trimesh
import numpy as np
from path import Trajectory, PathNode


class ViewerItemContainer():
    def __init__(self, path, display=True) -> None:
        self.display = display
        self.load(path)

    def is_empty(self):
        return self.item == None

    def len(self):
        if self.is_empty():
            return 0
        else:
            return 1

class ViewerMeshItemContainer(ViewerItemContainer):
    def __init__(self, path) -> None:
        super().__init__(path)

    def load(self, mesh_path=r'F:\projects\DroneCenter\test_data\xuexiao_coarse.ply'):
        self.mesh = trimesh.load_mesh(mesh_path)
        self.name = os.path.basename(mesh_path)
        self.item = gl.GLMeshItem(
            vertexes=self.mesh.vertices,
            faces=self.mesh.faces, shader='viewNormalColor',
            glOptions='opaque', smooth=False)

class ViewerSampleItemContainer(ViewerItemContainer):
    def __init__(self, path, display=True) -> None:
        self.size = 2.
        super().__init__(path, display)

    def load(self, mesh_path=r'F:\projects\DroneCenter\test_data\xuexiao_coarse_90.ply', color=None):
        self.sample = trimesh.load_mesh(mesh_path)
        self.name = os.path.basename(mesh_path)
        self.set_item()
        self.set_color(color)

    def set_sample(self, sample, name='samples', color=None):
        self.name = name
        self.sample = sample
        self.set_item(color)

    def set_item(self, color=None):
        self.item = []
        self.set_color(color)
        self.item = gl.GLScatterPlotItem(pos=self.sample.vertices, size=self.size, color=self.color, pxMode=False, glOptions='translucent')
        # for i, pos in enumerate(self.sample.vertices):
        #     self.item.append(gl.GLScatterPlotItem(pos=self.sample.vertices[i], size=self.size, color=self.color[i], pxMode=False, glOptions='translucent'))
        #     # sphere = gl.MeshData.sphere(rows=1, cols=1, radius=self.radius)
        #     # sphere_meshItem = gl.GLMeshItem(meshdata=sphere, color=self.color[i], smooth=True)
        #     # sphere_meshItem.translate(pos[0], pos[1], pos[2])
        #     # self.item.append(sphere_meshItem)

    def set_color(self, color=None):
        sample_len = len(self.sample.vertices)
        if color == None or not color.size(0) == sample_len:
            self.color = np.tile(np.array((1., 0., 0., 1.)), (sample_len, 1))
        elif color.size(0) == 1:
            self.color = np.tile(color, (sample_len, 1))
        else:
            self.color = color

class ViewerPathItemContainer(ViewerItemContainer):
    def __init__(self, path, display=True) -> None:
        self.radius = [.8, 0.]
        self.length = 4.
        super().__init__(path, display)

    def load(self, log_path=r'H:\final_trajectory.log', color=None):
        self.path = Trajectory(log_path)
        self.name = os.path.basename(log_path)
        self.set_color(color)
        self.set_item()

    def set_path(self, trajectory, name='path', color=None):
        self.name = name
        self.path = trajectory
        self.set_item(color)

    def set_item(self, color=None):
        self.item = []
        self.set_color(color)
        for i, node in enumerate(self.path.path):
            cylinder = gl.MeshData.cylinder(
                rows=1, cols=3, radius=self.radius, length=self.length)
            cylinder_meshItem = gl.GLMeshItem(
                meshdata=cylinder, color=self.color[i], smooth=True, drawEdges=False, shader='balloon')
            cylinder_meshItem.rotate(-90, 1, 0, 0)
            cylinder_meshItem.rotate(node.pitch, 1, 0, 0)
            cylinder_meshItem.rotate(node.yaw-90, 0, 0, 1)
            cylinder_meshItem.translate(node.x, node.y, node.z)
            self.item.append(cylinder_meshItem)

    def set_color(self, color=None):
        path_len = len(self.path.path)
        if color == None or not color.size(0) == path_len:
            self.color = np.tile(np.array((0., 0., 1., 1.)), (path_len, 1))
        else:
            self.color = color

    def set_radius(self, radius):
        self.radius = radius
        self.set_item()

    def set_length(self, length):
        self.length = length
        self.set_item()

    def len(self):
        if self.is_empty():
            return 0
        else:
            return len(self.item)


class MeshViewerWidget(gl.GLViewWidget):
    def __init__(self, parent=None, devicePixelRatio=None, rotationMethod='euler'):
        super().__init__(parent, devicePixelRatio, rotationMethod)
        # self.setBackgroundColor(255,255,255)
        self.setWindowTitle('3D Viewer')
        self.setCameraPosition(distance=256)

        grid = gl.GLGridItem()
        grid.setColor((100, 100, 100))
        grid.scale(2, 2, 1)
        self.addItem(grid)
        axis = gl.GLAxisItem(QVector3D(3, 3, 3))
        axis.translate(0.5, 0.5, 0.5)
        self.addItem(axis)

        self.meshContainer_list = []
        self.pathContainer_list = []
        self.sampleContainer_list = []

        # self.load_example()

    def load_example(self):
        src_dir = os.path.dirname(os.path.abspath(__file__))
        self.load_mesh(os.path.join(src_dir, '../test_data/xuexiao_coarse.ply'))
        self.load_sample(os.path.join(src_dir, '../test_data/xuexiao_coarse_90.ply'))
        self.load_path(os.path.join(src_dir, '../test_data/final_trajectory.log'))

    def load(self,path):
        pass

    def load_mesh(self, mesh_path=r'F:\projects\DroneCenter\test_data\xuexiao_coarse.ply'):
        mesh_container = ViewerMeshItemContainer(mesh_path)
        self.meshContainer_list.append(mesh_container)
        self.addItemContainer(mesh_container)

    def load_path(self, log_path=r'F:\projects\DroneCenter\test_data\final_trajectory.log'):
        path_container = ViewerPathItemContainer(log_path)
        self.pathContainer_list.append(path_container)
        self.addItemContainer(path_container)

    def load_sample(self, sample_path=r'F:\projects\DroneCenter\test_data\xuexiao_coarse_90.ply'):
        sample_container = ViewerSampleItemContainer(sample_path)
        self.sampleContainer_list.append(sample_container)
        self.addItemContainer(sample_container)

    def addItemContainer(self, itemContainer):
        if not type(itemContainer.item) == list:
            self.addItem(itemContainer.item)
        else:
            for i in itemContainer.item:
                self.addItem(i)

    def removeItemContainer(self, itemContainer):
        itemContainer.display = False
        if not type(itemContainer.item) == list:
            self.removeItem(itemContainer.item)
        else:
            for i in itemContainer.item:
                self.removeItem(i)