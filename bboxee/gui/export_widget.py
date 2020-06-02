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
from PyQt5 import QtCore, QtWidgets, QtGui, uic
from bboxee.gui import CocoDialog
from bboxee import schema

EXPORT, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__),
                           'export_widget.ui'))


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
                              'mask_name': ''}
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
            self.progress.emit(p+1)
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

        self.globber = Globber()
        self.globber.finished.connect(self.display)
        self.globber.init_progress.connect(self.init_progress_bar)
        self.globber.progress.connect(self.progressBar.setValue)

        size = QtCore.QSize(icon_size, icon_size)
        self.pb_select_directory.setIconSize(size)
        self.pb_select_directory.setIcon(QtGui.QIcon(':/icons/folder.svg'))
        self.pb_select_directory.clicked.connect(self.load_annotation_files)

        self.pb_export.clicked.connect(self.export_preflight)

        (self.tw_files.
            setSelectionBehavior(QtWidgets.
                                 QAbstractItemView.SelectRows))
        (self.tw_files.
            selectionModel().
            selectionChanged.
            connect(self.selection_changed))
        (self.tw_files.
            horizontalHeader().
            setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch))

        (self.tw_remap.
            horizontalHeader().
            setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch))
        self.tw_remap.cellChanged.connect(self.update_label_map)

        self.cb_truncated.stateChanged.connect(self.exclude_changed)
        self.cb_occluded.stateChanged.connect(self.exclude_changed)
        self.cb_difficult.stateChanged.connect(self.exclude_changed)

    def display(self, data, masks):
        """(Slot) Display annotation files in table with summary count
        by label."""
        self.tw_files.setRowCount(len(data))
        for index, bbx_file in enumerate(data):
            item = QtWidgets.QTableWidgetItem(bbx_file)
            item.setFlags(QtCore.Qt.ItemIsSelectable)
            self.tw_files.setItem(index, 0, item)

            item = QtWidgets.QTableWidgetItem(data[bbx_file]['summary'])
            item.setFlags(QtCore.Qt.ItemIsSelectable)
            self.tw_files.setItem(index, 1, item)
            self.tw_files.resizeRowToContents(index)
        self.tw_files.resizeColumnToContents(1)
        self.pb_select_directory.setEnabled(True)
        self.pb_export.setEnabled(True)
        self.progressBar.setRange(0, 1)
        self.base_data = data
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
        module_loaded = False
        if export_to == 'Tensorflow Record':
            try:
                from bboxee.exporter.tfrecord import Exporter
                module_loaded = True
            except ModuleNotFoundError:
                message = 'Required Tensorflow modules not found.' \
                    '\n\nPlease review install requirements.'
                QtWidgets.QMessageBox.critical(self, 'Export', message)
        elif export_to == 'Darknet YOLOv3':
            try:
                from bboxee.exporter.yolo import Exporter
                module_loaded = True
            except ModuleNotFoundError:
                message = 'Required Torch or Yolov3 modules not found.\n\n' \
                    'Please review install requirements.'
                QtWidgets.QMessageBox.critical(self, 'Export', message)
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
                if process:
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

    def exported(self):
        """(Slot) Enable buttons when packaging is completed."""
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
        row = 0
        for label in sorted(labels.keys()):
            if label not in self.label_map:
                self.label_map[label] = ''
            item = QtWidgets.QTableWidgetItem(label)
            item.setFlags(QtCore.Qt.NoItemFlags)
            self.tw_remap.setItem(row, 0, item)
            item = QtWidgets.QTableWidgetItem(str(labels[label]))
            item.setFlags(QtCore.Qt.NoItemFlags)
            self.tw_remap.setItem(row, 1, item)
            item = QtWidgets.QTableWidgetItem(self.label_map[label])
            self.tw_remap.setItem(row, 2, item)
            row += 1
        self.tw_remap.blockSignals(False)
