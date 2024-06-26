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
import glob
import json
import numpy as np
from PIL import Image
from PyQt6 import QtCore, QtGui, QtWidgets, uic
from bboxee import schema
from bboxee.gui import SelectModelDialog
from bboxee.gui import AnalystDialog
from bboxee.gui import FilterDialog
from .timer import Timer

if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
else:
    bundle_dir = os.path.dirname(__file__)
WIDGET, _ = uic.loadUiType(os.path.join(bundle_dir, 'annotation_widget.ui'))
# TODO: Break this class / widget up into multiple widgets / components.


class AnnotationWidget(QtWidgets.QWidget, WIDGET):
    """Widget for annotating images."""

    file_saved = QtCore.pyqtSignal(str)

    def __init__(self, icon_size=24, parent=None):
        """Class init function."""
        QtWidgets.QWidget.__init__(self, parent)
        self.setupUi(self)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.image_directory = '.'
        self.current_file_name = ''
        self.selected_row = -1
        self.current_image = 1
        self.image_list = []
        self.original_image_list = []
        self.mask = None
        self.data = {}
        self.labels = None
        self.last_label = 'N/A'
        self.dirty = False
        self.qt_image = None

        self.annotator = None
        self.model_selector = SelectModelDialog(self)
        self.model_selector.selected.connect(self.annotator_selected)

        self.graphicsView.created.connect(self.bbox_created)
        self.graphicsView.resized.connect(self.update_bbox)
        self.graphicsView.moved.connect(self.update_bbox)
        self.graphicsView.select_bbox.connect(self.select_bbox)
        self.graphicsView.delete_event.connect(self.delete_selected_row)

        self.pb_directory.clicked.connect(self.load_from_directory)
        self.pb_directory.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_directory.setIcon(QtGui.QIcon('icons:folder.svg'))

        self.pb_label_file.clicked.connect(self.load_from_file)
        self.pb_label_file.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_label_file.setIcon(QtGui.QIcon('icons:file.svg'))

        self.pb_summary.clicked.connect(self.summary)
        self.pb_summary.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_summary.setIcon(QtGui.QIcon('icons:analytics.svg'))

        self.filter_dialog = FilterDialog(self.data, self)
        self.filter_dialog.filtered_list.connect(self.load_image_list)
        self.pb_filter.clicked.connect(self.filter_dialog.show)
        self.pb_filter.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_filter.setIcon(QtGui.QIcon('icons:filter.svg'))

        self.pb_reset_filter.clicked.connect(self.filter_reset)
        self.pb_reset_filter.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_reset_filter.setIcon(QtGui.QIcon('icons:reset.svg'))

        self.pb_review.clicked.connect(self.toggle_for_review)
        self.pb_review.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_review.setIcon(QtGui.QIcon('icons:flag.svg'))

        self.pb_visible.clicked.connect(self.graphicsView.toggle_visibility)
        self.pb_visible.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_visible.setIcon(QtGui.QIcon('icons:visibility.svg'))

        self.pb_zoom_in.clicked.connect(self.graphicsView.zoom_in)
        self.pb_zoom_in.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_zoom_in.setIcon(QtGui.QIcon('icons:zoom_in.svg'))

        self.pb_zoom_out.clicked.connect(self.graphicsView.zoom_out)
        self.pb_zoom_out.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_zoom_out.setIcon(QtGui.QIcon('icons:zoom_out.svg'))

        self.pb_next_ann.clicked.connect(self.next_annotated_image)
        self.pb_next_ann.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_next_ann.setIcon(QtGui.QIcon('icons:skip_next.svg'))

        self.pb_previous_ann.clicked.connect(self.previous_annotated_image)
        self.pb_previous_ann.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_previous_ann.setIcon(QtGui.QIcon('icons:skip_previous.svg'))

        self.pb_next.clicked.connect(self.next_image)
        self.pb_next.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_next.setIcon(QtGui.QIcon('icons:next.svg'))

        self.pb_previous.clicked.connect(self.previous_image)
        self.pb_previous.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_previous.setIcon(QtGui.QIcon('icons:previous.svg'))

        self.pb_clear.clicked.connect(self.clear_annotations)
        self.pb_clear.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_clear.setIcon(QtGui.QIcon('icons:delete.svg'))

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

        self.verticalSliderMidPoint.valueChanged.connect(self.graphicsView.set_mid_point)

        self.tw_labels.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tw_labels.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tw_labels.verticalHeader().sectionClicked.connect(self.set_sticky)
        table_header = self.tw_labels.horizontalHeader()
        table_header.setStretchLastSection(False)
        table_header.ResizeMode = QtWidgets.QHeaderView.ResizeMode.Interactive
        table_header.resizeSection(0, 150)
        table_header.resizeSection(3, 30)
        table_header.resizeSection(4, 30)
        table_header.resizeSection(5, 30)
        table_header.resizeSection(6, 50)

        # Set up auto advance buttom and timersQtGui.QShortcut
        self.pb_auto_advance.clicked.connect(self.auto_advance_clicked)
        self.pb_auto_advance.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.pb_auto_advance.setIcon(QtGui.QIcon('icons:fast_forward.svg'))
        self.timer = Timer()
        self.timer.advance.connect(self.auto_advance)
        self.vs_speed.valueChanged.connect(self.timer.set_speed)
        self.timer_thread = QtCore.QThread()
        self.timer.moveToThread(self.timer_thread)
        self.timer_thread.start()

        #
        # Key bindings
        #

        # Arrow keys move bbox
        self.scut_right_arrow = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Right), self)
        self.scut_right_arrow.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.scut_right_arrow.activated.connect(self.graphicsView.nudge_right)

        self.scut_left_arrow = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Left), self)
        self.scut_left_arrow.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.scut_left_arrow.activated.connect(self.graphicsView.nudge_left)

        self.scut_up_arrow = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Up), self)
        self.scut_up_arrow.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.scut_up_arrow.activated.connect(self.graphicsView.nudge_up)

        self.scut_down_arrow = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Down), self)
        self.scut_down_arrow.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.scut_down_arrow.activated.connect(self.graphicsView.nudge_down)

        # Expand & contract right and top
        self.scut_right_arrow_shift = \
            QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.KeyboardModifier.ShiftModifier | QtCore.Qt.Key.Key_Right), self)
        self.scut_right_arrow_shift.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.scut_right_arrow_shift.activated.connect(self.graphicsView.expand_right)

        self.scut_left_arrow_shift = \
            QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.KeyboardModifier.ShiftModifier | QtCore.Qt.Key.Key_Left), self)
        self.scut_left_arrow_shift.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.scut_left_arrow_shift.activated.connect(self.graphicsView.shrink_left)

        self.scut_up_arrow_shift = \
            QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.KeyboardModifier.ShiftModifier | QtCore.Qt.Key.Key_Up), self)
        self.scut_up_arrow_shift.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.scut_up_arrow_shift.activated.connect(self.graphicsView.expand_up)

        self.scut_down_arrow_shift = \
            QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.KeyboardModifier.ShiftModifier | QtCore.Qt.Key.Key_Down), self)
        self.scut_down_arrow_shift.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.scut_down_arrow_shift.activated.connect(self.graphicsView.shrink_down)

        # Duplicate bbox
        self.scut_duplicate = QtGui.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.KeyboardModifier.ControlModifier | QtCore.Qt.Key.Key_C), self)
        self.scut_duplicate.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.scut_duplicate.activated.connect(self.duplicate_selected_row)

        # Delete bbox
        self.scut_clear = QtGui.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.KeyboardModifier.ControlModifier | QtCore.Qt.KeyboardModifier.ShiftModifier | QtCore.Qt.Key.Key_D), self)
        self.scut_clear.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.scut_clear.activated.connect(self.clear_annotations)

        self.scut_delete = QtGui.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.KeyboardModifier.ControlModifier | QtCore.Qt.Key.Key_D), self)
        self.scut_delete.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.scut_delete.activated.connect(self.delete_selected_row)

        # Toggle bbox visibility
        self.scut_visibility = QtGui.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.KeyboardModifier.ControlModifier | QtCore.Qt.Key.Key_H), self)
        self.scut_visibility.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.scut_visibility.activated.connect(self.graphicsView.toggle_visibility)

        # Next & previous row
        self.scut_next_row = QtGui.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.Key.Key_Tab), self)
        self.scut_next_row.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.scut_next_row.activated.connect(self.next_row)

        self.scut_previous_row = QtGui.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.Key.Key_Backtab), self)
        self.scut_previous_row.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.scut_previous_row.activated.connect(self.prev_row)

        # Next & previous image
        self.scut_next_image = QtGui.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.Key.Key_Space), self)
        self.scut_next_image.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.scut_next_image.activated.connect(self.next_image)

        self.scut_next_annotated_image = QtGui.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.KeyboardModifier.ShiftModifier | QtCore.Qt.Key.Key_Space), self)
        self.scut_next_annotated_image.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.scut_next_annotated_image.activated.connect(self.next_annotated_image)

        self.scut_previous_image = QtGui.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.KeyboardModifier.ControlModifier | QtCore.Qt.Key.Key_Space), self)
        self.scut_previous_image.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.scut_previous_image.activated.connect(self.previous_image)

        self.scut_previous_annotated_image = QtGui.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.KeyboardModifier.ControlModifier | QtCore.Qt.KeyboardModifier.ShiftModifier | QtCore.Qt.Key.Key_Space), self)
        self.scut_previous_annotated_image.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.scut_previous_annotated_image.activated.connect(self.previous_annotated_image)

        # Cancel auto advance
        self.scut_stop_auto_advance = QtGui.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.Key.Key_Escape), self)
        self.scut_stop_auto_advance.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.scut_stop_auto_advance.activated.connect(self.stop_auto_advance)

    def add_analyst(self, name):
        if self.data:
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
        if self.data:
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
            self.pb_cancel.setEnabled(True)

            self.progressBar.setFormat("Loading Model...")
            self.progressBar.setRange(0, len(self.image_list))
            self.progressBar.setValue(0)
            self.annotator.threshold = self.doubleSpinBoxThreshold.value()
            self.annotator.image_directory = self.image_directory
            self.annotator.image_list = self.image_list
            if self.cb_start_and_merge.isChecked():
                self.annotator.starting_image = self.current_image - 1
            else:
                self.annotator.starting_image = 0
            self.annotator.start()

    def annotation_complete(self, data):
        """(SLOT) Automatic annotation complete, reenable gui and
        reset current image to 1."""
        if not self.cb_start_and_merge.isChecked():
            self.data.clear()
            self.data.update(data)
        self.display_analysts()
        self.license.setEnabled(True)
        self.analysts.setEnabled(True)
        self.main_frame.setEnabled(True)
        self.table_frame.setEnabled(True)
        self.pb_annotater.setEnabled(True)
        self.pb_annotate.setEnabled(True)
        self.pb_cancel.setDisabled(True)
        self.set_dirty(True)
        self.current_image = 0
        self.next_image()

    def annotation_progress(self, progress, image, annotations):
        """(SLOT) Show progress and current detections (annotations) as
        they are processed."""
        if progress - 1 != self.current_image:
            self.current_image = progress - 1
        self.progressBar.setValue(progress)
        self.data['images'][image] = annotations
        self.next_image()

    def annotation_started(self):
        self.progressBar.setFormat("%p%")

    def annotator_selected(self, annotator):
        """ (SLOT) save and hook up annotator."""
        self.annotator = annotator
        self.annotator.progress.connect(self.annotation_progress)
        self.annotator.finished.connect(self.annotation_complete)
        self.annotator.model_loaded.connect(self.annotation_started)
        self.pb_cancel.clicked.connect(self.annotator.stop_annotation)
        self.pb_annotate.setEnabled(True)

    def apply_license(self, license):
        if self.data:
            for image in self.data['images']:
                if 'annotations' in self.data['images'][image] and self.data['images'][image]['annotations']:
                    rec = self.data['images'][image]
                    rec['attribution'] = license['attribution']
                    rec['license'] = license['license']
                    rec['license_url'] = license['license_url']
                    self.set_dirty(True)

    def auto_advance(self):
        if self.pb_auto_advance.isChecked():
            if not self.next_image():
                self.pb_auto_advance.setChecked(False)
                self.timer.stop()
        else:
            self.timer.stop()

    def auto_advance_clicked(self):
        if self.pb_auto_advance.isChecked():
            self.timer.start()
        else:
            self.timer.stop()

    def bbox_created(self, rect, image_size, meta=None):
        """(Slot) save the newly created bbox and display it."""
        if rect.width() > 0 and rect.height() > 0:
            self.set_dirty(True)
            if self.current_file_name not in self.data['images']:
                template = schema.annotation_file_entry()
                self.data['images'][self.current_file_name] = template
            rec = self.data['images'][self.current_file_name]
            metadata = schema.annotation()
            metadata['created_by'] = 'human'
            metadata['bbox']['xmin'] = rect.left() / image_size[0]
            metadata['bbox']['xmax'] = rect.right() / image_size[0]
            metadata['bbox']['ymin'] = rect.top() / image_size[1]
            metadata['bbox']['ymax'] = rect.bottom() / image_size[1]

            if meta is not None:
                metadata['label'] = meta['label']
                metadata['truncated'] = meta['truncated']
                metadata['occluded'] = meta['occluded']
                metadata['difficult'] = meta['difficult']
            else:
                metadata['label'] = self.last_label
            rec['annotations'].append(metadata)
            self.display_annotation_data()
            self.selected_row = self.tw_labels.rowCount() - 1
            self.tw_labels.selectRow(self.selected_row)

            self.license.request()
        self.display_bboxes()

    def cell_changed(self, row, column):
        """(Slot) Update annotation data on change."""
        header = self.tw_labels.horizontalHeaderItem(column).text().lower()
        rec = self.data['images'][self.current_file_name]
        if header == 'label':
            text = self.tw_labels.cellWidget(row, column).currentText()
            self.last_label = text
            rec['annotations'][row]['updated_by'] = 'human'
            rec['annotations'][row]['confidence'] = 1.0
            rec['annotations'][row][header] = text
            self.tw_labels.item(row, 1).setText('1.0')
            self.display_bboxes()
        elif header == 'confidence':
            if self.tw_labels.cellWidget(row, column) is not None:
                value = self.tw_labels.cellWidget(row, column).text()
                try:
                    rec['annotations'][row][header] = float(value)
                except ValueError:
                    rec['annotations'][row][header] = 0.0
                self.display_bboxes()
        elif header in ('o', 't', 'd'):
            checked = self.tw_labels.item(row, column).checkState() == QtCore.Qt.Checked
            text = "Y" if checked else "N"
            mapping = {'o': 'occluded', 't': 'truncated', 'd': 'difficult'}
            header = mapping[header]
            rec['annotations'][row][header] = text
        else:
            return
        self.set_dirty(True)

    def clear_annotations(self):
        """(SLOT) Clear all annotations for the current image."""
        self.tw_labels.selectionModel().blockSignals(True)
        self.tw_labels.setRowCount(0)
        self.tw_labels.selectionModel().blockSignals(False)
        self.tw_labels.clearSelection()
        if 'images' in self.data and self.current_file_name in self.data['images']:  # Check
            del self.data['images'][self.current_file_name]
        self.graphicsView.sticky_bbox = False
        self.graphicsView.selected_bbox = None
        self.graphicsView.setFocus()
        self.display_bboxes()
        self.set_dirty(True)

    def delete_click_handler(self):
        """(SLOT) Handle delete button click."""
        # Get button that was clicked
        button = self.sender()
        # Find location in table
        row = self.tw_labels.indexAt(button.pos()).row()
        # Select row and call delete
        self.tw_labels.selectRow(row)
        self.delete_selected_row()

    def delete_row(self, row, column=None):
        """Delete row from table and associated metadata."""
        self.tw_labels.selectionModel().blockSignals(True)
        self.tw_labels.removeRow(row)
        del self.data['images'][self.current_file_name]['annotations'][row]
        if self.tw_labels.rowCount() == 0:
            del self.data['images'][self.current_file_name]
            self.graphicsView.setFocus()
        self.tw_labels.selectionModel().blockSignals(False)
        self.tw_labels.clearSelection()
        self.display_bboxes()
        self.set_dirty(True)

    def delete_selected_row(self):
        if self.selected_row is None or self.selected_row < 0:
            return

        self.delete_row(self.selected_row)
        self.tw_labels.clearSelection()
        self.graphicsView.sticky_bbox = False
        self.graphicsView.selected_bbox = None

    def dirty_data_check(self):
        """Display alert of annotations are dirty and need to be saved before
        proceeding to next step."""
        proceed = True
        if self.dirty:
            msg_box = QtWidgets.QMessageBox(self)
            msg_box.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
            msg_box.setWindowTitle('Unsaved Changes')
            msg_box.setText('Annotations have been modified.')
            msg_box.setInformativeText('Do you want to save your changes?')
            msg_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Save | QtWidgets.QMessageBox.StandardButton.Cancel | QtWidgets.QMessageBox.StandardButton.Ignore)
            msg_box.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Save)
            response = msg_box.exec()
            if response == QtWidgets.QMessageBox.StandardButton.Save:
                proceed = self.save()
            elif response == QtWidgets.QMessageBox.StandardButton.Cancel:
                proceed = False
        return proceed

    def display_analysts(self):
        if self.data:
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
        image_size = self.graphicsView.image_size
        if self.table_frame.isEnabled() and self.current_file_name in self.data['images']:
            rec = self.data['images'][self.current_file_name]
            rows = len(rec['annotations'])
            self.tw_labels.setRowCount(rows)
            for row, annotation in enumerate(rec['annotations']):

                text = annotation['label']
                combo = QtWidgets.QComboBox()
                combo.addItems(self.labels)
                index = combo.findText(text, QtCore.Qt.MatchFlag.MatchFixedString)
                if index >= 0:
                    combo.setCurrentIndex(index)
                else:
                    combo.setCurrentIndex(0)

                combo.currentIndexChanged.connect(self.label_change_handler)
                self.tw_labels.setCellWidget(row, 0, combo)

                conf = ''
                if 'confidence' in annotation:
                    conf = '{:0.2f}'.format(annotation['confidence'])
                item = QtWidgets.QTableWidgetItem(conf)
                self.tw_labels.setItem(row, 1, item)

                width = int((annotation['bbox']['xmax'] - annotation['bbox']['xmin']) * image_size[0])
                height = int((annotation['bbox']['ymax'] - annotation['bbox']['ymin']) * image_size[1])
                item = QtWidgets.QTableWidgetItem("{:d} x {:d}".format(width, height))
                item.setFlags(QtCore.Qt.ItemFlag.ItemIsSelectable)
                self.tw_labels.setItem(row, 2, item)

                item = QtWidgets.QTableWidgetItem()
                item.setFlags(QtCore.Qt.ItemFlag.ItemIsUserCheckable | QtCore.Qt.ItemFlag.ItemIsEnabled)
                item.setCheckState(QtCore.Qt.CheckState.Checked if annotation['truncated'] == "Y" else QtCore.Qt.CheckState.Unchecked)
                self.tw_labels.setItem(row, 3, item)

                item = QtWidgets.QTableWidgetItem()
                item.setFlags(QtCore.Qt.ItemFlag.ItemIsUserCheckable | QtCore.Qt.ItemFlag.ItemIsEnabled)
                item.setCheckState(QtCore.Qt.CheckState.Checked if annotation['occluded'] == "Y" else QtCore.Qt.CheckState.Unchecked)
                self.tw_labels.setItem(row, 4, item)

                item = QtWidgets.QTableWidgetItem()
                item.setFlags(QtCore.Qt.ItemFlag.ItemIsUserCheckable | QtCore.Qt.ItemFlag.ItemIsEnabled)
                item.setCheckState(QtCore.Qt.CheckState.Checked if annotation['difficult'] == "Y" else QtCore.Qt.CheckState.Unchecked)
                self.tw_labels.setItem(row, 5, item)

                delete = QtWidgets.QPushButton()
                delete.setIconSize(QtCore.QSize(24, 24))
                delete.setIcon(QtGui.QIcon('icons:delete.svg'))
                delete.clicked.connect(self.delete_click_handler)
                self.tw_labels.setCellWidget(row, 6, delete)

        self.tw_labels.blockSignals(False)
        self.tw_labels.selectionModel().blockSignals(False)
        self.tw_labels.selectRow(self.selected_row)

    def display_bboxes(self):
        """Display bboxes in graphics scene."""

        annotations = None
        if 'images' in self.data and self.current_file_name in self.data['images']:
            rec = self.data['images'][self.current_file_name]
            annotations = rec['annotations']

        # Forward to graphicsView
        self.graphicsView.display_bboxes(annotations, self.selected_row, self.checkBoxDisplayAnnotationData.isChecked())

    def display_license(self):
        """Pass license object to the license widget for display in UI"""
        lic = {'license': '', 'license_url': '', 'attribution': ''}
        if 'images' in self.data and self.current_file_name in self.data['images']:
            rec = self.data['images'][self.current_file_name]
            try:  # backward compatability
                lic['license'] = rec['license']
                lic['license_url'] = rec['license_url']
                lic['attribution'] = rec['attribution']
            except KeyError:
                pass
        self.license.display_license(lic)

    def duplicate_selected_row(self):
        """Duplicate the currently selected bounding box and place at cursor's location"""
        if self.selected_row is None or self.selected_row < 0:
            return

        # Get metadata
        rec = self.data['images'][self.current_file_name]
        metadata = rec['annotations'][self.selected_row]
        image_size = self.graphicsView.image_size

        # Get rect
        selected_rect = self.graphicsView.selected_bbox.rect()

        # Create new bbox of same size centerd on cursor
        width = selected_rect.width()
        height = selected_rect.height()
        center = QtGui.QCursor.pos()
        center = self.graphicsView.mapToScene(self.graphicsView.mapFromGlobal(center))
        top_left = QtCore.QPointF(center.x() - width // 2, center.y() - height // 2)
        bottom_right = QtCore.QPointF(center.x() + (width - width // 2), center.y() + (height - height // 2))
        rect = QtCore.QRectF(top_left, bottom_right)

        new_bbox = self.graphicsView.add_bbox(rect, None)
        self.graphicsView.selected_bbox = new_bbox

        self.bbox_created(rect, image_size, meta=metadata)

    def enable_buttons(self):
        """Enable UI for interacting with the image and annotations"""
        self.pb_zoom_in.setEnabled(True)
        self.pb_zoom_out.setEnabled(True)
        self.pb_visible.setEnabled(True)
        self.pb_previous.setEnabled(True)
        self.pb_previous_ann.setEnabled(True)
        self.pb_next.setEnabled(True)
        self.pb_next_ann.setEnabled(True)
        self.pb_clear.setEnabled(True)
        self.pb_summary.setEnabled(True)
        self.pb_auto_advance.setEnabled(True)
        self.pb_filter.setEnabled(True)
        self.pb_review.setEnabled(True)
        self.pb_reset_filter.setEnabled(True)

    def filter_reset(self):
        self.image_list = self.original_image_list
        self.filter_dialog.input_label.setText("")
        self.filter_dialog.cb_flagged.setChecked(False)
        self.filter_dialog.cb_case_sensitive.setChecked(False)
        self.load_first_image()

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

    def label_change_handler(self):
        """(SLOT) Handle index change from lable combobox."""
        # Get combobox that changed
        cbox = self.sender()
        # Find location in table
        row = self.tw_labels.indexAt(cbox.pos()).row()
        # Select row and call delete
        self.cell_changed(row, 0)

    def load_config(self, directory):
        dir_name = directory
        file_name = os.path.join(dir_name, 'bboxee_config.json')
        history = []
        config = {}
        while file_name not in history:
            if os.path.exists(file_name):
                f = None
                try:
                    f = open(file_name, 'r')
                    config = json.load(f)
                    f.close()
                    if 'labels' in config and 'license' in config:
                        self.labels = config['labels']
                        if 'N/A' not in self.labels:
                            self.labels = ['N/A'] + self.labels
                        self.license.set_licenses(config['license'])
                        break
                except json.decoder.JSONDecodeError as error:
                    f.close()
                    msg_box = QtWidgets.QMessageBox()
                    msg_box.setWindowTitle('Configuration')
                    msg_box.setText('Found {}'.format(file_name))
                    msg_box.setInformativeText(
                        'Error found in config file: {}'.format(error))
                    msg_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
                    msg_box.exec()
                    break
                except PermissionError:
                    msg_box = QtWidgets.QMessageBox()
                    msg_box.setWindowTitle('Configuration')
                    msg_box.setText('Found {}'.format(file_name))
                    msg_box.setInformativeText(
                        'You do not have permission to read this file.')
                    msg_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
                    msg_box.exec()
                    break
            history.append(file_name)
            dir_name = os.path.split(dir_name)[0]
            file_name = os.path.join(dir_name, 'bboxee_config.json')

    def load_first_image(self):
        # Update UI
        self.enable_buttons()
        self.current_image = 1
        self.labelImages.setText('of ' + str(len(self.image_list)))
        self.lineEditCurrentImage.setText('1')
        self.graphicsView.pixmap = None  # Force resize

        self.load_image()

    def load_from_directory(self):
        """(Slot) Load image data from directory."""
        if self.dirty_data_check():
            directory = (QtWidgets.
                         QFileDialog.
                         getExistingDirectory(self,
                                              'Select Directory',
                                              self.image_directory))
            if directory != '':
                # Search for first instance of config file and load the labels
                self.image_directory = directory
                self.load_config(directory)
                self.populate_labels()

                # Generate an empty version of the schema
                self.data.clear()
                self.data.update(schema.annotation_file())
                self.mask = None

                # Update UI
                self.pb_mask.setEnabled(True)
                self.pb_annotater.setEnabled(True)
                self.set_dirty(False)
                self.label_image_directory.setText(self.image_directory)

                # Load images from image directory
                self.load_image_list()

    def load_from_file(self, file_name=False):
        """(Slot) Load existing annotation data from file."""
        if self.dirty_data_check():
            if not file_name:
                file_name = QtWidgets.QFileDialog.getOpenFileName(self, 'Load Annotations', self.image_directory, 'BBoxEE (*.bbx)')
                file_name = file_name[0]

            if file_name != '':
                # Read the bbx file
                file = open(file_name, 'r')
                self.data.clear()
                self.data.update(json.load(file))
                file.close()

                # Search for first instance of config file and load the labels
                self.image_directory = os.path.split(file_name)[0]
                self.load_config(self.image_directory)
                self.populate_labels()

                if self.data['mask'] is not None:
                    tmp = np.array(self.data['mask'], dtype='uint8')
                    self.mask = np.dstack((tmp, tmp, tmp))
                else:
                    self.mask = None

                # Backward compatability.
                # Update schema but don't mark as dirty
                if self.data['schema'] == '1.0.0':
                    self.data['review'] = []
                    self.data['skip_export'] = []
                    self.data['schema'] = '1.1.0'

                # Update UI
                self.display_analysts()
                self.set_dirty(False)
                self.pb_annotater.setEnabled(True)
                self.pb_mask.setEnabled(True)
                self.label_image_directory.setText(self.image_directory)

                # Load images from image directory
                self.load_image_list()

    def load_image(self):
        """Load image into graphics scene."""
        if len(self.image_list) > 0:

            self.selected_row = -1
            self.current_file_name = self.image_list[self.current_image - 1]

            # Load the image and apply the mask
            filename = os.path.join(self.image_directory, self.current_file_name)
            img = Image.open(filename).convert("RGB")
            array = np.array(img)
            img.close()
            if self.mask is not None:
                array = array * self.mask

            self.graphicsView.load_image(array)
            array = None

            # Update UI
            self.update_review_button()
            self.display_bboxes()
            self.display_annotation_data()
            self.graphicsView.setFocus()
            self.display_license()

    def load_image_list(self, image_list=[]):
        """Glob the image files and save to image list."""
        # Check if image_list is being passed in from filter dialog
        if len(image_list) > 0:
            self.image_list = image_list

        # Glob the directory and filter for images
        if len(image_list) == 0 and self.image_directory != '':
            self.original_image_list = []
            self.image_list = []
            self.image_directory += os.path.sep
            files = glob.glob(self.image_directory + '*')
            image_format = [".jpg", ".jpeg", ".png"]
            f = (lambda x: os.path.splitext(x)[1].lower() in image_format)
            self.image_list = list(filter(f, files))
            self.image_list = [os.path.basename(x) for x in self.image_list]
            self.image_list = sorted(self.image_list)
            # JY: Store original_image_list in filter dialog
            self.original_image_list = self.image_list

        # If images exist load the first one
        if len(self.image_list) > 0:
            self.load_first_image()

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
            return True
        else:
            return False

    def next_row(self):
        if self.tw_labels.rowCount() != 0:
            self.tw_labels.selectRow((self.selected_row + 1) % self.tw_labels.rowCount())
            self.graphicsView.sticky_bbox = True
        else:
            self.graphicsView.sticky_bbox = False

    def populate_labels(self):
        if self.labels is None:
            label_set = set()
            if 'images' in self.data:
                for image_name, annotations in self.data['images'].items():
                    for annotation in annotations['annotations']:
                        label_set.add(annotation['label'])

            self.labels = ['N/A'] + list(label_set)

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

    def prev_row(self):
        self.tw_labels.selectRow((self.selected_row - 1) % self.tw_labels.rowCount())
        self.graphicsView.sticky_bbox = True

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
                self.file_saved.emit(file_name[0])
            else:
                message = ('You are attempting to save the annotations '
                           'outside of the current image directory. '
                           'Operation canceled.\nDATA NOT SAVED.')
                QtWidgets.QMessageBox.warning(self.parent(),
                                              'ERROR',
                                              message,
                                              QtWidgets.QMessageBox.StandardButton.Ok)
        return saved

    def select_annotator(self):
        self.model_selector.show()

    def select_bbox(self, point):
        if 'images' in self.data and self.current_file_name in self.data['images']:
            width = self.graphicsView.image_size[0]
            height = self.graphicsView.image_size[1]
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
                # Set focus to combobox to allow keyboard entry shortcuts
                self.tw_labels.cellWidget(current_index, 0).setFocus()
            else:
                self.tw_labels.clearSelection()
                # Clear the focus from previous combobox
                self.graphicsView.setFocus()

    def select_mask(self):
        """(Slot) Select mask from disk."""
        filter_string = '{}_{}.png'.format(self.graphicsView.image_size[0],
                                           self.graphicsView.image_size[1])
        file = (QtWidgets.
                QFileDialog.getOpenFileName(self,
                                            'Select Mask',
                                            './masks/',
                                            'PNG (*' + filter_string + ')'))
        if file[0] != '':
            img = Image.open(file[0])
            if self.graphicsView.image_size == img.size:
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
        else:
            self.selected_row = -1
            self.graphicsView.selected_bbox = None
            self.graphicsView.sticky_bbox = False

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

    def set_sticky(self):
        self.graphicsView.sticky_bbox = True

    def stop_auto_advance(self):
        self.timer.stop()
        self.pb_auto_advance.setChecked(False)

    def summary(self):
        summary = {}
        if 'images' in self.data:
            for image in self.data['images']:
                for ann in self.data['images'][image]['annotations']:
                    if ann['label'] not in summary:
                        summary[ann['label']] = 0
                    summary[ann['label']] += 1

            message = ''
            for label in summary:
                message += "{}: {}\n".format(label, summary[label])
            QtWidgets.QMessageBox.information(self, 'Annotation Summary', message)

    def toggle_for_review(self):
        if self.pb_review.isChecked():
            self.data['review'].append(self.current_file_name)
        else:
            if self.current_file_name in self.data['review']:
                self.data['review'].remove(self.current_file_name)

        self.set_dirty(True)
        self.update_review_button()

    def update_annotation(self, annotation_data):
        """(Slot) Update annotation table widget."""
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
            ann['confidence'] = 1.0
            ann['bbox']['xmin'] = rect.left() / self.graphicsView.image_size[0]
            ann['bbox']['xmax'] = rect.right() / self.graphicsView.image_size[0]
            ann['bbox']['ymin'] = rect.top() / self.graphicsView.image_size[1]
            ann['bbox']['ymax'] = rect.bottom() / self.graphicsView.image_size[1]
            self.update_annotation(ann)

    def update_license(self, license):
        if 'images' in self.data and self.current_file_name in self.data['images']:
            rec = self.data['images'][self.current_file_name]
            rec['attribution'] = license['attribution']
            rec['license'] = license['license']
            rec['license_url'] = license['license_url']

    def update_review_button(self):
        if self.current_file_name in self.data['review']:
            self.pb_review.setIcon(QtGui.QIcon('icons:flagged.svg'))
            self.pb_review.setChecked(True)
        else:
            self.pb_review.setIcon(QtGui.QIcon('icons:flag.svg'))
            self.pb_review.setChecked(False)
