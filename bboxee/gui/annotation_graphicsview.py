# -*- coding: utf-8 -*-
#
# Bounding Box Editor and Exporter (BBoxEE)
# Author: Peter Ersts (ersts@amnh.org)
#
# --------------------------------------------------------------------------
#
# This file is part of Animal Detection Network's (Andenet)
# Bounding Box Editor and Exporter (BBoxEE)
#
# BBoxEE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BBoxEE is distributed in the hope that it will be useful,
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

        self.img_size = (0, 0)
        self.bboxes = []
        self.graphics_scene = QtWidgets.QGraphicsScene()
        self.setScene(self.graphics_scene)

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

    def resize(self):
        bounding_rect = self.graphics_scene.itemsBoundingRect()
        self.fitInView(bounding_rect, QtCore.Qt.KeepAspectRatio)
        self.setSceneRect(bounding_rect)

    def load_image(self, array, img_size):

        self.points = []
        self.graphics_items = []
        self.selected_bbox = None
        self.graphics_scene.clear()
        self.bboxes = []
        self.img_size = img_size # TODO: get this from array


        bpl = int(array.nbytes / array.shape[0])
        if array.shape[2] == 4:
            self.qt_image = QtGui.QImage(array.data,
                                         array.shape[1],
                                         array.shape[0],
                                         QtGui.QImage.Format_RGBA8888)
        else:
            self.qt_image = QtGui.QImage(array.data,
                                         array.shape[1],
                                         array.shape[0],
                                         bpl,
                                         QtGui.QImage.Format_RGB888)

        self.graphics_scene.addPixmap(QtGui.QPixmap.fromImage(self.qt_image))

        self.resize()
        #self.setSceneRect(self.graphics_scene.itemsBoundingRect())

    def display_bboxes(self, annotations, selected_row, display_details=False):

        if self.bboxes:
            for bbox in self.bboxes:
                self.graphics_scene.removeItem(bbox)
            self.bboxes = []

        width = self.img_size[0]
        height = self.img_size[1]


        for index, annotation in enumerate(annotations):

            bbox = annotation['bbox']

            x = bbox['xmin'] * width
            y = bbox['ymin'] * height

            top_left = QtCore.QPointF(x, y)

            x = bbox['xmax'] * width
            y = bbox['ymax'] * height

            bottom_right = QtCore.QPointF(x, y)

            rect = QtCore.QRectF(top_left, bottom_right)
            if index == selected_row:
                pen = QtGui.QPen(QtGui.QBrush(QtCore.Qt.red,
                                              QtCore.Qt.SolidPattern), 3)
            else:
                pen = QtGui.QPen(QtGui.QBrush(QtCore.Qt.yellow,
                                              QtCore.Qt.SolidPattern), 3)
                if (annotation['created_by'] == 'machine' and
                        annotation['updated_by'] == ''):
                    pen = QtGui.QPen(QtGui.QBrush(QtCore.Qt.green,
                                                  QtCore.Qt.SolidPattern),
                                     3)
            graphics_item = self.graphics_scene.addRect(rect, pen)

            # display annotation data center in bounding box.
            if display_details:
                font = QtGui.QFont()
                font.setPointSize(int(rect.width() * 0.065))
                s = "{}\nTruncated: {}\nOccluded: {}\nDifficult: {}"
                content = (s.
                           format(annotation['label'],
                                  annotation['truncated'],
                                  annotation['occluded'],
                                  annotation['difficult']))
                text = QtWidgets.QGraphicsTextItem(content)
                text.setFont(font)
                text.setPos(rect.topLeft().toPoint())
                text.setDefaultTextColor(QtCore.Qt.yellow)
                x_offset = text.boundingRect().width() / 2.0
                y_offset = text.boundingRect().height() / 2.0
                x = (rect.width() / 2.0) - x_offset
                y = (rect.height() / 2.0) - y_offset
                text.moveBy(x, y)
                text.setParentItem(graphics_item)
            self.bboxes.append(graphics_item)

            if index == selected_row:
                self.selected_bbox = graphics_item
