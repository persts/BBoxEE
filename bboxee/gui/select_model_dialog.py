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
import os
import sys
from PyQt6 import QtCore, QtWidgets, QtGui, uic

if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
else:
    bundle_dir = os.path.dirname(__file__)
DIALOG, _ = uic.loadUiType(os.path.join(bundle_dir, 'select_model_dialog.ui'))


class SelectModelDialog(QtWidgets.QDialog, DIALOG):
    """Helper widget to select and load model."""

    selected = QtCore.pyqtSignal(QtCore.QThread)

    def __init__(self, parent=None):
        """Class init function."""
        QtWidgets.QDialog.__init__(self)
        self.setupUi(self)
        self.setWindowTitle('Select Model')
        self.last_dir = '.'

        self.pushButtonLabelMapV2.clicked.connect(self.get_label_map_2)
        self.label_map = None

        self.pushButtonTFModel.clicked.connect(self.get_saved_model)
        self.pushButtonYolov5ModelFile.clicked.connect(self.get_yolov5_model)
        self.pushButtonYolov9ModelFile.clicked.connect(self.get_yolov9_model)
        self.model = None

        self.pushButtonTFV2.clicked.connect(self.tensorflow_v2_saved_model)
        self.pushButtonYolov5.clicked.connect(self.yolov5_model)
        self.pushButtonYolov9.clicked.connect(self.yolov9_model)

    def set_label(self, label, text):
        qfm = QtGui.QFontMetrics(label.font())
        width = label.width() - 2
        clipped = qfm.elidedText(text, QtCore.Qt.TextElideMode.ElideMiddle, width)
        label.setText(clipped)
        label.raw_text = text

    def tensorflow_v2_saved_model(self):
        """Load a saved model and label map."""
        self.pushButtonTFV2.setDisabled(True)
        self.pushButtonLabelMapV2.setDisabled(True)
        self.pushButtonTFModel.setDisabled(True)
        try:
            import tensorflow as tf
            if tf.__version__[0] == '1':
                raise ModuleNotFoundError('')
            from bboxee.annotator.tensorflow_v2_saved import Annotator
            model = self.labelTFModel.raw_text
            label_map = self.labelLabelMapV2.raw_text
            self.annotator = Annotator(model, label_map)
            self.selected.emit(self.annotator)
            self.hide()
        except ModuleNotFoundError:
            message = 'Required TensorFlow modules not found.'
            QtWidgets.QMessageBox.critical(self, 'Export', message)
        self.pushButtonTFV2.setDisabled(False)
        self.pushButtonLabelMapV2.setDisabled(False)
        self.pushButtonTFModel.setDisabled(False)

    def yolov5_model(self):
        """Load YOLOv5 Model"""
        self.pushButtonYolov5ModelFile.setDisabled(True)
        try:
            from bboxee.annotator.yolo_v5 import Annotator
            model = self.labelYolov5ModelFile.raw_text
            self.annotator = Annotator(model, self.spinBoxImageSize.value(), self.spinBoxStride.value())
            self.selected.emit(self.annotator)
            self.hide()
        except ModuleNotFoundError:
            message = 'Required YOLOv5 modules not found.'
            QtWidgets.QMessageBox.critical(self, 'Export', message)
        self.pushButtonYolov5ModelFile.setEnabled(True)

    def yolov9_model(self):
        """Load YOLOv9 Model"""
        self.pushButtonYolov9ModelFile.setDisabled(True)
        try:
            from bboxee.annotator.yolo_v9 import Annotator
            model = self.labelYolov9ModelFile.raw_text
            self.annotator = Annotator(model)
            self.selected.emit(self.annotator)
            self.hide()
        except ModuleNotFoundError:
            message = 'Required YOLOv9 modules not found.'
            QtWidgets.QMessageBox.critical(self, 'Export', message)
        self.pushButtonYolov9ModelFile.setEnabled(True)

    # Helper functions

    def get_label_map_2(self):
        file_name = (QtWidgets.
                     QFileDialog.
                     getOpenFileName(self,
                                     'Select Label Map',
                                     self.last_dir, 'Label Map (*.pbtxt *.txt)'))
        if file_name[0] != '':
            self.set_label(self.labelLabelMapV2, file_name[0])
            self.last_dir = os.path.split(file_name[0])[0]
            self.pushButtonTFModel.setDisabled(False)

    def get_saved_model(self):
        directory = (QtWidgets.
                     QFileDialog.
                     getExistingDirectory(self,
                                          'Select Saved Model Directory',
                                          self.last_dir))
        if directory != '':
            self.set_label(self.labelTFModel, directory)
            self.last_dir = directory
            self.pushButtonTFV2.setDisabled(False)

    def get_yolov5_model(self):
        file_name = (QtWidgets.
                     QFileDialog.
                     getOpenFileName(self,
                                     'Select YOLOv5 Model',
                                     self.last_dir, '(*.pt)'))
        if file_name[0] != '':
            self.set_label(self.labelYolov5ModelFile, file_name[0])
            self.last_dir = os.path.split(file_name[0])[0]
            self.pushButtonYolov5.setDisabled(False)

    def get_yolov9_model(self):
        file_name = (QtWidgets.
                     QFileDialog.
                     getOpenFileName(self,
                                     'Select YOLOv9 Model',
                                     self.last_dir, '(*.pt)'))
        if file_name[0] != '':
            self.set_label(self.labelYolov9ModelFile, file_name[0])
            self.last_dir = os.path.split(file_name[0])[0]
            self.pushButtonYolov9.setDisabled(False)
