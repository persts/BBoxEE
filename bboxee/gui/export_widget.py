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
from PyQt6 import QtCore, QtWidgets, QtGui, uic
from bboxee.gui import CocoDialog
from bboxee import schema
from bboxee.gui import FilterDialog

if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
else:
    bundle_dir = os.path.dirname(__file__)
EXPORT, _ = uic.loadUiType(os.path.join(bundle_dir, 'export_widget.ui'))


class Globber(QtCore.QThread):
    """Threaded worker to keep gui from freezing while search
       for and pre-processing annotation files."""

    progress = QtCore.pyqtSignal(int)
    finished = QtCore.pyqtSignal(dict, dict)
    init_progress = QtCore.pyqtSignal(int, str)

    def __init__(self):
        """Class init function."""
        QtCore.QThread.__init__(self)
        self.directory = ''

    def run(self):
        """The starting point for the thread."""
        self.init_progress.emit(0, 'Scanning...')
        file_list = glob.glob(self.directory + os.path.sep + '**/*.bbx',
                              recursive=True)
        self.init_progress.emit(len(file_list), 'Parsing %p%')
        data = {}
        masks = {}
        for p, bbx_file in enumerate(file_list):
            # Read labels from original annotaiton file and summarize by file.
            file = open(bbx_file, 'r')
            contents = json.load(file)
            file.close()

            data[bbx_file] = {'summary': '',
                              'labels': {},
                              'images': {},
                              'mask_name': '',
                              'flagged_images': False}
            # Backward compatability check
            if 'review' in contents:
                # Determine if bbx file contains images flagged for review
                data[bbx_file]['flagged_images'] = len(contents['review']) > 0

            summary = {}
            # Store mask and set name in data object
            if contents['mask_name'] != '':
                if contents['mask_name'] not in masks:
                    masks[contents['mask_name']] = contents['mask']
            data[bbx_file]['mask_name'] = contents['mask_name']
            # Loop through all of the images and summarize
            for entry in contents['images']:
                data[bbx_file]['images'][entry] = contents['images'][entry]
                labels = {}
                exclusions = {}

                annotations = contents['images'][entry]['annotations']
                for annotation in annotations:
                    if annotation['label'] not in labels:
                        labels[annotation['label']] = 1
                    else:
                        labels[annotation['label']] += 1

                    if annotation['label'] not in summary:
                        summary[annotation['label']] = 1
                    else:
                        summary[annotation['label']] += 1

                    if annotation['truncated'] == "Y":
                        exclusions['truncated'] = True
                    if annotation['occluded'] == "Y":
                        exclusions['occluded'] = True
                    if annotation['difficult'] == "Y":
                        exclusions['difficult'] = True
                tmp = contents['images'][entry]
                tmp['exclusions'] = exclusions
                tmp['labels'] = labels
            string = ''
            data[bbx_file]['labels'] = summary
            for label in summary:
                string += label + ': ' + str(summary[label]) + "\n"
            data[bbx_file]['summary'] = string
            self.progress.emit(p + 1)
        self.finished.emit(data, masks)


class ExportWidget(QtWidgets.QWidget, EXPORT):
    """Widget for selecting, relabeling, and exporting annotated images."""

    def __init__(self, icon_size, parent=None):
        """Class init function."""
        QtWidgets.QWidget.__init__(self, parent)
        self.setupUi(self)
        self.base_data = {}
        self.masks = {}
        self.label_map = {}
        self.exporter = None

        self.globber = Globber()
        self.globber.finished.connect(self.display)
        self.globber.init_progress.connect(self.init_progress_bar)
        self.globber.progress.connect(self.progressBar.setValue)

        size = QtCore.QSize(icon_size, icon_size)
        self.pb_select_directory.setIconSize(size)
        self.pb_select_directory.setIcon(QtGui.QIcon('icons:folder.svg'))
        self.pb_select_directory.clicked.connect(self.load_annotation_files)

        self.pb_label_map.setIconSize(size)
        self.pb_label_map.setIcon(QtGui.QIcon('icons:file.svg'))
        self.pb_label_map.clicked.connect(self.load_label_map)

        self.pb_search.setIconSize(size)
        self.pb_search.setIcon(QtGui.QIcon('icons:search.svg'))
        self.filter_dialog = FilterDialog(self.base_data, self)
        self.pb_search.clicked.connect(self.filter_dialog.show)

        self.comboBoxFormat.currentIndexChanged.connect(self.check_format)

        self.pb_export.clicked.connect(self.export_preflight)
        self.pb_cancel.clicked.connect(self.cancel)

        self.tw_files.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tw_files.selectionModel().selectionChanged.connect(self.selection_changed)
        self.tw_files.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)

        self.tw_remap.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.tw_remap.cellChanged.connect(self.update_label_map)

        self.cb_truncated.stateChanged.connect(self.exclude_changed)
        self.cb_occluded.stateChanged.connect(self.exclude_changed)
        self.cb_difficult.stateChanged.connect(self.exclude_changed)

        # Find and shade the header select all button and make more visible
        corner = self.tw_files.findChild(QtWidgets.QAbstractButton)
        corner.setStyleSheet("background-color: #CCC;")

    def cancel(self):
        if self.exporter is not None:
            self.exporter.stop = True

    def check_format(self, index):
        format = self.comboBoxFormat.currentText()
        if format == 'TensorFlow Record':
            self.spinBoxShards.setEnabled(True)
        else:
            self.spinBoxShards.setEnabled(False)

    def display(self, data, masks):
        """(Slot) Display annotation files in table with summary count
        by label."""
        self.tw_files.setRowCount(len(data))
        for index, bbx_file in enumerate(data):
            item = QtWidgets.QTableWidgetItem(bbx_file)
            item.setFlags(QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.tw_files.setItem(index, 0, item)

            item = QtWidgets.QTableWidgetItem(data[bbx_file]['summary'])
            item.setFlags(QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.tw_files.setItem(index, 1, item)
            self.tw_files.resizeRowToContents(index)
        self.tw_files.resizeColumnToContents(1)
        self.pb_select_directory.setEnabled(True)
        self.pb_export.setEnabled(True)
        self.pb_search.setEnabled(True)
        self.progressBar.setRange(0, 1)
        self.base_data.update(data)
        self.masks = masks

    def exclude_changed(self):
        labels = {}
        cbt = self.cb_truncated.isChecked()
        cbo = self.cb_occluded.isChecked()
        cbd = self.cb_difficult.isChecked()
        for index in self.tw_files.selectionModel().selectedRows():
            bbx_file = self.tw_files.item(index.row(), 0).text()
            for label in self.base_data[bbx_file]['labels']:
                if label not in labels:
                    labels[label] = self.base_data[bbx_file]['labels'][label]
                else:
                    labels[label] += self.base_data[bbx_file]['labels'][label]
            # If something is checked find and subtract from total
            if cbt or cbo or cbd:
                for image in self.base_data[bbx_file]['images']:
                    entry = self.base_data[bbx_file]['images'][image]
                    match = False
                    if cbt and 'truncated' in entry['exclusions']:
                        match = True
                    if cbo and 'occluded' in entry['exclusions']:
                        match = True
                    if cbd and 'difficult' in entry['exclusions']:
                        match = True
                    if match:
                        for label in entry['labels']:
                            labels[label] -= entry['labels'][label]

        self.update_remap_table(labels)

    def export(self, images):
        export_to = self.comboBoxFormat.currentText()
        validation_split = self.doubleSpinBoxSplit.value()
        shards = self.spinBoxShards.value()
        module_loaded = False
        if export_to == 'TensorFlow Record':
            try:
                from bboxee.exporter.tfrecord import Exporter
                module_loaded = True
            except ModuleNotFoundError:
                message = 'Required TensorFlow modules not found.'
                QtWidgets.QMessageBox.critical(self, 'Export', message)
        elif export_to == 'YOLOv5':
            from bboxee.exporter.yolo import Exporter
            module_loaded = True
        elif export_to == 'COCO':
            from bboxee.exporter.coco import Exporter
            module_loaded = True
        if module_loaded:
            directory = (QtWidgets.
                         QFileDialog.
                         getExistingDirectory(self, 'Select destination'))
            if directory != '':
                self.exporter = Exporter(directory,
                                         images,
                                         self.label_map,
                                         validation_split,
                                         shards,
                                         self.masks,
                                         self.cb_strip_metadata.isChecked())
                if export_to == 'COCO':
                    diag = CocoDialog(self)
                    accepted = diag.exec()
                    self.exporter.info = diag.info
                    if accepted == 0:
                        return

                self.pb_export.setEnabled(False)
                self.pb_select_directory.setEnabled(False)
                self.init_progress_bar(len(images), 'Exporting %p%')
                self.exporter.progress.connect(self.progressBar.setValue)
                self.exporter.exported.connect(self.exported)
                self.exporter.start()

    def export_preflight(self):
        """(Slot) Prepare data and select exporter."""
        cbt = self.cb_truncated.isChecked()
        cbo = self.cb_occluded.isChecked()
        cbd = self.cb_difficult.isChecked()
        images = []

        # Build an excluded label list
        excludes = []
        for label in self.label_map:
            if self.label_map[label].lower() == 'exclude':
                excludes.append(label)
        # Loop through all of the selected rows
        for index in self.tw_files.selectionModel().selectedRows():
            bbx_file = self.tw_files.item(index.row(), 0).text()
            img_list = self.base_data[bbx_file]['images']

            # Loop through images in annotation file
            directory = os.path.split(bbx_file)[0]
            for img_name in img_list:
                process = True
                entry = img_list[img_name]
                if cbt or cbo or cbd:
                    if cbt and 'truncated' in entry['exclusions']:
                        process = False
                    if cbo and 'occluded' in entry['exclusions']:
                        process = False
                    if cbd and 'difficult' in entry['exclusions']:
                        process = False
                for label in excludes:
                    if label in entry['labels']:
                        process = False
                if process and len(entry['annotations']) > 0:
                    image = schema.package_entry()
                    image['directory'] = directory
                    image['file_name'] = img_name
                    image['mask_name'] = self.base_data[bbx_file]['mask_name']
                    image['attribution'] = entry['attribution']
                    image['license'] = entry['license']
                    try:
                        url = entry['license_url']
                        image['license_url'] = url
                    except (KeyError):
                        image['license_url'] = ''
                    image['annotations'] = entry['annotations']
                    images.append(image)
        self.export(images)

    def exported(self, train_size, val_size):
        """(Slot) Enable buttons when packaging is completed."""
        message = "Training images: {}\nValidation images: {} ".format(train_size, val_size)
        QtWidgets.QMessageBox.information(self, 'Export Summary', message)
        self.pb_export.setEnabled(True)
        self.pb_select_directory.setEnabled(True)

    def init_progress_bar(self, maxiumum, string="%p%"):
        """(Slot) Initalize progress bar."""
        self.progressBar.setRange(0, maxiumum)
        self.progressBar.setFormat(string)

    def load_annotation_files(self):
        """(Slot) Select directory and start the globber to search
        for annotation files."""
        directory = QtWidgets.QFileDialog.getExistingDirectory(self)
        if directory != '':
            self.pb_select_directory.setEnabled(False)
            self.pb_export.setEnabled(False)
            self.progressBar.setRange(0, 0)
            self.globber.directory = directory
            self.globber.start()

    def load_label_map(self):
        file_name = (QtWidgets.QFileDialog.getOpenFileName(self, 'Load Remap File', ".", 'JSON (*.json)'))
        if file_name[0] != '':
            try:
                file = open(file_name[0], 'r')
                self.label_map = json.load(file)
                file.close()
            except json.decoder.JSONDecodeError as error:
                file.close()
                msg_box = QtWidgets.QMessageBox()
                msg_box.setWindowTitle('Label Map')
                msg_box.setText('{}'.format(file_name))
                msg_box.setInformativeText(
                    'Error found in remap object: {}'.format(error))
                msg_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
                msg_box.exec()
            except PermissionError:
                msg_box = QtWidgets.QMessageBox()
                msg_box.setWindowTitle('Label Map')
                msg_box.setText('{}'.format(file_name))
                msg_box.setInformativeText(
                    'You do not have permission to read this file.')
                msg_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
                msg_box.exec()
            self.selection_changed()

    def selection_changed(self):
        labels = {}
        for index in self.tw_files.selectionModel().selectedRows():
            bbx_file = self.tw_files.item(index.row(), 0).text()
            for label in self.base_data[bbx_file]['labels']:
                if label not in labels:
                    labels[label] = self.base_data[bbx_file]['labels'][label]
                else:
                    labels[label] += self.base_data[bbx_file]['labels'][label]
        self.update_remap_table(labels)

    def update_label_map(self, row, column):
        """(Slot) Update label map when cell in table changes."""
        label = self.tw_remap.item(row, 0).text()
        self.label_map[label] = self.tw_remap.item(row, column).text()

    def update_remap_table(self, labels):
        self.tw_remap.blockSignals(True)
        self.tw_remap.setRowCount(len(labels.keys()))
        for row, label in enumerate(sorted(labels.keys())):
            if label not in self.label_map:
                self.label_map[label] = ''
            item = QtWidgets.QTableWidgetItem(label)
            item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.tw_remap.setItem(row, 0, item)
            item = QtWidgets.QTableWidgetItem(str(labels[label]))
            item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.tw_remap.setItem(row, 1, item)
            item = QtWidgets.QTableWidgetItem(self.label_map[label])
            self.tw_remap.setItem(row, 2, item)
        self.tw_remap.blockSignals(False)
