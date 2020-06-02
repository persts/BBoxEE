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
import glob
import json
import numpy as np
from PIL import Image
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from bboxee import schema
from bboxee.gui import AnnotationAssistant
from bboxee.gui import AnnotatorDialog
from bboxee.gui import AnalystDialog

WIDGET, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__),
                           'annotation_widget.ui'))
# TODO: Break this class / widget up into multiple widgets / components.


class AnnotationWidget(QtWidgets.QWidget, WIDGET):
    """Widget for annotating images."""

    def __init__(self, icon_size=24, parent=None):
        """Class init function."""
        QtWidgets.QWidget.__init__(self, parent)
        self.setupUi(self)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.image_directory = '.'
        self.current_file_name = ''
        self.selected_row = -1
        self.current_image = 1
        self.image_list = []
        self.mask = None
        self.data = None
        self.labels = None
        self.dirty = False
        self.assistant = AnnotationAssistant(self)
        self.assistant.submitted.connect(self.update_annotation)
        self.qt_image = None

        self.annotator = None
        self.annotator_selecter = AnnotatorDialog(self)
        self.annotator_selecter.selected.connect(self.annotator_selected)

        self.graphicsView.created.connect(self.bbox_created)
        self.graphicsView.resized.connect(self.update_bbox)
        self.graphicsView.moved.connect(self.update_bbox)
        self.graphicsView.select_bbox.connect(self.select_bbox)
        self.graphicsView.delete_event.connect(self.delete_selected_row)
        #self.graphicsView.zoom_event.connect(self.disable_edit_mode)

        self.pb_directory.clicked.connect(self.load_from_directory)
        self.pb_directory.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_directory.setIcon(QtGui.QIcon(':/icons/folder.svg'))

        self.pb_label_file.clicked.connect(self.load_from_file)
        self.pb_label_file.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_label_file.setIcon(QtGui.QIcon(':/icons/file.svg'))

        self.pb_visible.clicked.connect(self.graphicsView.toggle_visibility)

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

        self.license.license_changed.connect(self.update_license)
        self.license.apply_license.connect(self.apply_license)

        self.analyst_dialog = AnalystDialog(self)
        self.analyst_dialog.name.connect(self.add_analyst)
        self.pb_add_analyst.clicked.connect(self.add_analyst_dialog)

        self.pb_annotater.clicked.connect(self.select_annotator)
        self.pb_annotate.clicked.connect(self.annotate)
        self.pb_save.clicked.connect(self.save)
        self.pb_mask.clicked.connect(self.select_mask)
        self.lineEditCurrentImage.editingFinished.connect(self.jump_to_image)
        self.tw_labels.selectionModel().selectionChanged.connect(self.selection_changed)
        self.tw_labels.cellChanged.connect(self.cell_changed)
        self.checkBoxDisplayAnnotationData.clicked.connect(self.display_bboxes)

        (self.tw_labels.
         setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows))
        (self.tw_labels.
         setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection))
        table_header = self.tw_labels.horizontalHeader()
        table_header.setStretchLastSection(False)
        table_header.ResizeMode = QtWidgets.QHeaderView.Interactive
        table_header.resizeSection(0, 150)
        table_header.resizeSection(2, 30)
        table_header.resizeSection(3, 30)
        table_header.resizeSection(4, 30)

        # (self.tw_labels.
        #  horizontalHeader().
        #  setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch))

        # Create some key bindings to help navigate through images
        self.right_arrow = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Right), self)
        self.right_arrow.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.right_arrow.activated.connect(self.graphicsView.nudge_right)
        #self.right_arrow.activated.connect(self.next_image)

        self.left_arrow = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Left), self)
        self.left_arrow.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.left_arrow.activated.connect(self.graphicsView.nudge_left)
        #self.left_arrow.activated.connect(self.previous_image)

        self.up_arrow = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Up), self)
        self.up_arrow.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.up_arrow.activated.connect(self.graphicsView.nudge_up)

        self.down_arrow = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Down), self)
        self.down_arrow.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.down_arrow.activated.connect(self.graphicsView.nudge_down)


        self.right_arrow_shift = \
            QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.SHIFT + QtCore.Qt.Key_Right), self)
        self.right_arrow_shift.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.right_arrow_shift.activated.connect(self.graphicsView.expand_right)

        self.left_arrow_shift = \
            QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.SHIFT + QtCore.Qt.Key_Left), self)
        self.left_arrow_shift.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.left_arrow_shift.activated.connect(self.graphicsView.shrink_left)

        self.up_arrow_shift = \
            QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.SHIFT + QtCore.Qt.Key_Up), self)
        self.up_arrow_shift.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.up_arrow_shift.activated.connect(self.graphicsView.expand_up)

        self.down_arrow_shift = \
            QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.SHIFT + QtCore.Qt.Key_Down), self)
        self.down_arrow_shift.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.down_arrow_shift.activated.connect(self.graphicsView.shrink_down)

        self.clear = QtWidgets.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_C), self)
        self.clear.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.clear.activated.connect(self.duplicate_selected_row)

        self.clear = QtWidgets.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_D), self)
        self.clear.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.clear.activated.connect(self.clear_annotations)

        self.clear = QtWidgets.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.SHIFT + QtCore.Qt.Key_Delete), self)
        self.clear.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.clear.activated.connect(self.clear_annotations)

        self.clear = QtWidgets.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.SHIFT + QtCore.Qt.Key_Backspace), self)
        self.clear.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.clear.activated.connect(self.clear_annotations)

        self.visibility = QtWidgets.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_H), self)
        self.visibility.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.visibility.activated.connect(self.graphicsView.toggle_visibility)

        self.visibility = QtWidgets.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.Key_Tab), self)
        self.visibility.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.visibility.activated.connect(self.next_row)

        self.visibility = QtWidgets.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.Key_Backtab), self)
        self.visibility.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.visibility.activated.connect(self.prev_row)

        self.visibility = QtWidgets.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_D), self)
        self.visibility.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.visibility.activated.connect(self.delete_selected_row)

        self.visibility = QtWidgets.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.Key_Delete), self)
        self.visibility.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.visibility.activated.connect(self.delete_selected_row)

        self.visibility = QtWidgets.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.Key_Backspace), self)
        self.visibility.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.visibility.activated.connect(self.delete_selected_row)

        self.visibility = QtWidgets.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.Key_Space), self)
        self.visibility.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.visibility.activated.connect(self.next_image)

        self.visibility = QtWidgets.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.SHIFT + QtCore.Qt.Key_Space), self)
        self.visibility.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.visibility.activated.connect(self.next_annotated_image)

        self.helper = QtWidgets.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_A), self)
        self.helper.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.helper.activated.connect(self.assistant.show)

    def next_row(self):
        self.tw_labels.selectRow((self.selected_row + 1) % self.tw_labels.rowCount())
        self.graphicsView.sticky_bbox = True

    def prev_row(self):
        self.tw_labels.selectRow((self.selected_row - 1) % self.tw_labels.rowCount())
        self.graphicsView.sticky_bbox = True

    def add_analyst(self, name):
        if self.data is not None:
            last_index = len(self.data['analysts']) - 1
            if name not in self.data['analysts']:
                self.data['analysts'].append(name)
                self.set_dirty(True)
            # Ignore add request of name is the same as the last entry
            elif self.data['analysts'][last_index] != name:
                self.data['analysts'].append(name)
                self.set_dirty(True)
            self.display_analysts()

    def add_analyst_dialog(self):
        if self.data is not None:
            self.analyst_dialog.show()

    def annotate(self):
        """(SLOT) Start the automated annotator."""
        if self.dirty_data_check():
            self.checkBoxDisplayAnnotationData.setChecked(True)
            self.license.setDisabled(True)
            self.analysts.setDisabled(True)
            self.main_frame.setDisabled(True)
            self.table_frame.setDisabled(True)
            self.pb_annotater.setDisabled(True)
            self.pb_annotate.setDisabled(True)

            self.progressBar.setRange(0, len(self.image_list))
            self.progressBar.setValue(0)
            self.annotator.threshold = self.doubleSpinBoxThreshold.value()
            self.annotator.image_directory = self.image_directory
            self.annotator.image_list = self.image_list
            self.annotator.start()

    def annotation_complete(self, data):
        """(SLOT) Automatic annotation complete, reenable gui and
        reset current image to 1."""
        self.data = data
        self.display_analysts()
        self.current_image = 0
        self.next_image()
        self.license.setEnabled(True)
        self.analysts.setEnabled(True)
        self.main_frame.setEnabled(True)
        self.table_frame.setEnabled(True)
        self.pb_annotater.setEnabled(True)
        self.pb_annotate.setEnabled(True)
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

    def apply_license(self, license):
        if self.data is not None:
            for image in self.data['images']:
                if ('annotations' in self.data['images'][image] and
                        self.data['images'][image]['annotations']):
                    rec = self.data['images'][image]
                    rec['attribution'] = license['attribution']
                    rec['license'] = license['license']
                    rec['license_url'] = license['license_url']
                    self.set_dirty(True)

    def bbox_created(self, rect, show_assistant=True, meta=None):
        """(Slot) save the newly created bbox and display it."""
        if rect.width() > 0 and rect.height() > 0:
            self.set_dirty(True)
            if self.current_file_name not in self.data['images']:
                template = schema.annotation_file_entry()
                self.data['images'][self.current_file_name] = template
            rec = self.data['images'][self.current_file_name]
            metadata = schema.annotation()
            metadata['created_by'] = 'human'
            metadata['bbox']['xmin'] = rect.left() / self.graphicsView.img_size[0]
            metadata['bbox']['xmax'] = rect.right() / self.graphicsView.img_size[0]
            metadata['bbox']['ymin'] = rect.top() / self.graphicsView.img_size[1]
            metadata['bbox']['ymax'] = rect.bottom() / self.graphicsView.img_size[1]

            if meta is not None:
                metadata['label'] = meta['label']
                metadata['truncated'] = meta['truncated']
                metadata['occluded'] = meta['occluded']
                metadata['difficult'] = meta['difficult']
            rec['annotations'].append(metadata)
            self.display_annotation_data()
            self.selected_row = self.tw_labels.rowCount() - 1
            self.tw_labels.selectRow(self.selected_row)

            self.license.request()
        self.display_bboxes()
        if show_assistant:
            self.show_assistant()

    def cell_changed(self, row, column):
        """(Slot) Update annotation data on change."""
        table = self.tw_labels
        # get text
        header = table.horizontalHeaderItem(column).text().lower()
        if column == 0:
            text = table.cellWidget(row, 0).currentText()
        elif header in ('o', 't', 'd'):
            checked = table.item(row, column).checkState() == QtCore.Qt.Checked
            text = "Y" if checked else "N"
            mapping = {'o': 'occluded', 't': 'truncated', 'd': 'difficult'}
            header = mapping[header]
        else:
            print("Got unexpected header: {}".format(header))

        # update annotations
        rec = self.data['images'][self.current_file_name]
        rec['annotations'][row][header] = text
        self.set_dirty(True)
        if column == 0:
            self.display_bboxes()

    def clear_annotations(self):
        """(SLOT) Clear all annotations for the current image."""
        self.tw_labels.selectionModel().blockSignals(True)
        self.tw_labels.setRowCount(0)
        self.tw_labels.selectionModel().blockSignals(False)
        self.tw_labels.clearSelection()
        if (self.data is not None and
                self.current_file_name in self.data['images']):
            del self.data['images'][self.current_file_name]
        self.display_bboxes()
        self.set_dirty(True)

    def duplicate_selected_row(self):
        if self.selected_row is None or self.selected_row < 0:
            return

        self.selected_row
        # get metadata
        rec = self.data['images'][self.current_file_name]
        metadata = rec['annotations'][self.selected_row]

        # get rect
        selected_rect = self.graphicsView.selected_bbox.rect()
        # create new of same size centerd on cursor
        width = selected_rect.width()
        height = selected_rect.height()
        center = QtGui.QCursor.pos()
        center = self.graphicsView.mapToScene(self.graphicsView.mapFromGlobal(center))
        top_left = QtCore.QPoint(center.x() - width // 2, center.y() - height // 2)
        bottom_right = QtCore.QPoint(center.x() + (width - width // 2), center.y() + (height - height // 2))
        rect = QtCore.QRectF(top_left, bottom_right)

        new_bbox = self.graphicsView.add_bbox(rect, None, QtCore.Qt.green)
        self.graphicsView.selected_bbox = new_bbox

        self.bbox_created(rect, show_assistant=False, meta=metadata)

    def delete_selected_row(self):
        if self.selected_row is None or self.selected_row < 0:
            return

        # select new row at same position, or previous row if last
        next_row = self.selected_row

        # last row selected?
        if(next_row == self.tw_labels.rowCount() - 1):
            # next selection will be previous row
            next_row -= 1

        self.delete_row(self.selected_row)

        self.tw_labels.selectRow(next_row)
        self.graphicsView.sticky_bbox = True

    def delete_row(self, row, column=None):
        """(Slot) Delete row from table and associated metadata
        when double clicked."""
        self.tw_labels.selectionModel().blockSignals(True)
        self.tw_labels.removeRow(row)
        del self.data['images'][self.current_file_name]['annotations'][row]
        if self.tw_labels.rowCount() == 0:
            del self.data['images'][self.current_file_name]
        self.tw_labels.selectionModel().blockSignals(False)
        self.tw_labels.clearSelection()
        self.display_bboxes()
        self.set_dirty(True)

    def dirty_data_check(self):
        """Display alert of annotations are dirty and need to be saved before
        proceeding to next step."""
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
        return proceed

    def display_analysts(self):
        if self.data is not None:
            # Backward compatibility check
            if 'analysts' not in self.data:
                self.data['analysts'] = []
            div = ''
            string = ''
            for a in self.data['analysts']:
                string += "{}{}".format(div, a)
                div = ' | '
            self.label_analysts.setText(string)

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

                text = annotation['label']
                combo = QtWidgets.QComboBox()
                combo.addItems(self.labels)
                index = combo.findText(text, QtCore.Qt.MatchFixedString)
                if index >= 0:
                    combo.setCurrentIndex(index)
                else:
                    combo.setCurrentIndex(0)

                # foward change event to cell_changed
                # this crazy lambda construction binds the current value of 'row' in the closure
                combo.currentIndexChanged.connect((lambda bound_row: lambda: self.cell_changed(bound_row, 0))(row))
                self.tw_labels.setCellWidget(row, 0, combo)

                width = int((annotation['bbox']['xmax'] - annotation['bbox']['xmin']) * self.graphicsView.img_size[0])
                height = int((annotation['bbox']['ymax'] - annotation['bbox']['ymin']) * self.graphicsView.img_size[1])
                item = QtWidgets.QTableWidgetItem("{:d} x {:d}".format(width, height))
                self.tw_labels.setItem(row, 1, item)

                item = QtWidgets.QTableWidgetItem()
                item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
                item.setCheckState(QtCore.Qt.Checked if annotation['truncated'] == "Y" else QtCore.Qt.Unchecked)
                self.tw_labels.setItem(row, 2, item)

                item = QtWidgets.QTableWidgetItem()
                item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
                item.setCheckState(QtCore.Qt.Checked if annotation['occluded'] == "Y" else QtCore.Qt.Unchecked)
                self.tw_labels.setItem(row, 3, item)

                item = QtWidgets.QTableWidgetItem()
                item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
                item.setCheckState(QtCore.Qt.Checked if annotation['difficult'] == "Y" else QtCore.Qt.Unchecked)
                self.tw_labels.setItem(row, 4, item)

        self.tw_labels.blockSignals(False)
        self.tw_labels.selectionModel().blockSignals(False)
        self.tw_labels.selectRow(self.selected_row)

    def display_bboxes(self):
        """Display bboxes in graphics scene."""

        annotations = None

        if (self.data is not None and
                self.current_file_name in self.data['images']):
            rec = self.data['images'][self.current_file_name]
            annotations = rec['annotations']

        # forward to graphicsView
        self.graphicsView.display_bboxes(annotations, self.selected_row, self.checkBoxDisplayAnnotationData.isChecked())

    def display_license(self):
        lic = {'license': '', 'license_url': '', 'attribution': ''}
        if (self.data is not None and
                self.current_file_name in self.data['images']):
            rec = self.data['images'][self.current_file_name]
            lic['license'] = rec['license']
            lic['license_url'] = rec['license_url']
            lic['attribution'] = rec['attribution']
        self.license.display_license(lic)

    def enableButtons(self):
        """Enable UI for interacting with the image and annotations"""
        self.pb_zoom_in.setEnabled(True)
        self.pb_zoom_out.setEnabled(True)
        self.pb_visible.setEnabled(True)
        self.pb_previous.setEnabled(True)
        self.pb_previous_ann.setEnabled(True)
        self.pb_next.setEnabled(True)
        self.pb_next_ann.setEnabled(True)
        self.pb_clear.setEnabled(True)

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

    def load_config(self, directory):
        dir_name = directory
        file_name = os.path.join(dir_name, 'bboxee_config.json')
        history = []
        config = {}
        while file_name not in history:
            if os.path.exists(file_name):
                try:
                    f = open(file_name, 'r')
                    config = json.load(f)
                    f.close()
                    if 'labels' in config and 'license' in config:
                        self.labels = config['labels']
                        if 'N/A' not in self.labels:
                            self.labels = ['N/A'] + self.labels
                        self.assistant.set_labels(self.labels)
                        self.license.set_licenses(config['license'])
                        break
                except json.decoder.JSONDecodeError as error:
                    f.close()
                    msg_box = QtWidgets.QMessageBox()
                    msg_box.setWindowTitle('Configuration')
                    msg_box.setText('Found {}'.format(file_name))
                    msg_box.setInformativeText(
                        'Error found in config file: {}'.format(error))
                    msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
                    msg_box.exec()
                    break
                except PermissionError:
                    msg_box = QtWidgets.QMessageBox()
                    msg_box.setWindowTitle('Configuration')
                    msg_box.setText('Found {}'.format(file_name))
                    msg_box.setInformativeText(
                        'You do not have permission to read this file.')
                    msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
                    msg_box.exec()
                    break
            history.append(file_name)
            dir_name = os.path.split(dir_name)[0]
            file_name = os.path.join(dir_name, 'bboxee_config.json')

    def load_from_directory(self):
        """(Slot) Load image data from directory."""
        if self.dirty_data_check():
            directory = (QtWidgets.
                         QFileDialog.
                         getExistingDirectory(self,
                                              'Select Directory',
                                              self.image_directory))
            if directory != '':
                self.load_config(directory)
                self.image_directory = directory
                self.data = schema.annotation_file()
                self.populate_labels()
                self.mask = None
                self.load_image_list()
                self.pb_mask.setEnabled(True)
                self.pb_annotater.setEnabled(True)
                self.set_dirty(False)
                self.label_image_directory.setText(self.image_directory)

    def load_from_file(self):
        """(Slot) Load existing annotation data from file."""
        if self.dirty_data_check():
            file_name = (QtWidgets.
                         QFileDialog.
                         getOpenFileName(self,
                                         'Load Annotations',
                                         self.image_directory,
                                         'BBoxEE (*.bbx)'))
            if file_name[0] != '':
                file = open(file_name[0], 'r')
                self.data = json.load(file)
                file.close()
                self.image_directory = os.path.split(file_name[0])[0]
                self.load_config(self.image_directory)

                self.populate_labels()
                if self.data['mask'] is not None:
                    tmp = np.array(self.data['mask'], dtype='uint8')
                    self.mask = np.dstack((tmp, tmp, tmp))
                else:
                    self.mask = None
                self.display_analysts()
                self.load_image_list()
                self.set_dirty(False)
                self.pb_annotater.setEnabled(True)
                self.pb_mask.setEnabled(True)
                self.label_image_directory.setText(self.image_directory)

    def load_image(self):
        """Load image into graphics scene."""
        if len(self.image_list) > 0:

            self.selected_row = -1
            self.current_file_name = self.image_list[self.current_image - 1]
            filename = os.path.join(self.image_directory, self.current_file_name)

            img = Image.open(filename).convert("RGB")
            array = np.array(img)
            img.close()

            if self.mask is not None:
                array = array * self.mask

            self.graphicsView.load_image(array)
            array = None

            self.enableButtons()
            self.display_bboxes()
            self.display_annotation_data()
            self.graphicsView.setFocus()
            self.display_license()

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

    def populate_labels(self):
        if self.labels is None:
            label_set = set()
            for image_name, annotations in self.data['images'].items():
                for annotation in annotations['annotations']:
                    label_set.add(annotation['label'])

            self.labels = ['N/A'] + list(label_set)
            self.assistant.set_labels(self.labels)

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
        self.graphicsView.resize()

    def save(self):
        """(Slot) Save the annotations to disk."""
        saved = False
        file_name = (QtWidgets.
                     QFileDialog.
                     getSaveFileName(self,
                                     'Save Annotations',
                                     self.image_directory + 'untitled.bbx',
                                     'BBoxEE (*.bbx)'))
        if file_name[0] != '':
            if os.path.samefile(self.image_directory,
                                os.path.split(file_name[0])[0]):
                file = open(file_name[0], 'w')
                json.dump(self.data, file, indent=4)
                file.close()
                self.set_dirty(False)
                saved = True
            else:
                message = ('You are attempting to save the annotations '
                           'outside of the current image directory. '
                           'Operation canceled.\nDATA NOT SAVED.')
                QtWidgets.QMessageBox.warning(self.parent(),
                                              'ERROR',
                                              message,
                                              QtWidgets.QMessageBox.Ok)
        return saved

    def select_annotator(self):
        self.annotator_selecter.show()

    def select_bbox(self, point):
        if (self.data is not None and
                self.current_file_name in self.data['images']):
            width = self.graphicsView.img_size[0]
            height = self.graphicsView.img_size[1]
            rec = self.data['images'][self.current_file_name]
            found = False
            current_index = 0
            distance = 10000000.0
            for index, annotation in enumerate(rec['annotations']):
                x = annotation['bbox']['xmin'] * width
                y = annotation['bbox']['ymin'] * height
                top_left = QtCore.QPointF(x, y)

                x = annotation['bbox']['xmax'] * width
                y = annotation['bbox']['ymax'] * height
                bottom_right = QtCore.QPointF(x, y)

                rect = QtCore.QRectF(top_left, bottom_right)
                if rect.contains(point):
                    found = True
                    line = QtCore.QLineF(point, rect.center())
                    if line.length() < distance:
                        current_index = index
                        distance = line.length()

            if found:
                self.tw_labels.selectRow(current_index)
            else:
                self.tw_labels.clearSelection()

    def select_mask(self):
        """(Slot) Select mask from disk."""
        filter_string = '{}_{}.png'.format(self.graphicsView.img_size[0],
                                           self.graphicsView.img_size[1])
        file = (QtWidgets.
                QFileDialog.getOpenFileName(self,
                                            'Select Mask',
                                            './masks/',
                                            'PNG (*' + filter_string + ')'))
        if file[0] != '':
            img = Image.open(file[0])
            if self.graphicsView.img_size == img.size:
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
        """(Slot) Listen for selection and deselection of rows."""
        if selected.indexes():
            self.selected_row = selected.indexes()[0].row()
            if self.tw_labels.cellWidget(self.selected_row, 0).currentText() != 'N/A':
                rec = self.data['images'][self.current_file_name]
                label = rec['annotations'][self.selected_row]['label']
                self.assistant.set_label(label)
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
            self.pb_save.setDisabled(True)

    def show_assistant(self):
        pos = self.mapToGlobal(self.graphicsView.pos())
        x = pos.x() + (self.graphicsView.width() - self.assistant.width())
        y = pos.y() + (self.graphicsView.height() - self.assistant.height())
        self.assistant.move(x / 2, y / 2)
        self.assistant.show()

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
            ann['bbox']['xmin'] = rect.left() / self.graphicsView.img_size[0]
            ann['bbox']['xmax'] = rect.right() / self.graphicsView.img_size[0]
            ann['bbox']['ymin'] = rect.top() / self.graphicsView.img_size[1]
            ann['bbox']['ymax'] = rect.bottom() / self.graphicsView.img_size[1]
            self.update_annotation(ann)

    def update_license(self, license):
        if (self.data is not None and
                self.current_file_name in self.data['images']):
            rec = self.data['images'][self.current_file_name]
            rec['attribution'] = license['attribution']
            rec['license'] = license['license']
            rec['license_url'] = license['license_url']
