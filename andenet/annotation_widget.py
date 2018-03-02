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
import datetime
import numpy as np
from PIL import Image, ImageQt
from andenet import schema
from andenet import AnnotationAssistant
from PyQt5 import QtCore, QtGui, QtWidgets, uic
import tensorflow as tf
from utils import label_map_util


LABEL, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'annotation_widget.ui'))


class AnnotationWidget(QtWidgets.QWidget, LABEL):
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
        self.data = schema.annotation_file()
        self.dirty = False
        self.assistant = AnnotationAssistant(self)
        self.assistant.submitted.connect(self.update_annotation)
        self.image = None
        self.detection_graph = tf.Graph()
        self.model_loaded = False

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
        self.pushButtonLoadModel.clicked.connect(self.load_model)
        self.pushButtonAnnotate.clicked.connect(self.annotate)
        self.pushButtonSave.clicked.connect(self.save)
        self.pushButtonSelectMask.clicked.connect(self.select_mask)
        self.lineEditCurrentImage.editingFinished.connect(self.jump_to_image)
        self.tableWidgetLabels.selectionModel().selectionChanged.connect(self.selection_changed)
        self.tableWidgetLabels.cellChanged.connect(self.cell_changed)
        self.tableWidgetLabels.cellDoubleClicked.connect(self.delete_row)
        self.checkBoxDisplayAnnotationData.clicked.connect(self.display_bboxes)

        self.tableWidgetLabels.horizontalHeader().setStretchLastSection(False)
        self.tableWidgetLabels.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)

    def annotate(self):
        """Annotate image using existing model."""
        self.pushButtonAnnotate.setEnabled(False)
        if self.image is not None and self.model_loaded:
            with self.detection_graph.as_default():
                with tf.Session(graph=self.detection_graph) as sess:
                    # Definite input and output Tensors for detection_graph
                    image_tensor = self.detection_graph.get_tensor_by_name('image_tensor:0')
                    # Each box represents a part of the image where a particular object was detected.
                    detection_boxes = self.detection_graph.get_tensor_by_name('detection_boxes:0')
                    # Each score represent how level of confidence for each of the objects.
                    # Score is shown on the result image, together with the class label.
                    detection_scores = self.detection_graph.get_tensor_by_name('detection_scores:0')
                    detection_classes = self.detection_graph.get_tensor_by_name('detection_classes:0')
                    num_detections = self.detection_graph.get_tensor_by_name('num_detections:0')
                    image_np_expanded = np.expand_dims(self.image, axis=0)
                    # Actual detection.
                    (boxes, scores, classes, num) = sess.run([detection_boxes, detection_scores, detection_classes, num_detections], feed_dict={image_tensor: image_np_expanded})
                    boxes = np.squeeze(boxes)
                    scores = np.squeeze(scores)
                    classes = np.squeeze(classes)
                for i in range(len(scores)):
                    if scores[i] > 0.6:
                        bbox = boxes[i]
                        tl = QtCore.QPointF(bbox[1] * self.image.shape[1], bbox[0] * self.image.shape[0])
                        br = QtCore.QPointF(bbox[3] * self.image.shape[1], bbox[2] * self.image.shape[0])
                        self.bbox_created(QtCore.QRectF(tl, br), show_assistant=False)
                        self.update_annotation({'label': self.category_index[classes[i]]['name']})
        self.pushButtonAnnotate.setEnabled(True)

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
                    graphics_item = self.graphicsScene.addRect(rect, QtGui.QPen(QtGui.QBrush(QtCore.Qt.yellow, QtCore.Qt.SolidPattern), 3))
                    # display annotation data center in bounding box.
                    if self.checkBoxDisplayAnnotationData.isChecked():
                        font = QtGui.QFont()
                        font.setPointSize(int(rect.width() * 0.075))
                        content = "{}\nTruncated: {}\nOccluded: {}\nDifficult: {}".format(annotation['label'], annotation['truncated'], annotation['occluded'], annotation['difficult'])
                        text = QtWidgets.QGraphicsTextItem(content)
                        text.setFont(font)
                        text.setPos(rect.topLeft().toPoint())
                        text.setDefaultTextColor(QtCore.Qt.yellow)
                        x_offset = text.boundingRect().width() / 2.0
                        y_offset = text.boundingRect().height() / 2.0
                        text.moveBy((rect.width() / 2.0) - x_offset, (rect.height() / 2.0) - y_offset)
                        text.setParentItem(graphics_item)
                    self.bboxes.append(graphics_item)

    def jump_to_image(self):
        """(Slot) Just to a specific image when when line edit changes."""
        try:
            image_num = int(self.lineEditCurrentImage.text())
            if image_num <= len(self.image_list) and image_num >= 1:
                self.current_image = image_num
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
            self.data = schema.annotation_file()
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
        self.image = np.array(img)
        if self.mask is not None:
            img = self.image * self.mask
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

    def load_model(self):
        """Load a frozen inference graph and label map."""
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Model Directory', self.directory)
        if directory != '':
            self.label_map = label_map_util.load_labelmap(directory + os.path.sep + 'label_map.pbtxt')
            self.categories = label_map_util.convert_label_map_to_categories(self.label_map, max_num_classes=100, use_display_name=True)
            self.category_index = label_map_util.create_category_index(self.categories)
            od_graph_def = tf.GraphDef()
            with self.detection_graph.as_default():
                od_graph_def = tf.GraphDef()
                with tf.gfile.GFile(directory + os.path.sep + 'frozen_inference_graph.pb', 'rb') as fid:
                    serialized_graph = fid.read()
                    od_graph_def.ParseFromString(serialized_graph)
                    tf.import_graph_def(od_graph_def, name='')
            self.model_loaded = True
            self.pushButtonAnnotate.setEnabled(True)

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

    def bbox_created(self, rect, show_assistant=True):
        """(Slot) save the newly created bbox and display it."""
        if rect.width() > 0 and rect.height() > 0:
            self.set_dirty(True)
            if self.current_file_name not in self.data['images']:
                self.data['images'][self.current_file_name] = []
            metadata = schema.annotation()
            metadata['bbox'] = [rect.x(), rect.y(), rect.width(), rect.height()]
            self.data['images'][self.current_file_name].append(metadata)
            self.display_annotation_data()
            self.selected_row = self.tableWidgetLabels.rowCount() - 1
        self.display_bboxes()
        if show_assistant:
            pos = self.mapToGlobal(self.graphicsView.pos())
            self.assistant.move(pos.x() + (self.graphicsView.width() - self.assistant.width()) / 2, pos.y() + (self.graphicsView.height() - self.assistant.height()) / 2)
            self.assistant.show()

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

    def selection_changed(self, selected, deselected):
        """(Slot) Listen for deselection of rows to hide BBox Editor."""
        if len(selected.indexes()) == 0:
            self.graphicsView.bbox_editor.hide()
            self.selected_row = -1
        else:
            self.selected_row = selected.indexes()[0].row()
        self.display_bboxes()

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
