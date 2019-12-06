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
import os
import io
import json
import numpy as np
from PIL import Image
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from andenet.gui import CocoDialog
from andenet import schema

BROWSER, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'browser_widget.ui'))


class BrowserWidget(QtWidgets.QWidget, BROWSER):
    """Browser to view data stored in the Andenet format."""

    def __init__(self, icon_size=24, parent=None):
        """Class init function."""
        QtWidgets.QWidget.__init__(self, parent)
        self.setupUi(self)
        self.metadata_file = None
        self.labels = None
        self.metadata = None
        self.image_data = None
        self.current_record = 0
        self.exporter = None
        self.qt_image = None
        self.coco_info = {}

        self.pen = QtGui.QPen(QtGui.QBrush(QtCore.Qt.yellow, QtCore.Qt.SolidPattern), 3)

        self.graphics_scene = QtWidgets.QGraphicsScene()
        self.graphicsView.setScene(self.graphics_scene)

        self.pushButtonNext.clicked.connect(self.next)
        self.pushButtonNext.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pushButtonNext.setIcon(QtGui.QIcon(':/icons/next.svg'))

        self.pushButtonPrevious.clicked.connect(self.previous)
        self.pushButtonPrevious.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pushButtonPrevious.setIcon(QtGui.QIcon(':/icons/previous.svg'))

        self.pushButtonSelectDirectory.clicked.connect(self.load)
        self.pushButtonSelectDirectory.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pushButtonSelectDirectory.setIcon(QtGui.QIcon(':/icons/folder.svg'))

        self.pushButtonFlag.clicked.connect(self.flag)
        self.pushButtonFlag.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pushButtonFlag.setIcon(QtGui.QIcon(':/icons/flag.svg'))

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
        array = np.array(img)
        bpl = int(array.nbytes / array.shape[0])
        if array.shape[2] == 4:
            self.qt_image = QtGui.QImage(array.data, array.shape[1], array.shape[0], QtGui.QImage.Format_RGBA8888)
        else:
            self.qt_image = QtGui.QImage(array.data, array.shape[1], array.shape[0], bpl, QtGui.QImage.Format_RGB888)
        self.graphics_scene.clear()
        self.graphics_scene.addPixmap(QtGui.QPixmap.fromImage(self.qt_image))
        self.graphicsView.fitInView(self.graphics_scene.itemsBoundingRect(), \
            QtCore.Qt.KeepAspectRatio)
        self.graphicsView.setSceneRect(self.graphics_scene.itemsBoundingRect())
        # Set flagged button
        if 'flagged' in data and data['flagged'] == True:
            self.pushButtonFlag.setChecked(True)
            self.pushButtonFlag.setIcon(QtGui.QIcon(':/icons/flagged.svg'))
        else:
            self.pushButtonFlag.setChecked(False)
            self.pushButtonFlag.setIcon(QtGui.QIcon(':/icons/flag.svg'))
        # Add bounding boxes and labels.
        for annotation in data['annotations']:
            bbox = annotation['bbox']
            top_left = QtCore.QPointF(bbox['xmin'] * width, bbox['ymin'] * height)
            bottom_right = QtCore.QPointF(bbox['xmax'] * width, bbox['ymax'] * height)
            rect = QtCore.QRectF(top_left, bottom_right)
            graphics_item = self.graphics_scene.addRect(rect, self.pen)
            # display annotation data center in bounding box.
            if self.checkBoxDisplayAnnotationData.isChecked():
                font = QtGui.QFont()
                font.setPointSize(int(rect.width() * 0.065))
                content = "{}\nTruncated: {}\nOccluded: {}\nDifficult: {}".format( \
                    annotation['label'], annotation['truncated'], \
                    annotation['occluded'], annotation['difficult'])
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
                QtWidgets.QMessageBox.critical(self, 'Export', \
                    'Required Tensorflow modules not found.\n\n' \
                    'Please review install requirements.')
        elif export_to == 'Darknet YOLOv3':
            try:
                from andenet.exporter.yolo import Exporter
                module_loaded = True
            except ModuleNotFoundError:
                QtWidgets.QMessageBox.critical(self, 'Export', \
                    'Required Torch or Yolov3 modules not found.\n\n' \
                    'Please review install requirements.')
        elif export_to == 'COCO':
            from andenet.exporter.coco import Exporter
            module_loaded = True
        if module_loaded:
            directory = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select destination')
            if directory != '':
                self.exporter = Exporter(directory, self.metadata, \
                    self.image_data, self.labels, validation_split)
                if export_to == 'COCO':
                    diag = CocoDialog()
                    diag.exec_()
                    self.exporter.info = diag.info
                self.progressBar.setRange(0, len(self.metadata))
                self.exporter.progress.connect(self.progressBar.setValue)
                self.exporter.exported.connect(self.export_finished)
                self.exporter.start()

    def export_finished(self):
        """(Slot) Re enable export button after export has finished."""
        self.pushButtonExport.setEnabled(True)

    def flag(self):
        if self.metadata is None:
            self.pushButtonFlag.setChecked(False)
            self.pushButtonFlag.setIcon(QtGui.QIcon(':/icons/flag.svg'))
        else:
            if self.pushButtonFlag.isChecked():
                self.pushButtonFlag.setIcon(QtGui.QIcon(':/icons/flagged.svg'))
                data = self.metadata[self.current_record - 1]['flagged'] = True
            else:
                self.pushButtonFlag.setIcon(QtGui.QIcon(':/icons/flag.svg'))
                data = self.metadata[self.current_record - 1]['flagged'] = False
            self.display()
            try:
                package = schema.package()
                package['labels'] = self.labels
                package['metadata'] = self.metadata
                file = open(self.metadata_file, 'w')
                json.dump(package, file)
                file.close()
            except PermissionError:
                msg_box = QtWidgets.QMessageBox()
                msg_box.setWindowTitle('Save Error')
                msg_box.setText('Changes not saved. Permission Error.')
                msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
                msg_box.setDefaultButton(QtWidgets.QMessageBox.Ok)
                msg_box.setMinimumWidth(600)
                msg_box.exec()
                

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
            self.metadata_file = directory + os.path.sep + 'metadata.json'
            file = open(self.metadata_file)
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
        """Override of virtual function to resize contents of graphics view."""
        self.graphicsView.fitInView(self.graphics_scene.itemsBoundingRect(), \
            QtCore.Qt.KeepAspectRatio)
