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
import glob
import json
import numpy as np
from PIL import Image, ImageQt
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from andenet import schema
from andenet.gui import AnnotationAssistant
from andenet.gui import AnnotatorDialog

WIDGET, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'annotation_widget.ui'))
# TODO: Break this class / widget up into multiple widgets / components.


class AnnotationWidget(QtWidgets.QWidget, WIDGET):
    """Widget for annotating images."""

    def __init__(self, config_data, icon_size=24, parent=None):
        """Class init function."""
        QtWidgets.QWidget.__init__(self, parent)
        self.setupUi(self)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.image_directory = '.'
        self.current_file_name = ''
        self.bboxes = []
        self.selected_row = -1
        self.current_image = 1
        self.image_list = []
        self.mask = None
        self.data = None
        self.dirty = False
        self.assistant = AnnotationAssistant(config_data['labels'], self)
        self.assistant.submitted.connect(self.update_annotation)
        self.image = None
        self.qt_image = None
        self.current_image_size = (0, 0)

        self.annotator = None
        self.annotator_selecter = AnnotatorDialog(self)
        self.annotator_selecter.selected.connect(self.annotator_selected)

        self.graphics_scene = QtWidgets.QGraphicsScene()
        self.graphicsView.setScene(self.graphics_scene)
        self.graphicsView.created.connect(self.bbox_created)
        self.graphicsView.resized.connect(self.update_bbox)
        self.graphicsView.select_bbox.connect(self.select_bbox)
        self.graphicsView.zoom_event.connect(self.disable_edit_mode)

        self.pushButtonDirectory.clicked.connect(self.load_from_directory)
        self.pushButtonDirectory.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pushButtonDirectory.setIcon(QtGui.QIcon(':/icons/folder.svg'))

        self.pushButtonLabelFile.clicked.connect(self.load_from_file)
        self.pushButtonLabelFile.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pushButtonLabelFile.setIcon(QtGui.QIcon(':/icons/file.svg'))

        self.pushButtonEditMode.clicked.connect(self.toggle_edit_mode)
        self.pushButtonEditMode.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pushButtonEditMode.setIcon(QtGui.QIcon(':/icons/edit.svg'))

        self.pushButtonClearPoints.clicked.connect(self.graphicsView.clear_points)
        self.pushButtonClearPoints.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pushButtonClearPoints.setIcon(QtGui.QIcon(':/icons/clear.svg'))

        self.pushButtonZoomIn.clicked.connect(self.graphicsView.zoom_in)
        self.pushButtonZoomIn.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pushButtonZoomIn.setIcon(QtGui.QIcon(':/icons/zoom_in.svg'))

        self.pushButtonZoomOut.clicked.connect(self.graphicsView.zoom_out)
        self.pushButtonZoomOut.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pushButtonZoomOut.setIcon(QtGui.QIcon(':/icons/zoom_out.svg'))

        self.pushButtonAnnotatedNext.clicked.connect(self.next_annotated_image)
        self.pushButtonAnnotatedNext.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pushButtonAnnotatedNext.setIcon(QtGui.QIcon(':/icons/skip_next.svg'))

        self.pushButtonAnnotatedPrevious.clicked.connect(self.previous_annotated_image)
        self.pushButtonAnnotatedPrevious.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pushButtonAnnotatedPrevious.setIcon(QtGui.QIcon(':/icons/skip_previous.svg'))
        
        self.pushButtonNext.clicked.connect(self.next_image)
        self.pushButtonNext.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pushButtonNext.setIcon(QtGui.QIcon(':/icons/next.svg'))

        self.pushButtonPrevious.clicked.connect(self.previous_image)
        self.pushButtonPrevious.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pushButtonPrevious.setIcon(QtGui.QIcon(':/icons/previous.svg'))

        self.pushButtonClear.clicked.connect(self.clear_annotations)
        self.pushButtonClear.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pushButtonClear.setIcon(QtGui.QIcon(':/icons/delete.svg'))

        self.pushButtonApplyLicense.clicked.connect(self.apply_license)
        self.pushButtonSelectAnnotater.clicked.connect(self.select_annotator)
        self.pushButtonAnnotate.clicked.connect(self.annotate)
        self.pushButtonSave.clicked.connect(self.save)
        self.pushButtonSelectMask.clicked.connect(self.select_mask)
        self.lineEditCurrentImage.editingFinished.connect(self.jump_to_image)
        self.tableWidgetLabels.selectionModel().selectionChanged.connect(self.selection_changed)
        self.tableWidgetLabels.cellChanged.connect(self.cell_changed)
        self.tableWidgetLabels.cellDoubleClicked.connect(self.delete_row)
        self.checkBoxDisplayAnnotationData.clicked.connect(self.display_bboxes)

        self.last_license_index = 0
        self.last_license_attribution = ''
        self.licenses = config_data['licenses']
        for entry in self.licenses:
            self.comboBoxLicense.addItem(entry['name'], entry['url'])
        self.comboBoxLicense.currentIndexChanged.connect(self.update_license)
        self.lineEditAttribution.textEdited.connect(self.update_license)

        self.tableWidgetLabels.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tableWidgetLabels.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tableWidgetLabels.horizontalHeader().setStretchLastSection(False)
        self.tableWidgetLabels.horizontalHeader().setSectionResizeMode(0, \
            QtWidgets.QHeaderView.Stretch)

        # Create some key bindings to help navigate through images
        self.right_arrow = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Right), self)
        self.right_arrow.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.right_arrow.activated.connect(self.next_image)

        self.right_arrow2 = QtWidgets.QShortcut( \
            QtGui.QKeySequence(QtCore.Qt.ALT + QtCore.Qt.Key_Right), self)
        self.right_arrow2.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.right_arrow2.activated.connect(self.next_annotated_image)

        self.left_arrow = QtWidgets.QShortcut( \
            QtGui.QKeySequence(QtCore.Qt.Key_Left), self)
        self.left_arrow.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.left_arrow.activated.connect(self.previous_image)

        self.left_arrow2 = QtWidgets.QShortcut( \
            QtGui.QKeySequence(QtCore.Qt.ALT + QtCore.Qt.Key_Left), self)
        self.left_arrow2.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.left_arrow2.activated.connect(self.previous_annotated_image)

        self.clear = QtWidgets.QShortcut( \
            QtGui.QKeySequence(QtCore.Qt.ALT + QtCore.Qt.Key_C), self)
        self.clear.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.clear.activated.connect(self.clear_annotations)

        self.helper = QtWidgets.QShortcut( \
            QtGui.QKeySequence(QtCore.Qt.ALT + QtCore.Qt.Key_A), self)
        self.helper.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.helper.activated.connect(self.assistant.show)

    def annotate(self):
        """(SLOT) Start the automated annotator."""
        proceed = True
        if self.dirty:
            msg_box = QtWidgets.QMessageBox()
            msg_box.setText('Annotations have been modified.')
            msg_box.setInformativeText('Do you want to save your changes?')
            msg_box.setStandardButtons(QtWidgets.QMessageBox.Save | \
                QtWidgets.QMessageBox.Cancel | QtWidgets.QMessageBox.Ignore)
            msg_box.setDefaultButton(QtWidgets.QMessageBox.Save)
            response = msg_box.exec()
            if response == QtWidgets.QMessageBox.Save:
                proceed = self.save()
            elif response == QtWidgets.QMessageBox.Cancel:
                proceed = False
        if proceed:
            self.pushButtonAnnotate.setEnabled(False)
            self.pushButtonDirectory.setEnabled(False)
            self.pushButtonLabelFile.setEnabled(False)
            self.pushButtonSelectAnnotater.setEnabled(False)
            self.pushButtonSelectMask.setEnabled(False)
            self.pushButtonSave.setEnabled(False)
            self.pushButtonNext.setEnabled(False)
            self.pushButtonAnnotatedNext.setEnabled(False)
            self.pushButtonPrevious.setEnabled(False)
            self.pushButtonAnnotatedPrevious.setEnabled(False)
            self.tableWidgetLabels.setEnabled(False)
            self.checkBoxDisplayAnnotationData.setChecked(True)

            self.progressBar.setRange(0, len(self.image_list))
            self.progressBar.setValue(0)
            self.annotator.threshold = self.doubleSpinBoxThreshold.value()
            self.annotator.image_directory = self.image_directory
            self.annotator.image_list = self.image_list
            self.annotator.start()

    def annotation_complete(self, data):
        """(SLOT) Automatic annotation complete, reenable gui and reset current image to 1."""
        self.data['images'] = data['images']
        self.current_image = 0
        self.next_image()
        self.pushButtonAnnotate.setEnabled(True)
        self.pushButtonDirectory.setEnabled(True)
        self.pushButtonLabelFile.setEnabled(True)
        self.pushButtonSelectAnnotater.setEnabled(True)
        self.pushButtonSelectMask.setEnabled(True)
        self.pushButtonSave.setEnabled(True)
        self.pushButtonNext.setEnabled(True)
        self.pushButtonAnnotatedNext.setEnabled(True)
        self.pushButtonPrevious.setEnabled(True)
        self.pushButtonAnnotatedPrevious.setEnabled(True)
        self.tableWidgetLabels.setEnabled(True)
        self.set_dirty(True)

    def annotation_progress(self, progress, image, annotations):
        """(SLOT) Show progress and current detections (annotations) as they are processed."""
        if progress == 1:
            self.current_image = 0
        self.progressBar.setValue(progress)
        self.data['images'][image] = annotations
        self.next_image()

    def annotator_selected(self, annotator):
        """ (SLOT) save and hook up annotator."""
        self.annotator = annotator
        self.annotator.progress.connect(self.annotation_progress)
        self.annotator.finished.connect(self.annotation_complete)
        self.pushButtonAnnotate.setEnabled(True)

    def apply_license(self):
        if self.data is not None:
            for image in self.data['images']:
                if 'annotations' in self.data['images'][image] and self.data['images'][image]['annotations']:
                    self.data['images'][image]['attribution'] = self.last_license_attribution
                    self.data['images'][image]['license'] = self.comboBoxLicense.itemText(self.last_license_index)
                    self.data['images'][image]['license_url'] = self.comboBoxLicense.itemData(self.last_license_index)

    def bbox_created(self, rect, show_assistant=True):
        """(Slot) save the newly created bbox and display it."""
        if rect.width() > 0 and rect.height() > 0:
            self.set_dirty(True)
            if self.current_file_name not in self.data['images']:
                self.data['images'][self.current_file_name] = schema.annotation_file_entry()
            metadata = schema.annotation()
            metadata['created_by'] = 'human'
            metadata['bbox']['xmin'] = rect.left() / self.current_image_size[0]
            metadata['bbox']['xmax'] = rect.right() / self.current_image_size[0]
            metadata['bbox']['ymin'] = rect.top() / self.current_image_size[1]
            metadata['bbox']['ymax'] = rect.bottom() / self.current_image_size[1]
            self.data['images'][self.current_file_name]['annotations'].append(metadata)
            self.display_annotation_data()
            self.selected_row = self.tableWidgetLabels.rowCount() - 1
            self.tableWidgetLabels.selectRow(self.selected_row)
        self.display_bboxes()
        self.save_license(display=True)
        if show_assistant:
            self.show_assistant()

    def cell_changed(self, row, column):
        """(Slot) Update annotation data on change."""
        text = self.tableWidgetLabels.item(row, column).text()
        header = self.tableWidgetLabels.horizontalHeaderItem(column).text().lower()
        if header in ('occluded', 'truncated', 'difficult'):
            if text in ['Y', 'y', 'N', 'n']:
                text = text.upper()
            else:
                text = self.data['images'][self.current_file_name]['annotations'][row][header]
                self.tableWidgetLabels.setItem(row, column, QtWidgets.QTableWidgetItem(text))
        self.data['images'][self.current_file_name]['annotations'][row][header] = text
        self.set_dirty(True)

    def clear_annotations(self):
        """(SLOT) Clear all annotations for the current image."""
        self.tableWidgetLabels.selectionModel().blockSignals(True)
        self.tableWidgetLabels.setRowCount(0)
        if self.data is not None and self.current_file_name in self.data['images']:
            del self.data['images'][self.current_file_name]
        self.tableWidgetLabels.selectionModel().blockSignals(False)
        self.selected_row = -1
        self.display_bboxes()
        self.set_dirty(True)

    def delete_row(self, row, column):
        """(Slot) Delete row from table and associated metadata when double clicked."""
        self.tableWidgetLabels.selectionModel().blockSignals(True)
        self.tableWidgetLabels.removeRow(row)
        del self.data['images'][self.current_file_name]['annotations'][row]
        if self.tableWidgetLabels.rowCount() == 0:
            del self.data['images'][self.current_file_name]
        self.tableWidgetLabels.selectionModel().blockSignals(False)
        self.selected_row = -1
        self.display_bboxes()
        self.set_dirty(True)

    def disable_edit_mode(self):
        if self.pushButtonEditMode.isChecked():
            self.pushButtonEditMode.click()
            self.pushButtonEditMode.setIcon(QtGui.QIcon(':/icons/edit.svg'))

    def display_annotation_data(self):
        """Display annotation data in table."""
        self.tableWidgetLabels.selectionModel().blockSignals(True)
        self.tableWidgetLabels.setRowCount(0)
        self.tableWidgetLabels.blockSignals(True)
        if self.current_file_name in self.data['images']:
            rows = len(self.data['images'][self.current_file_name]['annotations'])
            self.tableWidgetLabels.setRowCount(rows)
            for row in range(rows):
                annotation = self.data['images'][self.current_file_name]['annotations'][row]
                self.tableWidgetLabels.setItem(row, 0, \
                    QtWidgets.QTableWidgetItem(annotation['label']))
                self.tableWidgetLabels.setItem(row, 1, \
                    QtWidgets.QTableWidgetItem(annotation['truncated']))
                self.tableWidgetLabels.setItem(row, 2, \
                    QtWidgets.QTableWidgetItem(annotation['occluded']))
                self.tableWidgetLabels.setItem(row, 3, \
                    QtWidgets.QTableWidgetItem(annotation['difficult']))
        # self.tableWidgetLabels.resizeColumnToContents(0)
        self.tableWidgetLabels.blockSignals(False)
        self.tableWidgetLabels.selectionModel().blockSignals(False)
        self.tableWidgetLabels.selectRow(self.selected_row)

    def display_bboxes(self):
        """Display bboxes in graphics scene."""
        if self.bboxes:
            for bbox in self.bboxes:
                self.graphics_scene.removeItem(bbox)
            self.bboxes = []
        if self.data is not None and self.current_file_name in self.data['images']:
            annotations = self.data['images'][self.current_file_name]['annotations']
            width = self.current_image_size[0]
            height = self.current_image_size[1]
            for index, annotation in enumerate(annotations):
                bbox = annotation['bbox']
                top_left = QtCore.QPointF(bbox['xmin'] * width, bbox['ymin'] * height)
                bottom_right = QtCore.QPointF(bbox['xmax'] * width, bbox['ymax'] * height)
                rect = QtCore.QRectF(top_left, bottom_right)
                if index == self.selected_row:
                    pen = QtGui.QPen(QtGui.QBrush(QtCore.Qt.red, QtCore.Qt.SolidPattern), 3)
                else:
                    pen = QtGui.QPen(QtGui.QBrush(QtCore.Qt.yellow, QtCore.Qt.SolidPattern), 3)
                    if annotation['created_by'] == 'machine' and annotation['updated_by'] == '':
                        pen = QtGui.QPen(QtGui.QBrush(QtCore.Qt.green, QtCore.Qt.SolidPattern), 3)
                graphics_item = self.graphics_scene.addRect(rect, pen)
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
                self.bboxes.append(graphics_item)
                if index == self.selected_row:
                    self.graphicsView.selected_bbox = graphics_item

    def display_license(self):
        self.comboBoxLicense.blockSignals(True)
        if self.current_file_name in self.data['images']:
            record = self.data['images'][self.current_file_name]
            if 'license' in record and record['license'] != '':
                self.last_license_index = 0
                self.last_license_attribution = record['attribution']
                index = self.comboBoxLicense.findData(record['license_url'])
                if index != -1:
                    self.last_license_index = index
                self.comboBoxLicense.setCurrentIndex(self.last_license_index)
                self.lineEditAttribution.setText(self.last_license_attribution)
            else: 
                self.lineEditAttribution.setText('')
                self.comboBoxLicense.setCurrentIndex(0)
        else: 
                self.lineEditAttribution.setText('')
                self.comboBoxLicense.setCurrentIndex(0)
        self.comboBoxLicense.blockSignals(False)
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
        load = True
        if self.dirty:
            msg_box = QtWidgets.QMessageBox()
            msg_box.setText('Annotations have been modified.')
            msg_box.setInformativeText('Do you want to save your changes?')
            msg_box.setStandardButtons(QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Cancel | QtWidgets.QMessageBox.Ignore)
            msg_box.setDefaultButton(QtWidgets.QMessageBox.Save)
            response = msg_box.exec()
            if response == QtWidgets.QMessageBox.Save:
                load = self.save()
            elif response == QtWidgets.QMessageBox.Cancel:
                load = False
        if load:
            directory = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Directory', self.image_directory)
            if directory != '':
                self.image_directory = directory
                self.data = schema.annotation_file()
                self.mask = None
                self.load_image_list()
                self.pushButtonSelectMask.setEnabled(True)
                self.pushButtonSelectAnnotater.setEnabled(True)
                self.set_dirty(False)

    def load_from_file(self):
        """(Slot) Load existing annotation data from file."""
        load = True
        if self.dirty:
            msg_box = QtWidgets.QMessageBox()
            msg_box.setText('Annotations have been modified.')
            msg_box.setInformativeText('Do you want to save your changes?')
            msg_box.setStandardButtons(QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Cancel | QtWidgets.QMessageBox.Ignore)
            msg_box.setDefaultButton(QtWidgets.QMessageBox.Save)
            response = msg_box.exec()
            if response == QtWidgets.QMessageBox.Save:
                load = self.save()
            elif response == QtWidgets.QMessageBox.Cancel:
                load = False
        if load:
            file_name = QtWidgets.QFileDialog.getOpenFileName(self, 'Load Annotations', self.image_directory, 'Andenet (*.adn)')
            if file_name[0] != '':
                file = open(file_name[0], 'r')
                self.data = json.load(file)
                file.close()
                self.image_directory = os.path.split(file_name[0])[0]
                # self.image_directory = self.data['directory']
                if self.data['mask'] is not None:
                    tmp = np.array(self.data['mask'], dtype='uint8')
                    self.mask = np.dstack((tmp, tmp, tmp))
                else:
                    self.mask = None
                self.load_image_list()
                self.set_dirty(False)
                self.pushButtonSelectAnnotater.setEnabled(True)
                self.pushButtonSelectMask.setEnabled(True)

    def load_image(self):
        """Load image into graphics scene."""
        self.graphicsView.points = []
        self.graphicsView.graphics_items = []
        self.graphicsView.selected_bbox = None
        self.graphics_scene.clear()
        self.bboxes = []
        self.selected_row = -1
        self.current_file_name = self.image_list[self.current_image - 1]
        file = os.path.join(self.image_directory, self.current_file_name)
        img = Image.open(file)
        self.current_image_size = img.size
        self.image = np.array(img)
        if self.mask is not None:
            img = self.image * self.mask
            img = Image.fromarray(img)

        self.qt_image = ImageQt.ImageQt(img)
        self.graphics_scene.addPixmap(QtGui.QPixmap.fromImage(self.qt_image))
        img.close()
        img = None
        self.graphicsView.fitInView(self.graphics_scene.itemsBoundingRect(), QtCore.Qt.KeepAspectRatio)
        self.graphicsView.setSceneRect(self.graphics_scene.itemsBoundingRect())
        self.display_license()
        self.display_bboxes()
        self.display_annotation_data()
        self.graphicsView.setFocus()

    def load_image_list(self):
        """Glob the image files and save to image list."""
        if self.image_directory != '':
            self.image_list = []
            self.image_directory += os.path.sep
            files = glob.glob(self.image_directory + '*')
            image_format = [".jpg", ".jpeg", ".png"]
            self.image_list = list(filter(lambda x: os.path.splitext(x)[1].lower() in image_format, files))
            self.image_list = [os.path.basename(x) for x in self.image_list]
            self.image_list = sorted(self.image_list)
            self.current_image = 1
            self.labelImages.setText('of ' + str(len(self.image_list)))
            self.lineEditCurrentImage.setText('1')
            self.load_image()

    def next_annotated_image(self):
        """(Slot) Jump to the next image that has been annotated."""
        index = self.current_image
        while index < len(self.image_list):
            image_name = self.image_list[index]
            if image_name in self.data['images'] and self.data['images'][image_name]['annotations']:
                self.current_image = index + 1
                break
            else:
                index += 1
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
        index = self.current_image - 2
        while index >= 0:
            image_name = self.image_list[index]
            if image_name in self.data['images'] and self.data['images'][image_name]['annotations']:
                self.current_image = index + 1
                break
            else:
                index -= 1
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
        self.graphicsView.fitInView(self.graphics_scene.itemsBoundingRect(), QtCore.Qt.KeepAspectRatio)

    def save(self):
        """(Slot) Save the annotations to disk."""
        saved = False
        file_name = QtWidgets.QFileDialog.getSaveFileName(self, 'Save Annotations', self.image_directory + 'untitled.adn', 'Andenet (*.adn)')
        if file_name[0] != '':
            # self.data['timestamp'] = '{:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now())
            file = open(file_name[0], 'w')
            json.dump(self.data, file)
            file.close()
            self.set_dirty(False)
            saved = True
        return saved
    
    def save_license(self, display=False):
        self.set_dirty(True)
        if self.data is not None and self.current_file_name in self.data['images']:
            self.data['images'][self.current_file_name]['attribution'] = self.last_license_attribution
            self.data['images'][self.current_file_name]['license'] = self.comboBoxLicense.itemText(self.last_license_index)
            self.data['images'][self.current_file_name]['license_url'] = self.comboBoxLicense.itemData(self.last_license_index)
        if display:
            self.display_license()

    def select_annotator(self):
        self.annotator_selecter.show()

    def select_bbox(self, point):
        if self.data is not None and self.current_file_name in self.data['images']:
            width = self.current_image_size[0]
            height = self.current_image_size[1]
            annotations = self.data['images'][self.current_file_name]['annotations']
            for index, annotation in enumerate(annotations):
                bbox = annotation['bbox']
                top_left = QtCore.QPointF(bbox['xmin'] * width, bbox['ymin'] * height)
                bottom_right = QtCore.QPointF(bbox['xmax'] * width, bbox['ymax'] * height)
                rect = QtCore.QRectF(top_left, bottom_right)
                if rect.contains(point):
                    self.tableWidgetLabels.selectRow(index)
                    break

    def select_mask(self):
        """(Slot) Select mask from disk."""
        filter_string = str(self.current_image_size[0]) + '_' + str(self.current_image_size[1]) + '.png'
        file = QtWidgets.QFileDialog.getOpenFileName(self, 'Select Mask', './masks/', 'PNG (*' + filter_string + ')')
        if file[0] != '':
            img = Image.open(file[0])
            if self.current_image_size == img.size:
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
        """(Slot) Listen for deselection of rows."""
        if selected.indexes():
            self.selected_row = selected.indexes()[0].row()
            if self.checkBoxAnnotationAssistant.isChecked():
                self.show_assistant()
        else:
            self.selected_row = -1
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

    def show_assistant(self):
        pos = self.mapToGlobal(self.graphicsView.pos())
        self.assistant.move(pos.x() + (self.graphicsView.width() - self.assistant.width()) / 2, pos.y() + (self.graphicsView.height() - self.assistant.height()) / 2)
        self.assistant.show()

    def toggle_edit_mode(self):
        if self.pushButtonEditMode.isChecked():
            self.graphicsView.set_edit_mode(True)
            self.pushButtonEditMode.setIcon(QtGui.QIcon(':/icons/edit_active.svg'))
        else:
            self.graphicsView.set_edit_mode(False)
            self.pushButtonEditMode.setIcon(QtGui.QIcon(':/icons/edit.svg'))

    def update_annotation(self, annotation_data):
        """(Slot) Update table with data submitted from assistant widget."""
        if self.selected_row >= 0:
            for key in annotation_data.keys():
                self.data['images'][self.current_file_name]['annotations'][self.selected_row][key] = annotation_data[key]
                self.data['images'][self.current_file_name]['annotations'][self.selected_row]['updated_by'] = 'human'
            self.display_annotation_data()

    def update_bbox(self, rect):
        """(Slot) Store the new geometry for the active bbox."""
        if rect.width() > 1.0 and rect.height() > 1.0:
            self.set_dirty(True)
            annotation = self.data['images'][self.current_file_name]['annotations'][self.selected_row]
            annotation['updated_by'] = 'human'
            annotation['bbox']['xmin'] = rect.left() / self.current_image_size[0]
            annotation['bbox']['xmax'] = rect.right() / self.current_image_size[0]
            annotation['bbox']['ymin'] = rect.top() / self.current_image_size[1]
            annotation['bbox']['ymax'] = rect.bottom() / self.current_image_size[1]

    def update_license(self, index = 0):
        self.last_license_index = self.comboBoxLicense.currentIndex()
        self.last_license_attribution = self.lineEditAttribution.text()
        self.save_license()
