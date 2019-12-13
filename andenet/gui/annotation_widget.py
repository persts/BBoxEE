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
from PIL import Image
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from andenet import schema
from andenet.gui import AnnotationAssistant
from andenet.gui import AnnotatorDialog

WIDGET, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__),
                           'annotation_widget.ui'))
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
        self.qt_image = None
        self.current_img_size = (0, 0)

        self.annotator = None
        self.annotator_selecter = AnnotatorDialog(self)
        self.annotator_selecter.selected.connect(self.annotator_selected)

        self.graphics_scene = QtWidgets.QGraphicsScene()
        self.graphicsView.setScene(self.graphics_scene)
        self.graphicsView.created.connect(self.bbox_created)
        self.graphicsView.resized.connect(self.update_bbox)
        self.graphicsView.select_bbox.connect(self.select_bbox)
        self.graphicsView.zoom_event.connect(self.disable_edit_mode)

        self.pb_directory.clicked.connect(self.load_from_directory)
        self.pb_directory.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_directory.setIcon(QtGui.QIcon(':/icons/folder.svg'))

        self.pb_label_file.clicked.connect(self.load_from_file)
        self.pb_label_file.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_label_file.setIcon(QtGui.QIcon(':/icons/file.svg'))

        self.pb_edit_mode.clicked.connect(self.toggle_edit_mode)
        self.pb_edit_mode.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_edit_mode.setIcon(QtGui.QIcon(':/icons/edit.svg'))

        self.pb_clear_points.clicked.connect(self.graphicsView.clear_points)
        self.pb_clear_points.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_clear_points.setIcon(QtGui.QIcon(':/icons/clear.svg'))

        self.pb_zoom_in.clicked.connect(self.graphicsView.zoom_in)
        self.pb_zoom_in.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_zoom_in.setIcon(QtGui.QIcon(':/icons/zoom_in.svg'))

        self.pb_zoom_out.clicked.connect(self.graphicsView.zoom_out)
        self.pb_zoom_out.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_zoom_out.setIcon(QtGui.QIcon(':/icons/zoom_out.svg'))

        self.pb_next_ann.clicked.connect(self.next_annotated_image)
        self.pb_next_ann.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_next_ann.setIcon(QtGui.QIcon(':/icons/skip_next.svg'))

        self.pb_previous_ann.clicked.connect(self.previous_annotated_image)
        self.pb_previous_ann.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_previous_ann.setIcon(QtGui.QIcon(':/icons/skip_previous.svg'))

        self.pb_next.clicked.connect(self.next_image)
        self.pb_next.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_next.setIcon(QtGui.QIcon(':/icons/next.svg'))

        self.pb_previous.clicked.connect(self.previous_image)
        self.pb_previous.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_previous.setIcon(QtGui.QIcon(':/icons/previous.svg'))

        self.pb_clear.clicked.connect(self.clear_annotations)
        self.pb_clear.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_clear.setIcon(QtGui.QIcon(':/icons/delete.svg'))

        self.pb_license.clicked.connect(self.apply_license)
        self.pb_annotater.clicked.connect(self.select_annotator)
        self.pb_annotate.clicked.connect(self.annotate)
        self.pb_save.clicked.connect(self.save)
        self.pb_mask.clicked.connect(self.select_mask)
        self.lineEditCurrentImage.editingFinished.connect(self.jump_to_image)
        (self.tw_labels.
         selectionModel().
         selectionChanged.
         connect(self.selection_changed))
        self.tw_labels.cellChanged.connect(self.cell_changed)
        self.tw_labels.cellDoubleClicked.connect(self.delete_row)
        self.checkBoxDisplayAnnotationData.clicked.connect(self.display_bboxes)

        self.last_license_index = 0
        self.last_license_attribution = ''
        self.licenses = config_data['licenses']
        for entry in self.licenses:
            self.cbb_license.addItem(entry['name'], entry['url'])
        self.cbb_license.currentIndexChanged.connect(self.update_license)
        self.lineEditAttribution.textEdited.connect(self.update_license)

        (self.tw_labels.
         setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows))
        (self.tw_labels.
         setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection))
        self.tw_labels.horizontalHeader().setStretchLastSection(False)
        (self.tw_labels.
         horizontalHeader().
         setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch))

        # Create some key bindings to help navigate through images
        self.right_arrow = QtWidgets.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.Key_Right), self)
        self.right_arrow.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.right_arrow.activated.connect(self.next_image)

        self.right_arrow2 = QtWidgets.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.ALT + QtCore.Qt.Key_Right), self)
        self.right_arrow2.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.right_arrow2.activated.connect(self.next_annotated_image)

        self.left_arrow = QtWidgets.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.Key_Left), self)
        self.left_arrow.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.left_arrow.activated.connect(self.previous_image)

        self.left_arrow2 = QtWidgets.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.ALT + QtCore.Qt.Key_Left), self)
        self.left_arrow2.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.left_arrow2.activated.connect(self.previous_annotated_image)

        self.clear = QtWidgets.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.ALT + QtCore.Qt.Key_C), self)
        self.clear.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.clear.activated.connect(self.clear_annotations)

        self.helper = QtWidgets.QShortcut(
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
            msg_box.setStandardButtons(QtWidgets.QMessageBox.Save |
                                       QtWidgets.QMessageBox.Cancel |
                                       QtWidgets.QMessageBox.Ignore)
            msg_box.setDefaultButton(QtWidgets.QMessageBox.Save)
            response = msg_box.exec()
            if response == QtWidgets.QMessageBox.Save:
                proceed = self.save()
            elif response == QtWidgets.QMessageBox.Cancel:
                proceed = False
        if proceed:
            self.pb_annotate.setEnabled(False)
            self.pb_directory.setEnabled(False)
            self.pb_label_file.setEnabled(False)
            self.pb_annotater.setEnabled(False)
            self.pb_mask.setEnabled(False)
            self.pb_save.setEnabled(False)
            self.pb_next.setEnabled(False)
            self.pb_next_ann.setEnabled(False)
            self.pb_previous.setEnabled(False)
            self.pb_previous_ann.setEnabled(False)
            self.tw_labels.setEnabled(False)
            self.checkBoxDisplayAnnotationData.setChecked(True)

            self.progressBar.setRange(0, len(self.image_list))
            self.progressBar.setValue(0)
            self.annotator.threshold = self.doubleSpinBoxThreshold.value()
            self.annotator.image_directory = self.image_directory
            self.annotator.image_list = self.image_list
            self.annotator.start()

    def annotation_complete(self, data):
        """(SLOT) Automatic annotation complete, reenable gui and
        reset current image to 1."""
        self.data['images'] = data['images']
        self.current_image = 0
        self.next_image()
        self.pb_annotate.setEnabled(True)
        self.pb_directory.setEnabled(True)
        self.pb_label_file.setEnabled(True)
        self.pb_annotater.setEnabled(True)
        self.pb_mask.setEnabled(True)
        self.pb_save.setEnabled(True)
        self.pb_next.setEnabled(True)
        self.pb_next_ann.setEnabled(True)
        self.pb_previous.setEnabled(True)
        self.pb_previous_ann.setEnabled(True)
        self.tw_labels.setEnabled(True)
        self.set_dirty(True)

    def annotation_progress(self, progress, image, annotations):
        """(SLOT) Show progress and current detections (annotations) as
        they are processed."""
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
        self.pb_annotate.setEnabled(True)

    def apply_license(self):
        if self.data is not None:
            for image in self.data['images']:
                if ('annotations' in self.data['images'][image] and
                        self.data['images'][image]['annotations']):
                    rec = self.data['images'][image]
                    rec['attribution'] = self.last_license_attribution
                    item = self.cbb_license.itemText(self.last_license_index)
                    rec['license'] = item
                    item = self.cbb_license.itemData(self.last_license_index)
                    rec['license_url'] = item

    def bbox_created(self, rect, show_assistant=True):
        """(Slot) save the newly created bbox and display it."""
        if rect.width() > 0 and rect.height() > 0:
            self.set_dirty(True)
            if self.current_file_name not in self.data['images']:
                template = schema.annotation_file_entry()
                self.data['images'][self.current_file_name] = template
            rec = self.data['images'][self.current_file_name]
            metadata = schema.annotation()
            metadata['created_by'] = 'human'
            metadata['bbox']['xmin'] = rect.left() / self.current_img_size[0]
            metadata['bbox']['xmax'] = rect.right() / self.current_img_size[0]
            metadata['bbox']['ymin'] = rect.top() / self.current_img_size[1]
            metadata['bbox']['ymax'] = rect.bottom() / self.current_img_size[1]
            rec['annotations'].append(metadata)
            self.display_annotation_data()
            self.selected_row = self.tw_labels.rowCount() - 1
            self.tw_labels.selectRow(self.selected_row)
        self.display_bboxes()
        self.save_license(display=True)
        if show_assistant:
            self.show_assistant()

    def cell_changed(self, row, column):
        """(Slot) Update annotation data on change."""
        text = self.tw_labels.item(row, column).text()
        header = self.tw_labels.horizontalHeaderItem(column).text().lower()
        rec = self.data['images'][self.current_file_name]
        if header in ('occluded', 'truncated', 'difficult'):
            if text in ['Y', 'y', 'N', 'n']:
                text = text.upper()
            else:
                text = rec['annotations'][row][header]
                self.tw_labels.setItem(row,
                                       column,
                                       QtWidgets.QTableWidgetItem(text))
        rec['annotations'][row][header] = text
        self.set_dirty(True)

    def clear_annotations(self):
        """(SLOT) Clear all annotations for the current image."""
        self.tw_labels.selectionModel().blockSignals(True)
        self.tw_labels.setRowCount(0)
        if (self.data is not None and
                self.current_file_name in self.data['images']):
            del self.data['images'][self.current_file_name]
        self.tw_labels.selectionModel().blockSignals(False)
        self.selected_row = -1
        self.display_bboxes()
        self.set_dirty(True)

    def delete_row(self, row, column):
        """(Slot) Delete row from table and associated metadata
        when double clicked."""
        self.tw_labels.selectionModel().blockSignals(True)
        self.tw_labels.removeRow(row)
        del self.data['images'][self.current_file_name]['annotations'][row]
        if self.tw_labels.rowCount() == 0:
            del self.data['images'][self.current_file_name]
        self.tw_labels.selectionModel().blockSignals(False)
        self.selected_row = -1
        self.graphicsView.selected_bbox = None
        self.display_bboxes()
        self.set_dirty(True)

    def disable_edit_mode(self):
        if self.pb_edit_mode.isChecked():
            self.pb_edit_mode.click()
            self.pb_edit_mode.setIcon(QtGui.QIcon(':/icons/edit.svg'))

    def display_annotation_data(self):
        """Display annotation data in table."""
        self.tw_labels.selectionModel().blockSignals(True)
        self.tw_labels.setRowCount(0)
        self.tw_labels.blockSignals(True)
        if self.current_file_name in self.data['images']:
            rec = self.data['images'][self.current_file_name]
            rows = len(rec['annotations'])
            self.tw_labels.setRowCount(rows)
            for row, annotation in enumerate(rec['annotations']):
                item = QtWidgets.QTableWidgetItem(annotation['label'])
                self.tw_labels.setItem(row, 0, item)
                item = QtWidgets.QTableWidgetItem(annotation['truncated'])
                self.tw_labels.setItem(row, 1, item)
                item = QtWidgets.QTableWidgetItem(annotation['occluded'])
                self.tw_labels.setItem(row, 2, item)
                item = QtWidgets.QTableWidgetItem(annotation['difficult'])
                self.tw_labels.setItem(row, 3, item)
        # self.tw_labels.resizeColumnToContents(0)
        self.tw_labels.blockSignals(False)
        self.tw_labels.selectionModel().blockSignals(False)
        self.tw_labels.selectRow(self.selected_row)

    def display_bboxes(self):
        """Display bboxes in graphics scene."""
        if self.bboxes:
            for bbox in self.bboxes:
                self.graphics_scene.removeItem(bbox)
            self.bboxes = []
        if (self.data is not None and
                self.current_file_name in self.data['images']):
            rec = self.data['images'][self.current_file_name]
            annotations = rec['annotations']
            width = self.current_img_size[0]
            height = self.current_img_size[1]
            for index, annotation in enumerate(annotations):
                bbox = annotation['bbox']
                x = annotation['bbox']['xmin'] * width
                y = annotation['bbox']['ymin'] * height
                top_left = QtCore.QPointF(x, y)

                x = annotation['bbox']['xmax'] * width
                y = annotation['bbox']['ymax'] * height
                bottom_right = QtCore.QPointF(x, y)

                rect = QtCore.QRectF(top_left, bottom_right)
                if index == self.selected_row:
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
                if self.checkBoxDisplayAnnotationData.isChecked():
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
                if index == self.selected_row:
                    self.graphicsView.selected_bbox = graphics_item

    def display_license(self):
        self.cbb_license.blockSignals(True)
        if self.current_file_name in self.data['images']:
            record = self.data['images'][self.current_file_name]
            if 'license' in record and record['license'] != '':
                self.last_license_index = 0
                self.last_license_attribution = record['attribution']
                index = self.cbb_license.findData(record['license_url'])
                if index != -1:
                    self.last_license_index = index
                self.cbb_license.setCurrentIndex(self.last_license_index)
                self.lineEditAttribution.setText(self.last_license_attribution)
            else:
                self.lineEditAttribution.setText('')
                self.cbb_license.setCurrentIndex(0)
        else:
            self.lineEditAttribution.setText('')
            self.cbb_license.setCurrentIndex(0)
        self.cbb_license.blockSignals(False)

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
            msg_box.setStandardButtons(QtWidgets.QMessageBox.Save |
                                       QtWidgets.QMessageBox.Cancel |
                                       QtWidgets.QMessageBox.Ignore)
            msg_box.setDefaultButton(QtWidgets.QMessageBox.Save)
            response = msg_box.exec()
            if response == QtWidgets.QMessageBox.Save:
                load = self.save()
            elif response == QtWidgets.QMessageBox.Cancel:
                load = False
        if load:
            directory = (QtWidgets.
                         QFileDialog.
                         getExistingDirectory(self,
                                              'Select Directory',
                                              self.image_directory))
            if directory != '':
                self.image_directory = directory
                self.data = schema.annotation_file()
                self.mask = None
                self.load_image_list()
                self.pb_mask.setEnabled(True)
                self.pb_annotater.setEnabled(True)
                self.set_dirty(False)

    def load_from_file(self):
        """(Slot) Load existing annotation data from file."""
        load = True
        if self.dirty:
            msg_box = QtWidgets.QMessageBox()
            msg_box.setText('Annotations have been modified.')
            msg_box.setInformativeText('Do you want to save your changes?')
            msg_box.setStandardButtons(QtWidgets.QMessageBox.Save |
                                       QtWidgets.QMessageBox.Cancel |
                                       QtWidgets.QMessageBox.Ignore)
            msg_box.setDefaultButton(QtWidgets.QMessageBox.Save)
            response = msg_box.exec()
            if response == QtWidgets.QMessageBox.Save:
                load = self.save()
            elif response == QtWidgets.QMessageBox.Cancel:
                load = False
        if load:
            file_name = (QtWidgets.
                         QFileDialog.
                         getOpenFileName(self,
                                         'Load Annotations',
                                         self.image_directory,
                                         'Andenet (*.adn)'))
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
                self.pb_annotater.setEnabled(True)
                self.pb_mask.setEnabled(True)

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
        self.current_img_size = img.size
        array = np.array(img)
        img.close()
        if self.mask is not None:
            array = array * self.mask

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
        array = None
        self.graphics_scene.addPixmap(QtGui.QPixmap.fromImage(self.qt_image))
        self.graphicsView.fitInView(self.graphics_scene.itemsBoundingRect(),
                                    QtCore.Qt.KeepAspectRatio)
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
            f = (lambda x: os.path.splitext(x)[1].lower() in image_format)
            self.image_list = list(filter(f, files))
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
            if (image_name in self.data['images'] and
                    self.data['images'][image_name]['annotations']):
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
            if (image_name in self.data['images'] and
                    self.data['images'][image_name]['annotations']):
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
        self.graphicsView.fitInView(self.graphics_scene.itemsBoundingRect(),
                                    QtCore.Qt.KeepAspectRatio)

    def save(self):
        """(Slot) Save the annotations to disk."""
        saved = False
        file_name = (QtWidgets.
                     QFileDialog.
                     getSaveFileName(self,
                                     'Save Annotations',
                                     self.image_directory + 'untitled.adn',
                                     'Andenet (*.adn)'))
        if file_name[0] != '':
            file = open(file_name[0], 'w')
            json.dump(self.data, file)
            file.close()
            self.set_dirty(False)
            saved = True
        return saved

    def save_license(self, display=False):
        self.set_dirty(True)
        if (self.data is not None and
                self.current_file_name in self.data['images']):
            rec = self.data['images'][self.current_file_name]
            rec['attribution'] = self.last_license_attribution
            item = self.cbb_license.itemText(self.last_license_index)
            rec['license'] = item
            item = self.cbb_license.itemData(self.last_license_index)
            rec['license_url'] = item
        if display:
            self.display_license()

    def select_annotator(self):
        self.annotator_selecter.show()

    def select_bbox(self, point):
        if (self.data is not None and
                self.current_file_name in self.data['images']):
            width = self.current_img_size[0]
            height = self.current_img_size[1]
            rec = self.data['images'][self.current_file_name]
            for index, annotation in enumerate(rec['annotations']):
                x = annotation['bbox']['xmin'] * width
                y = annotation['bbox']['ymin'] * height
                top_left = QtCore.QPointF(x, y)

                x = annotation['bbox']['xmax'] * width
                y = annotation['bbox']['ymax'] * height
                bottom_right = QtCore.QPointF(x, y)

                rect = QtCore.QRectF(top_left, bottom_right)
                if rect.contains(point):
                    self.tw_labels.selectRow(index)
                    break

    def select_mask(self):
        """(Slot) Select mask from disk."""
        filter_string = '{}_{}.png'.format(self.current_img_size[0],
                                           self.current_img_size[1])
        file = (QtWidgets.
                QFileDialog.getOpenFileName(self,
                                            'Select Mask',
                                            './masks/',
                                            'PNG (*' + filter_string + ')'))
        if file[0] != '':
            img = Image.open(file[0])
            if self.current_img_size == img.size:
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
            self.graphicsView.selected_bbox = None
        self.display_bboxes()

    def set_dirty(self, is_dirty):
        """Set dirty flag.

        Args:
            is_dirty (bool): Is the data dirty.
        """
        if is_dirty:
            self.dirty = True
            self.pb_save.setEnabled(True)
        else:
            self.dirty = False
            self.pb_save.setEnabled(False)

    def show_assistant(self):
        pos = self.mapToGlobal(self.graphicsView.pos())
        x = pos.x() + (self.graphicsView.width() - self.assistant.width())
        y = pos.y() + (self.graphicsView.height() - self.assistant.height())
        self.assistant.move(x / 2, y / 2)
        self.assistant.show()

    def toggle_edit_mode(self):
        if self.pb_edit_mode.isChecked():
            self.graphicsView.set_edit_mode(True)
            self.pb_edit_mode.setIcon(QtGui.QIcon(':/icons/edit_active.svg'))
        else:
            self.graphicsView.set_edit_mode(False)
            self.pb_edit_mode.setIcon(QtGui.QIcon(':/icons/edit.svg'))

    def update_annotation(self, annotation_data):
        """(Slot) Update table with data submitted from assistant widget."""
        if self.selected_row >= 0:
            self.set_dirty(True)
            rec = self.data['images'][self.current_file_name]
            ann = rec['annotations'][self.selected_row]
            for key in annotation_data.keys():
                ann[key] = annotation_data[key]
                ann['updated_by'] = 'human'
            self.display_annotation_data()

    def update_bbox(self, rect):
        """(Slot) Store the new geometry for the active bbox."""
        if rect.width() > 1.0 and rect.height() > 1.0:
            self.set_dirty(True)
            rec = self.data['images'][self.current_file_name]
            ann = rec['annotations'][self.selected_row]
            ann['updated_by'] = 'human'
            ann['bbox']['xmin'] = rect.left() / self.current_img_size[0]
            ann['bbox']['xmax'] = rect.right() / self.current_img_size[0]
            ann['bbox']['ymin'] = rect.top() / self.current_img_size[1]
            ann['bbox']['ymax'] = rect.bottom() / self.current_img_size[1]

    def update_license(self, index=0):
        self.last_license_index = self.cbb_license.currentIndex()
        self.last_license_attribution = self.lineEditAttribution.text()
        self.save_license()
