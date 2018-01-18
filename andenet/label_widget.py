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
import glob
import json
import copy
import datetime
import numpy as np
from PIL import Image, ImageQt
from .label_assistant import LabelAssistant
from PyQt5 import QtCore, QtGui, QtWidgets, uic

LABEL, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'label_widget.ui'))


class LabelWidget(QtWidgets.QWidget, LABEL):
    """Widget for annotating images."""

    def __init__(self, parent=None):
        """Class init function."""
        QtWidgets.QWidget.__init__(self)
        self.setupUi(self)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setWindowTitle('Annotation Tool')
        self.directory = '.'
        self.current_file_name = ''
        self.bboxes = []
        self.selected_row = -1
        self.current_image = 1
        self.image_list = []
        self.mask = None
        self.data = self._baseSchema()
        self.dirty = False
        self.assistant = LabelAssistant(self)
        self.assistant.submitted.connect(self.update_annotation)

        self.graphicsScene = QtWidgets.QGraphicsScene()
        self.graphicsView.setScene(self.graphicsScene)
        self.graphicsView.created.connect(self.bbox_created)
        self.graphicsView.resized.connect(self.update_bbox)

        self.pushButtonAnnotatedNext.clicked.connect(self.next_annotated_image)
        self.pushButtonAnnotatedPrevious.clicked.connect(self.previous_annotated_image)
        self.pushButtonDirectory.clicked.connect(self.load_from_directory)
        self.pushButtonLabelFile.clicked.connect(self.load_from_file)
        self.pushButtonNext.clicked.connect(self.next_image)
        self.pushButtonPrevious.clicked.connect(self.previous_image)
        self.pushButtonSave.clicked.connect(self.save)
        self.pushButtonSelectMask.clicked.connect(self.select_mask)
        self.lineEditCurrentImage.editingFinished.connect(self.jump_to_image)
        self.tableWidgetLabels.selectionModel().currentRowChanged.connect(self.row_changed)
        self.tableWidgetLabels.cellChanged.connect(self.cell_changed)
        self.tableWidgetLabels.cellDoubleClicked.connect(self.delete_row)

        self.tableWidgetLabels.horizontalHeader().setStretchLastSection(False)
        self.tableWidgetLabels.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)

    def _annotationSchema(self):
        return {'bbox': None, 'label': 'N/A', 'occluded': 'N', 'truncated': 'N', 'difficult': 'N'}

    def _baseSchema(self):
        return {'directory': '', 'mask': None, 'mask_name': '', 'images': {}, 'schema': 'v1'}

    def cell_changed(self, row, column):
        """(Slot) Update annotation data on change."""
        text = self.tableWidgetLabels.item(row, column).text()
        header = self.tableWidgetLabels.horizontalHeaderItem(column).text().lower()
        if header == 'occluded' or header == 'truncated' or header == 'difficult':
            if text in ['Y', 'y', 'N', 'n']:
                text = text.upper()
            else:
                text = self.data['images'][self.current_file_name][row][header]
                self.tableWidgetLabels.setItem(row, column, QtWidgets.QTableWidgetItem(text))
        else:
            text = text.lower()
        self.data['images'][self.current_file_name][row][header] = text
        self.set_dirty(True)

    def delete_row(self, row, column):
        """(Slot) Delete row from table and associated metadata when double clicked."""
        self.tableWidgetLabels.selectionModel().blockSignals(True)
        self.tableWidgetLabels.removeRow(row)
        self.graphicsView.bbox_editor.hide()
        del self.data['images'][self.current_file_name][row]
        self.tableWidgetLabels.selectionModel().blockSignals(False)
        self.selected_row = -1
        self.display_bboxes()

    def display_annotation_data(self):
        """Display annotation data in table."""
        self.tableWidgetLabels.setRowCount(0)
        self.tableWidgetLabels.blockSignals(True)
        if self.current_file_name in self.data['images']:
            rows = len(self.data['images'][self.current_file_name])
            self.tableWidgetLabels.setRowCount(rows)
            for row in range(rows):
                self.tableWidgetLabels.setItem(row, 0, QtWidgets.QTableWidgetItem(self.data['images'][self.current_file_name][row]['label']))
                self.tableWidgetLabels.setItem(row, 1, QtWidgets.QTableWidgetItem(self.data['images'][self.current_file_name][row]['truncated']))
                self.tableWidgetLabels.setItem(row, 2, QtWidgets.QTableWidgetItem(self.data['images'][self.current_file_name][row]['occluded']))
                self.tableWidgetLabels.setItem(row, 3, QtWidgets.QTableWidgetItem(self.data['images'][self.current_file_name][row]['difficult']))
        # self.tableWidgetLabels.resizeColumnToContents(0)
        self.tableWidgetLabels.blockSignals(False)

    def display_bboxes(self):
        """Display bboxes in graphics scene."""
        if len(self.bboxes) > 0:
            for bbox in self.bboxes:
                self.graphicsScene.removeItem(bbox)
            self.bboxes = []
        if self.current_file_name in self.data['images']:
            for i in range(len(self.data['images'][self.current_file_name])):
                annotation = self.data['images'][self.current_file_name][i]
                if i == self.selected_row:
                    rect = QtCore.QRectF(annotation['bbox'][0], annotation['bbox'][1], annotation['bbox'][2], annotation['bbox'][3])
                    self.graphicsView.show_bbox_editor(rect)
                else:
                    rect = QtCore.QRectF(annotation['bbox'][0], annotation['bbox'][1], annotation['bbox'][2], annotation['bbox'][3])
                    rect = self.graphicsScene.addRect(rect, QtGui.QPen(QtGui.QBrush(QtCore.Qt.yellow, QtCore.Qt.SolidPattern), 3))
                    self.bboxes.append(rect)

    def jump_to_image(self):
        """(Slot) Just to a specific image when when line edit changes."""
        try:
            imageNum = int(self.lineEditCurrentImage.text())
            if imageNum <= len(self.image_list) and imageNum >= 1:
                self.current_image = imageNum
                self.load_image()
            else:
                self.lineEditCurrentImage.setText(str(self.current_image))
        except ValueError:
            self.lineEditCurrentImage.setText(str(self.current_image))

    def load_from_directory(self):
        """(Slot) Load image data from directory."""
        if self.dirty:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setText('Annotations have been modified.')
            msgBox.setInformativeText('Do you want to save your changes?')
            msgBox.setStandardButtons(QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Save)
            response = msgBox.exec()
            if response == QtWidgets.QMessageBox.Save:
                self.save()
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Directory', self.directory)
        if directory != '':
            self.directory = directory
            self.data = self._baseSchema()
            # self.data['directory'] = self.directory
            self.mask = None
            self.load_image_list()
            self.pushButtonSelectMask.setEnabled(True)

    def load_from_file(self):
        """(Slot) Load existing annotation data from file."""
        if self.dirty:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setText('Annotations have been modified.')
            msgBox.setInformativeText('Do you want to save your changes?')
            msgBox.setStandardButtons(QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Save)
            response = msgBox.exec()
            if response == QtWidgets.QMessageBox.Save:
                self.save()
        file_name = QtWidgets.QFileDialog.getOpenFileName(self, 'Load Annotations', self.directory, 'Andenet (*.adn)')
        if file_name[0] != '':
            file = open(file_name[0], 'r')
            self.data = json.load(file)
            file.close()
            self.directory = os.path.split(file_name[0])[0]
            # self.directory = self.data['directory']
            if self.data['mask'] is not None:
                tmp = np.array(self.data['mask'], dtype='uint8')
                self.mask = np.dstack((tmp, tmp, tmp))
            else:
                self.mask = None
            self.load_image_list()
            self.set_dirty(False)
            self.pushButtonSelectMask.setEnabled(True)

    def load_image(self):
        """Load image into graphics scene."""
        self.graphicsView.bbox_editor.hide()
        self.graphicsView.points = []
        self.graphicsScene.clear()
        self.bboxes = []
        self.selected_row = -1
        self.current_file_name = self.image_list[self.current_image - 1]
        file = os.path.join(self.directory, self.current_file_name)
        img = Image.open(file)
        self.current_imageSize = img.size
        if self.mask is not None:
            img = np.array(img) * self.mask
            img = Image.fromarray(img)

        self.qImage = ImageQt.ImageQt(img)
        self.graphicsScene.addPixmap(QtGui.QPixmap.fromImage(self.qImage))
        img.close()
        img = None
        self.graphicsView.fitInView(self.graphicsScene.itemsBoundingRect(), QtCore.Qt.KeepAspectRatio)
        self.graphicsView.setSceneRect(self.graphicsScene.itemsBoundingRect())
        self.display_bboxes()
        self.display_annotation_data()
        self.graphicsView.setFocus()

    def load_image_list(self):
        """Glob the image files and save to image list."""
        if self.directory != '':
            self.image_list = []
            self.directory += os.path.sep
            files = glob.glob(self.directory + '*')
            image_type = [".jpg", ".jpeg", ".png"]
            for file in files:
                ext = os.path.splitext(file)[1]
                if ext.lower() in image_type:
                    name = os.path.basename(file)
                    self.image_list.append(name)
            self.image_list = sorted(self.image_list)
            self.current_image = 1
            self.labelImages.setText('of ' + str(len(self.image_list)))
            self.lineEditCurrentImage.setText('1')
            self.load_image()

    def next_annotated_image(self):
        """(Slot) Jump to the next image that has been annotated."""
        tmp_list = sorted(self.data['images'].keys())
        current = self.image_list[self.current_image - 1]
        if current in tmp_list:
            index = tmp_list.index(current)
            if index + 1 < len(tmp_list):
                self.current_image = self.image_list.index(tmp_list[index + 1]) + 1
        else:
            index = 0
            while(index < len(tmp_list) and tmp_list[index] < current):
                index += 1
            if index < len(tmp_list):
                self.current_image = self.image_list.index(tmp_list[index]) + 1
        self.lineEditCurrentImage.setText(str(self.current_image))
        self.load_image()

    def next_image(self):
        """(Slot) Load the next image."""
        if self.current_image < len(self.image_list):
            self.current_image += 1
            self.lineEditCurrentImage.setText(str(self.current_image))
            self.load_image()

    def previous_annotated_image(self):
        """(Slot) Jump to the previous image that has been annotated."""
        tmp_list = sorted(self.data['images'].keys())
        current = self.image_list[self.current_image - 1]
        if current in tmp_list:
            index = tmp_list.index(current)
            if index - 1 >= 0:
                self.current_image = self.image_list.index(tmp_list[index - 1]) + 1
        else:
            index = len(tmp_list) - 1
            while(index >= 0 and tmp_list[index] > current):
                index -= 1
            if index >= 0:
                self.current_image = self.image_list.index(tmp_list[index]) + 1
        self.lineEditCurrentImage.setText(str(self.current_image))
        self.load_image()

    def previous_image(self):
        """(Slot) Load the previous image."""
        if self.current_image > 1:
            self.current_image -= 1
            self.lineEditCurrentImage.setText(str(self.current_image))
            self.load_image()

    def resizeEvent(self, event):
        """Overload resizeEvent to fit image in graphics view."""
        self.graphicsView.fitInView(self.graphicsScene.itemsBoundingRect(), QtCore.Qt.KeepAspectRatio)
        # self.display_bboxes()

    def bbox_created(self, rect):
        """(Slot) save the newly created bbox and display it."""
        if rect.width() > 0 and rect.height() > 0:
            self.set_dirty(True)
            if self.current_file_name not in self.data['images']:
                self.data['images'][self.current_file_name] = []
            metadata = self._annotationSchema()
            metadata['bbox'] = [rect.x(), rect.y(), rect.width(), rect.height()]
            self.data['images'][self.current_file_name].append(metadata)
            self.display_annotation_data()
            self.selected_row = self.tableWidgetLabels.rowCount() - 1
        self.display_bboxes()
        pos = self.mapToGlobal(self.graphicsView.pos())
        self.assistant.move(pos.x() + (self.graphicsView.width() - self.assistant.width()) / 2, pos.y() + (self.graphicsView.height() - self.assistant.height()) / 2)
        self.assistant.show()

    def row_changed(self, model_index):
        """(Slot) Update bbox editor to correspond with the currently selected row."""
        self.selected_row = model_index.row()
        self.display_bboxes()

    def save(self):
        """(Slot) Save the annotations to disk."""
        file_name = QtWidgets.QFileDialog.getSaveFileName(self, 'Save Annotations', self.directory + 'untitled.adn', 'Andenet (*.adn)')
        if file_name[0] != '':
            self.data['timestamp'] = '{:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now())
            file = open(file_name[0], 'w')
            json.dump(self.data, file)
            file.close()
            self.set_dirty(False)

    def select_mask(self):
        """(Slot) Select mask from disk."""
        filter_string = str(self.current_imageSize[0]) + '_' + str(self.current_imageSize[1]) + '.png'
        file = QtWidgets.QFileDialog.getOpenFileName(self, 'Select Mask', './masks/', 'PNG (*' + filter_string + ')')
        if file[0] != '':
            img = Image.open(file[0])
            if self.current_imageSize == img.size:
                img = np.array(img)
                img = np.clip(img, 0, 1)
                self.mask = img
                mask = np.dsplit(img, 3)
                mask = mask[0]
                mask = mask.reshape(mask.shape[:-1])
                self.data['mask'] = mask.tolist()
                self.data['mask_name'] = os.path.split(file[0])[1]
                self.set_dirty(True)
            else:
                print('TODO: Display Message')
                self.mask = None
        self.load_image()

    def set_dirty(self, is_dirty):
        """Set dirty flag.

        Args:
            is_dirty (bool): Is the data dirty.
        """
        if is_dirty:
            self.dirty = True
            self.pushButtonSave.setEnabled(True)
        else:
            self.dirty = False
            self.pushButtonSave.setEnabled(False)

    def update_annotation(self, annotation_data):
        """(Slot) Update table with data submitted from assistant widget."""
        for key in annotation_data.keys():
            self.data['images'][self.current_file_name][self.selected_row][key] = annotation_data[key]
        self.display_annotation_data()

    def update_bbox(self, rect):
        """(Slot) Store the new geometry for the active bbox."""
        if rect.width() > 0 and rect.height() > 0:
            self.set_dirty(True)
            self.data['images'][self.current_file_name][self.selected_row]['bbox'] = [rect.x(), rect.y(), rect.width(), rect.height()]
