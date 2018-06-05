# -*- coding: utf-8 -*-
#
# Animal Detection Network (Andenet)
# Copyright (C) 2017 Peter Ersts
# ersts@amnh.org
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
# along with with this software.  If not, see <http://www.gnu.org/licenses/>.
#
# --------------------------------------------------------------------------
from PyQt5 import QtWidgets, QtCore, QtGui


class BBoxSizeGrip(QtWidgets.QSizeGrip):
    """Extended version of QSizeGrip."""

    resized = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        """Class init function."""
        QtWidgets.QSizeGrip.__init__(self, parent)

    def mouseReleaseEvent(self, event):
        """Overload of mouseReleaseEvent to emit a resize signal."""
        self.resized.emit()


class BBoxWidget(QtWidgets.QFrame):
    """Custom QFrame to allow resizing of annotation bounding boxes."""

    resized = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        """Class init function."""
        QtWidgets.QFrame.__init__(self, parent)
        self.setWindowFlags(QtCore.Qt.SubWindow)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("BBoxWidget { border: 1px solid rgb(255, 0, 255);}")
        self.grip1 = BBoxSizeGrip(self)
        self.grip2 = BBoxSizeGrip(self)
        self.grip1.resized.connect(self.resize_complete)
        self.layout.addWidget(self.grip1, 0, QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.grip2.resized.connect(self.resize_complete)
        self.layout.addWidget(self.grip2, 0, QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)
        self.hide()

    def resize_complete(self):
        """(Slot) Receives the resize signal from the BBoxSizeGrip and emits a resized signal."""
        self.resized.emit()

    def resizeEvent(self, event):
        """Overload of the base resizeEvent."""
        self.setGeometry(self.pos().x(), self.pos().y(), self.width(), self.height())
        rectf = QtCore.QRectF(self.geometry())
        self.parent().updateScene([rectf])


class AnnotationGraphicsView(QtWidgets.QGraphicsView):
    """Custom QGraphicsView for creating and editing annotation bounding boxes."""

    created = QtCore.pyqtSignal(QtCore.QRectF)
    resized = QtCore.pyqtSignal(QtCore.QRectF)

    def __init__(self, parent=None):
        """Class init function."""
        QtWidgets.QGraphicsView.__init__(self, parent)
        self.points = []
        self.graphics_items = []
        self.bbox_editor = BBoxWidget(self)
        self.bbox_editor_last_rect = QtCore.QRectF()
        self.bbox = QtCore.QRectF()
        self.bbox_editor.resized.connect(self.bbox_resized)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)
        self.active_brush = QtGui.QBrush(QtCore.Qt.yellow, QtCore.Qt.SolidPattern)
        self.active_pen = QtGui.QPen(self.active_brush, 2)

    def get_bbox(self):
        """Map the ROI location from scene coordinates to image coordinates.

        Returns:
            QRectF: The location of the ROI in image coordinates.
        """
        if self.bbox_editor is not None:
            rect = self.mapToScene(self.bbox_editor.pos().x(), self.bbox_editor.pos().y(), self.bbox_editor.width(), self.bbox_editor.height()).boundingRect()
            adjusted = False
            # Check to see if ROI is completely on the scene, if not adjust to fit on scene.
            if rect.left() < 0:
                rect.setLeft(0.0)
                adjusted = True
            if rect.top() < 0:
                rect.setTop(0.0)
                adjusted = True
            if rect.right() > self.sceneRect().right():
                rect.setRight(self.sceneRect().right())
                adjusted = True
            if rect.bottom() > self.sceneRect().bottom():
                rect.setBottom(self.sceneRect().bottom())
                adjusted = True
            if adjusted:
                rect2 = self.mapFromScene(rect).boundingRect()
                self.bbox_editor.setGeometry(rect2.left(), rect2.top(), rect2.width(), rect2.height())
            self.bbox_editor_last_rect = rect
        return rect

    def mousePressEvent(self, event):
        """Overload of the mousePressEvent that stores mouse click positions in a list."""
        if len(self.scene().items()) > 0:
            point = self.mapToScene(event.pos())
            self.graphics_items.append(self.scene().addEllipse(QtCore.QRectF(point.x() - 5, point.y() - 5, 11, 11), self.active_pen, self.active_brush))
            self.points.append(event.pos())

    def mouseReleaseEvent(self, event):
        """Overload of the MouseReleaseEvent that will calculate the bounding box when four points are available."""
        x_min = 100000000
        y_min = 100000000
        x_max = 0
        y_max = 0
        if len(self.points) == 4:
            for point in self.points:
                x_min = min(x_min, point.x())
                x_max = max(x_max, point.x())
                y_min = min(y_min, point.y())
                y_max = max(y_max, point.y())
            for item in self.graphics_items:
                self.scene().removeItem(item)
            self.graphics_items = []
            self.bbox_editor.setGeometry(x_min, y_min, x_max - x_min, y_max - y_min)
            self.bbox_editor.show()
            self.created.emit(self.get_bbox())
            self.points = []

    def bbox_resized(self):
        """(Slot) Received bbox resized signal and emits another resize signal."""
        self.resized.emit(self.get_bbox())

    def resizeEvent(self, event):
        if self.bbox_editor.isVisible():
            self.show_bbox_editor(self.bbox_editor_last_rect)

    def show_bbox_editor(self, reference_rect):
        """Redisplay the ROI editor.

        Args:
            reference_rect (QRectF): The geometry to use when redisplaying the ROI editor.
        """
        rect = self.mapFromScene(reference_rect).boundingRect()
        self.bbox_editor.setGeometry(rect.left(), rect.top(), rect.width(), rect.height())
        self.bbox_editor.show()
