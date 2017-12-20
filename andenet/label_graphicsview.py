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
# along with Point Class Assigner.  If not, see <http://www.gnu.org/licenses/>.
#
# --------------------------------------------------------------------------
from PyQt5 import QtWidgets, QtCore


class RoiSizeGrip(QtWidgets.QSizeGrip):
    resized = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        QtWidgets.QSizeGrip.__init__(self, parent)

    def mouseReleaseEvent(self, theEvent):
        self.resized.emit()


class RoiWidget(QtWidgets.QFrame):
    resized = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        QtWidgets.QFrame.__init__(self, parent)
        self.setWindowFlags(QtCore.Qt.SubWindow)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("RoiWidget { border: 1px solid rgb(255, 0, 255);}")
        self.grip1 = RoiSizeGrip(self)
        self.grip2 = RoiSizeGrip(self)
        self.grip1.resized.connect(self.resizeComplete)
        self.layout.addWidget(self.grip1, 0, QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.grip2.resized.connect(self.resizeComplete)
        self.layout.addWidget(self.grip2, 0, QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)
        self.hide()

    def resizeComplete(self):
        self.resized.emit()

    def resizeEvent(self, theEvent):
        self.setGeometry(self.pos().x(), self.pos().y(), self.width(), self.height())


class LabelGraphicsView(QtWidgets.QGraphicsView):
    roiCreated = QtCore.pyqtSignal(QtCore.QRectF)
    roiResized = QtCore.pyqtSignal(QtCore.QRectF)

    def __init__(self, parent=None):
        QtWidgets.QGraphicsView.__init__(self, parent)
        self.points = []
        self.roiSelector = RoiWidget(self)
        self.roi = QtCore.QRectF()
        self.roiSelector.resized.connect(self.resizeRoi)

    def getRoi(self):
        if self.roiSelector is not None:
            rect = self.mapToScene(self.roiSelector.pos().x(), self.roiSelector.pos().y(), self.roiSelector.width(), self.roiSelector.height()).boundingRect()
            adjusted = False
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
                self.roiSelector.setGeometry(rect2.left(), rect2.top(), rect2.width(), rect2.height())
        return rect

    def mousePressEvent(self, theEvent):
        if len(self.scene().items()) > 0:
            self.points.append(theEvent.pos())

    def mouseReleaseEvent(self, theEvent):
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
            self.roiSelector.setGeometry(x_min, y_min, x_max - x_min, y_max - y_min)
            self.roiSelector.show()
            self.roiCreated.emit(self.getRoi())
            self.points = []

    def resizeRoi(self):
        self.roiResized.emit(self.getRoi())

    def showRoiSelector(self, theRect):
        rect = self.mapFromScene(theRect).boundingRect()
        self.roiSelector.setGeometry(rect.left(), rect.top(), rect.width(), rect.height())
        self.roiSelector.show()
