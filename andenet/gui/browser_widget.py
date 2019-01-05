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
# along with this software.  If not, see <http://www.gnu.org/licenses/>.
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
        self.labels = None
        self.metadata = None
        self.image_data = None
        self.current_record = 0
        self.exporter = None

        self.graphicsScene = QtWidgets.QGraphicsScene()
        self.graphicsView.setScene(self.graphicsScene)

        self.pushButtonSelectDirectory.clicked.connect(self.load)
        self.pushButtonNext.clicked.connect(self.next)
        self.pushButtonPrevious.clicked.connect(self.previous)
        self.pushButtonExport.clicked.connect(self.export)
        self.lineEditCurrentRecord.editingFinished.connect(self.jump_to_image)
        self.checkBoxDisplayAnnotationData.clicked.connect(self.display)

    def display(self):
        """Display image in widget, JSON metadata, and labeled annotation boxes."""
        data = self.metadata[self.current_record - 1]
        self.lineEditCurrentRecord.setText(str(self.current_record))
        self.textBrowser.setText(json.dumps(data, indent=4, sort_keys=True))
        # Seek to the start of the data block then read in the image data
        self.image_data.seek(data['image_data']['start'])
        raw = self.image_data.read(data['image_data']['size'])
        # Turn into a virtual file stream and load the image as if from disk
        file = io.BytesIO(raw)
        img = Image.open(file)
        width = img.size[0]
        height = img.size[1]
        # Display the image in the graphhics view
        self.qImage = ImageQt.ImageQt(img)
        self.graphicsScene.clear()
        self.graphicsScene.addPixmap(QtGui.QPixmap.fromImage(self.qImage))
        self.graphicsView.fitInView(self.graphicsScene.itemsBoundingRect(), QtCore.Qt.KeepAspectRatio)
        self.graphicsView.setSceneRect(self.graphicsScene.itemsBoundingRect())
        # Add bounding boxes and labels.
        for annotation in data['annotations']:
            bbox = annotation['bbox']
            top_left = QtCore.QPointF(bbox['xmin'] * width, bbox['ymin'] * height)
            bottom_right = QtCore.QPointF(bbox['xmax'] * width, bbox['ymax'] * height)
            rect = QtCore.QRectF(top_left, bottom_right)
            graphics_item = self.graphicsScene.addRect(rect, QtGui.QPen(QtGui.QBrush(QtCore.Qt.yellow, QtCore.Qt.SolidPattern), 3))
            # display annotation data center in bounding box.
            if self.checkBoxDisplayAnnotationData.isChecked():
                font = QtGui.QFont()
                font.setPointSize(int(rect.width() * 0.065))
                content = "{}\nTruncated: {}\nOccluded: {}\nDifficult: {}".format(annotation['label'], annotation['truncated'], annotation['occluded'], annotation['difficult'])
                text = QtWidgets.QGraphicsTextItem(content)
                text.setFont(font)
                text.setPos(rect.topLeft().toPoint())
                text.setDefaultTextColor(QtCore.Qt.yellow)
                x_offset = text.boundingRect().width() / 2.0
                y_offset = text.boundingRect().height() / 2.0
                text.moveBy((rect.width() / 2.0) - x_offset, (rect.height() / 2.0) - y_offset)
                text.setParentItem(graphics_item)

    def export(self):
        export_to = self.comboBoxFormat.currentText()
        validation_split = self.doubleSpinBoxSplit.value()
        module_loaded = False
        if export_to == 'Tensorflow Record':
            try:
                from andenet.exporter.tfrecord import Exporter
                module_loaded = True
            except ModuleNotFoundError:
                QtWidgets.QMessageBox.critical(self, 'Export', 'Required Tensorflow modules not found.\n\nPlease review install requirements.')
        elif export_to == 'YOLOv3 Format':
            try:
                from andenet.exporter.yolo import Exporter
                module_loaded = True
            except ModuleNotFoundError:
                QtWidgets.QMessageBox.critical(self, 'Export', 'Required Torch or Yolov3 modules not found.\n\nPlease review install requirements.')
        if module_loaded:
            directory = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select destination')
            if directory != '':
                self.exporter = Exporter(directory, self.metadata, self.image_data, self.labels, validation_split)
                self.progressBar.setRange(0, len(self.metadata))
                self.exporter.progress.connect(self.progressBar.setValue)
                self.exporter.exported.connect(self.export_finished)
                self.exporter.start()

    def export_finished(self):
        """(Slot) Re enable export button after export has finished."""
        self.pushButtonExport.setEnabled(True)

    def jump_to_image(self):
        """(Slot) Jump to image after editing has finished in line edit."""
        try:
            image_number = int(self.lineEditCurrentRecord.text())
            if image_number <= len(self.metadata) and image_number >= 1:
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
            self.image_data = open(directory + os.path.sep + 'images.bin', 'rb')
            file = open(directory + os.path.sep + 'metadata.json')
            obj = json.load(file)
            self.metadata = obj['metadata']
            self.labels = obj['labels']
            file.close()
            self.current_record = 1
            self.labelTotal.setText('of ' + str(len(self.metadata)))
            self.display()
            self.pushButtonExport.setEnabled(True)

    def next(self):
        """(Slot) Load next record."""
        if self.metadata is not None and self.current_record < len(self.metadata):
            self.current_record += 1
            self.display()

    def previous(self):
        """(Slot) Load previous record."""
        if self.metadata is not None and self.current_record > 1:
            self.current_record -= 1
            self.display()

    def resizeEvent(self, event):
        """Override of virtual function to resize contents of graphics view when widget is resized."""
        self.graphicsView.fitInView(self.graphicsScene.itemsBoundingRect(), QtCore.Qt.KeepAspectRatio)
