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


class ViewerMeshItem():
    def __init__(self) -> None:
        self.setup()

    def __init__(self, mesh_path) -> None:
        self.setup()
        self.load_mesh(mesh_path)

    def setup(self):
        self.mesh = None
        self.path = None
        self.name = None
        self.item = None

    def load_mesh(self, mesh_path=r'F:\projects\DroneCenter\test_data\xuexiao_coarse.ply'):
        self.mesh = trimesh.load_mesh(mesh_path)
        self.name = os.path.basename(mesh_path).split(os.sep)[0]
        self.item = gl.GLMeshItem(
            vertexes=self.mesh.vertices,
            faces=self.mesh.faces, shader='viewNormalColor',
            glOptions='opaque', smooth=False)
        pass

    def is_empty(self):
        return self.item == None


class ViewerSampleItem():
    def __init__(self) -> None:
        self.setup()

    def __init__(self, sample_path) -> None:
        self.setup()
        self.load_sample(sample_path)

    def setup(self):
        self.sample = None
        self.size = 2.
        # self.radius = .5
        self.color = None

    def load_sample(self, mesh_path=r'F:\projects\DroneCenter\test_data\xuexiao_coarse_90.ply', color=None):
        self.sample = trimesh.load_mesh(mesh_path)
        self.name = os.path.basename(mesh_path).split(os.sep)[0]
        self.set_item()
        pass

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


class PathNode():
    def __init__(self, x, y, z, pitch, roll, yaw) -> None:
        self.x, self.y, self.z, self.pitch, self.roll, self.yaw = \
            x, y, z, pitch, roll, yaw
        pass


class Trajectory():
    def __init__(self) -> None:
        self.path = []
        pass

    def __init__(self, log_path) -> None:
        self.path = []
        self.load_smith18_path(log_path)
        pass

    def load_smith18_path(self, log_path):
        f = open(log_path, 'r')
        lines = f.readlines()
        self.path = []
        for i, line in enumerate(lines):
            imagename, x, y, z, pitch, roll, yaw = line.split(',')
            # as the same format used in C++ program
            x, y, z, pitch, roll, yaw = - \
                float(x)/100, float(y)/100, float(z)/100, - \
                float(pitch), float(roll), 90-float(yaw)
            node = PathNode(x, y, z, pitch, roll, yaw)
            self.path.append(node)

    def len(self):
        return len(self.path)

    def is_empty(self):
        return self.len() == 0


class ViewerPathItem():
    def __init__(self) -> None:
        self.setup()

    def __init__(self, log_path) -> None:
        self.setup()
        self.load_path(log_path)

    def setup(self):
        self.path = None
        self.name = None
        self.item = None
        self.color = None
        self.radius = [.8, 0.]
        self.length = 4.

    def load_path(self, log_path=r'H:\final_trajectory.log', color=None):
        self.path = Trajectory(log_path)
        self.name = os.path.basename(log_path).split(os.sep)[0]
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
        if self.color == None or not self.color.size(0) == path_len:
            self.color = np.tile(np.array((0., 0., 1., 1.)), (path_len, 1))
        else:
            self.color = color

    def set_radius(self, radius):
        self.radius = radius
        self.set_item()

    def set_length(self, length):
        self.length = length
        self.set_item()

    def is_empty(self):
        return self.item == None


class MeshViewerWidget(gl.GLViewWidget):
    def __init__(self, parent=None, devicePixelRatio=None, rotationMethod='euler'):
        super().__init__(parent, devicePixelRatio, rotationMethod)
        # self.setBackgroundColor(255,255,255)
        self.setWindowTitle('pyqtgraph example: GLMeshItem')
        self.setCameraPosition(distance=120)

        grid = gl.GLGridItem()
        grid.setColor((100, 100, 100))
        grid.scale(2, 2, 1)
        self.addItem(grid)
        axis = gl.GLAxisItem(QVector3D(3, 3, 3))
        axis.translate(0.5, 0.5, 0.5)
        self.addItem(axis)

        self.meshitem_list = []
        self.pathitem_list = []
        self.sampleitem_list = []

        self.load_mesh()
        self.load_path()
        self.load_sample()

    def load_mesh(self, mesh_path=r'F:\projects\DroneCenter\test_data\xuexiao_coarse.ply'):
        meshitem = ViewerMeshItem(mesh_path)
        self.meshitem_list.append(meshitem)
        self.addItem(meshitem.item)

    def load_path(self, log_path=r'F:\projects\DroneCenter\test_data\final_trajectory.log'):
        pathitem = ViewerPathItem(log_path)
        self.pathitem_list.append(pathitem)
        for item in pathitem.item:
            self.addItem(item)

    def load_sample(self, sample_path=r'F:\projects\DroneCenter\test_data\xuexiao_coarse_90.ply'):
        sampleitem = ViewerSampleItem(sample_path)
        self.sampleitem_list.append(sampleitem)
        self.addItem(sampleitem.item)
        # for item in sampleitem.item:
        #     self.addItem(item)