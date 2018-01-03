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
import os
import io
import json
from PIL import Image, ImageQt
from PyQt5 import QtCore, QtGui, QtWidgets, uic

BROWSER, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'browser_widget.ui'))


class BrowserWidget(QtWidgets.QWidget, BROWSER):
    """Browser to view data stored in the Andenet format."""

    def __init__(self, parent=None):
        """Class init function."""
        QtWidgets.QWidget.__init__(self)
        self.setupUi(self)
        self.data = None
        self.images = None
        self.current_record = 0

        self.graphicsScene = QtWidgets.QGraphicsScene()
        self.graphicsView.setScene(self.graphicsScene)

        self.pushButtonSelectDirectory.clicked.connect(self.load)
        self.pushButtonNext.clicked.connect(self.next)
        self.pushButtonPrevious.clicked.connect(self.previous)
        self.lineEditCurrentRecord.editingFinished.connect(self.jumpToImage)

    def display(self):
        """Display image in widget, JSON metadata, and labeled annotation boxes."""
        data = self.data[self.current_record - 1]
        self.lineEditCurrentRecord.setText(str(self.current_record))
        self.textBrowser.setText(json.dumps(data, indent=4, sort_keys=True))
        self.images.seek(data['image_data']['start'])
        raw = self.images.read(data['image_data']['size'])
        file = io.BytesIO(raw)
        img = Image.open(file)
        self.qImage = ImageQt.ImageQt(img)
        self.graphicsScene.clear()
        self.graphicsScene.addPixmap(QtGui.QPixmap.fromImage(self.qImage))
        self.graphicsView.fitInView(self.graphicsScene.itemsBoundingRect(), QtCore.Qt.KeepAspectRatio)
        self.graphicsView.setSceneRect(self.graphicsScene.itemsBoundingRect())
        for annotation in data['annotations']:
            rect = QtCore.QRectF(annotation['bbox'][0], annotation['bbox'][1], annotation['bbox'][2], annotation['bbox'][3])
            graphics_item = self.graphicsScene.addRect(rect, QtGui.QPen(QtGui.QBrush(QtCore.Qt.magenta, QtCore.Qt.SolidPattern), 3))
            font = QtGui.QFont()
            font.setPointSize(60)
            text = QtWidgets.QGraphicsTextItem(annotation['label'])
            text.setFont(font)
            text.setPos(rect.topLeft().toPoint())
            text.setDefaultTextColor(QtCore.Qt.magenta)
            text.moveBy(10., 0.)
            text.setParentItem(graphics_item)

    def jumpToImage(self):
        """(Slot) Just to image after editing has finished in line edit."""
        try:
            image_number = int(self.lineEditCurrentRecord.text())
            if image_number <= len(self.data) and image_number >= 1:
                self.current_record = image_number
                self.display()
            else:
                self.lineEditCurrentRecord.setText(str(self.current_record))
        except ValueError:
            self.lineEditCurrentRecord.setText(str(self.current_record))

    def load(self):
        """(Slot) Load metadata file."""
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select destination')
        if directory != '':
            self.images = open(directory + os.path.sep + 'images.bin', 'rb')
            file = open(directory + os.path.sep + 'metadata.json')
            self.data = json.load(file)
            file.close()
            self.current_record = 1
            self.labelTotal.setText('of ' + str(len(self.data)))
            self.display()

    def next(self):
        """(Slot) Load next record."""
        if self.data is not None and self.current_record < len(self.data):
            self.current_record += 1
            self.display()

    def previous(self):
        """(Slot) Load previous record."""
        if self.data is not None and self.current_record > 1:
            self.current_record -= 1
            self.display()

    def resizeEvent(self, event):
        """Override of virtual function to resize contents of graphics view when widget is resized."""
        self.graphicsView.fitInView(self.graphicsScene.itemsBoundingRect(), QtCore.Qt.KeepAspectRatio)
