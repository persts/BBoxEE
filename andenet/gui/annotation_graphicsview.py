# -*- coding: utf-8 -*-
#
# Animal Detection Network (Andenet)
# Author: Peter Ersts (ersts@amnh.org)
#
# --------------------------------------------------------------------------
#
# This file is part of Animal Detection Network (Andenet).
#
# Andenet is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Andenet is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.
#
# --------------------------------------------------------------------------
from PyQt5 import QtWidgets, QtCore, QtGui
from enum import Enum


class Quad(Enum):
    TL = 0
    TR = 1
    BR = 2
    BL = 3


class Mode(Enum):
    PAN = 0
    EDIT = 1
    RESIZE = 2


class AnnotationGraphicsView(QtWidgets.QGraphicsView):
    """Custom QGraphicsView for creating and editing annotation
    bounding boxes."""

    created = QtCore.pyqtSignal(QtCore.QRectF)
    resized = QtCore.pyqtSignal(QtCore.QRectF)
    select_bbox = QtCore.pyqtSignal(QtCore.QPointF)
    zoom_event = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        """Class init function."""
        QtWidgets.QGraphicsView.__init__(self, parent)
        self.mode = Mode.PAN
        self.points = []
        self.point_graphics_items = []
        self.bbox = QtCore.QRectF()
        self.selected_bbox = None
        self.quad = Quad.TL
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)
        self.brushes = [QtGui.QBrush(QtCore.Qt.blue, QtCore.Qt.SolidPattern),
                        QtGui.QBrush(QtCore.Qt.green, QtCore.Qt.SolidPattern),
                        QtGui.QBrush(QtCore.Qt.yellow, QtCore.Qt.SolidPattern),
                        QtGui.QBrush(QtCore.Qt.red, QtCore.Qt.SolidPattern)]
        self.pens = [QtGui.QPen(self.brushes[0], 2),
                     QtGui.QPen(self.brushes[1], 2),
                     QtGui.QPen(self.brushes[2], 2),
                     QtGui.QPen(self.brushes[3], 2)]

    def clear_points(self):
        for item in self.point_graphics_items:
            self.scene().removeItem(item)
            self.point_graphics_items = []
            self.points = []

    def mouseMoveEvent(self, event):
        if self.mode == Mode.RESIZE:
            point = self.mapToScene(event.pos())
            rect = self.selected_bbox.rect()
            if self.quad == Quad.TL:
                rect.setTopLeft(point)
            elif self.quad == Quad.TR:
                rect.setTopRight(point)
            elif self.quad == Quad.BR:
                rect.setBottomRight(point)
            else:
                rect.setBottomLeft(point)
            self.selected_bbox.setRect(rect)
        else:
            QtWidgets.QGraphicsView.mouseMoveEvent(self, event)

    def mousePressEvent(self, event):
        """Overload of the mousePressEvent that stores mouse click
        positions in a list."""
        if len(self.scene().items()) > 0:
            if event.button() == QtCore.Qt.MiddleButton:
                self.clear_points()
            elif self.mode == Mode.PAN:
                self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
                QtWidgets.QGraphicsView.mousePressEvent(self, event)
            else:  # mode = Mode.EDIT
                point = self.mapToScene(event.pos())
                collect_points = True
                if len(self.points) == 0:
                    if (self.selected_bbox is not None and
                            self.selected_bbox.boundingRect().contains(point)):
                        self.mode = Mode.RESIZE
                        center = self.selected_bbox.boundingRect().center()
                        if point.x() < center.x() and point.y() < center.y():
                            self.quad = Quad.TL
                        elif point.x() > center.x() and point.y() < center.y():
                            self.quad = Quad.TR
                        elif point.x() > center.x() and point.y() > center.y():
                            self.quad = Quad.BR
                        else:
                            self.quad = Quad.BL
                    else:
                        for graphic in self.scene().items():
                            if type(graphic) == QtWidgets.QGraphicsRectItem:
                                if graphic.boundingRect().contains(point):
                                    collect_points = False
                                    self.select_bbox.emit(point)
                                    break

                if collect_points and self.mode == Mode.EDIT:
                    rect = QtCore.QRectF(point.x() - 5, point.y() - 5, 11, 11)
                    pen = self.pens[len(self.points)]
                    brush = self.brushes[len(self.points)]
                    (self.point_graphics_items.
                        append(self.scene().addEllipse(rect, pen, brush)))
                    self.points.append(event.pos())

    def mouseReleaseEvent(self, event):
        """Overload of the MouseReleaseEvent that will calculate the
        bounding box when four points are available."""
        self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        if self.mode == Mode.RESIZE:
            rect = self.selected_bbox.rect()
            self.verify_rect(rect)
            self.selected_bbox.setRect(rect)
            self.resized.emit(rect)
            self.mode = Mode.EDIT

        if len(self.points) == 4:
            x_min = 100000000
            y_min = 100000000
            x_max = 0
            y_max = 0
            for point in self.points:
                x_min = min(x_min, point.x())
                x_max = max(x_max, point.x())
                y_min = min(y_min, point.y())
                y_max = max(y_max, point.y())
            for item in self.point_graphics_items:
                self.scene().removeItem(item)
            self.point_graphics_items = []
            rect = QtCore.QRect(x_min, y_min, x_max - x_min, y_max - y_min)
            rect = self.mapToScene(rect).boundingRect()
            self.verify_rect(rect)
            self.created.emit(rect)
            self.points = []

    def set_edit_mode(self, enabled):
        if enabled:
            self.mode = Mode.EDIT
        else:
            self.mode = Mode.PAN

    def verify_rect(self, rect):
        if rect.left() < 0:
            rect.setLeft(0.0)
        if rect.top() < 0:
            rect.setTop(0.0)
        if rect.right() > self.sceneRect().right():
            rect.setRight(self.sceneRect().right())
        if rect.bottom() > self.sceneRect().bottom():
            rect.setBottom(self.sceneRect().bottom())

    def wheelEvent(self, event):
        if len(self.scene().items()) > 0:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()

    def zoom_in(self):
        if len(self.scene().items()) > 0:
            self.scale(1.1, 1.1)
            self.zoom_event.emit()

    def zoom_out(self):
        if len(self.scene().items()) > 0:
            self.scale(0.9, 0.9)
            self.zoom_event.emit()
