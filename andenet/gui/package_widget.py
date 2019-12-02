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
import random
import numpy as np
from PyQt5 import QtCore, QtWidgets, uic
from andenet.worker import AndenetPackager
from andenet import schema

PACK, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'package_widget.ui'))


class Globber(QtCore.QThread):
    """Threaded worker to keep gui from freezing while search for annotation files."""

    finished = QtCore.pyqtSignal(list)

    def __init__(self):
        """Class init function."""
        QtCore.QThread.__init__(self)
        self.directory = ''

    def run(self):
        """The starting point for the thread."""
        file_list = glob.glob(self.directory + os.path.sep + '**/*.adn', recursive=True)
        self.finished.emit(file_list)


class PackageWidget(QtWidgets.QWidget, PACK):
    """Widget for selecting, relabeling, and packaging annotated images."""

    def __init__(self, parent=None):
        """Class init function."""
        QtWidgets.QWidget.__init__(self, parent)
        self.setupUi(self)
        self.label_cache = {}
        self.remap = {}
        self.globber = Globber()
        self.globber.finished.connect(self.display)

        self.packager = None

        self.pushButtonSelectDirectory.clicked.connect(self.load_annotation_files)
        self.pushButtonPackage.clicked.connect(self.package)

        self.tableWidgetFiles.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tableWidgetFiles.selectionModel().selectionChanged.connect(self.refresh_remap_table)
        self.tableWidgetFiles.horizontalHeader().setSectionResizeMode(0, \
            QtWidgets.QHeaderView.Stretch)

        self.tableWidgetRemap.horizontalHeader().setSectionResizeMode(0, \
            QtWidgets.QHeaderView.Stretch)
        self.tableWidgetRemap.cellChanged.connect(self.update_remap_dictionary)

        self.checkBoxTruncated.stateChanged.connect(self.refresh_remap_table)
        self.checkBoxOccluded.stateChanged.connect(self.refresh_remap_table)
        self.checkBoxDifficult.stateChanged.connect(self.refresh_remap_table)

    def display(self, file_list):
        """(Slot) Display annotation files in table with summary count by label."""
        self.pushButtonSelectDirectory.setEnabled(True)
        self.progressBar.setRange(0, 1)
        self.tableWidgetFiles.setRowCount(len(file_list))
        for index in range(len(file_list)):
            file_name = file_list[index]
            item = QtWidgets.QTableWidgetItem(file_name)
            item.setFlags(QtCore.Qt.ItemIsSelectable)
            self.tableWidgetFiles.setItem(index, 0, item)
            # TODO: Store labels in dictionary to prevent having to re read from file on changes
            labels = self.summarize_labels(file_name)
            string = ''
            for class_name in labels:
                string += class_name + ': ' + str(labels[class_name]) + "\n"
            item = QtWidgets.QTableWidgetItem(string)
            item.setFlags(QtCore.Qt.NoItemFlags)
            self.tableWidgetFiles.setItem(index, 1, item)
            self.tableWidgetFiles.resizeRowToContents(index)
        self.tableWidgetFiles.resizeColumnToContents(1)

    def load_annotation_files(self):
        """(Slot) Select directory and start the globber to search for annotation files."""
        self.label_cache = {}
        directory = QtWidgets.QFileDialog.getExistingDirectory(self)
        if directory != '':
            self.pushButtonSelectDirectory.setEnabled(False)
            self.progressBar.setRange(0, 0)
            self.globber.directory = directory
            self.globber.start()

    def package(self):
        """(Slot) Import and run selected packager."""
        truncated = self.checkBoxTruncated.isChecked()
        occluded = self.checkBoxOccluded.isChecked()
        difficult = self.checkBoxDifficult.isChecked()
        examples = []
        masks = {}
        # Loop through all of the selected rows
        for index in self.tableWidgetFiles.selectionModel().selectedRows():
            file_name = self.tableWidgetFiles.item(index.row(), 0).text()
            # Open the andenet annotation file
            file = open(file_name, 'r')
            data = json.load(file)
            file.close()
            # Add mask to dictionary
            if data['mask_name'] != '':
                mask = np.array(data['mask'], dtype='uint8')
                masks[data['mask_name']] = np.dstack((mask, mask, mask))
            # Loop through images in annotation file
            directory = os.path.split(file_name)[0]
            for file in data['images']:
                example = schema.package_entry()
                example['directory'] = directory
                example['file_name'] = file
                example['mask_name'] = data['mask_name']
                example['attribution'] = data['images'][file]['attribution']
                example['license'] = data['images'][file]['license']
                try:
                    example['license_url'] = data['images'][file]['license_url']
                except (KeyError):
                    example['license_url'] = ''
                
                # Loop through annotations and filter
                for annotation in data['images'][file]['annotations']:
                    if truncated and annotation['truncated'] == 'Y':
                        pass
                    elif occluded and annotation['occluded'] == 'Y':
                        pass
                    elif difficult and annotation['difficult'] == 'Y':
                        pass
                    else:
                        example['annotations'].append(annotation)
                if example['annotations']:
                    examples.append(example)
        random.shuffle(examples)

        # Build the label mapping
        remap = {'lookup': []}
        for index in range(self.tableWidgetRemap.rowCount()):
            key = self.tableWidgetRemap.item(index, 0).text()
            new_key = self.tableWidgetRemap.item(index, 2).text()
            if new_key == '':
                new_key = key
            remap[key] = new_key
            if new_key.lower() != 'exclude' and new_key not in remap['lookup']:
                remap['lookup'].append(new_key)

        # pass data to packager
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select destination')
        if directory != '':
            self.pushButtonPackage.setEnabled(False)
            self.progressBar.setRange(0, len(examples))
            self.packager = AndenetPackager(directory, examples, masks, remap)
            self.packager.progress.connect(self.progressBar.setValue)
            self.packager.packaged.connect(self.packaged)
            self.packager.start()

    def packaged(self):
        """(Slot) Reinable package button when packaging is completed."""
        self.pushButtonPackage.setEnabled(True)

    def refresh_remap_table(self):
        """(Slot) Update the remap table based on selected files and exclude criteria."""
        labels = {}
        truncated = not self.checkBoxTruncated.isChecked()
        occluded = not self.checkBoxOccluded.isChecked()
        difficult = not self.checkBoxDifficult.isChecked()
        for index in self.tableWidgetFiles.selectionModel().selectedRows():
            file = self.tableWidgetFiles.item(index.row(), 0).text()
            label_summary = self.summarize_labels(file, truncated=truncated, \
                occluded=occluded, difficult=difficult)
            for label in label_summary:
                if label in labels:
                    labels[label] += label_summary[label]
                else:
                    labels[label] = label_summary[label]
        self.tableWidgetRemap.blockSignals(True)
        self.tableWidgetRemap.setRowCount(len(labels.keys()))
        row = 0
        for label in sorted(labels.keys()):
            if label not in self.remap:
                self.remap[label] = ''
            item = QtWidgets.QTableWidgetItem(label)
            item.setFlags(QtCore.Qt.NoItemFlags)
            self.tableWidgetRemap.setItem(row, 0, item)
            item = QtWidgets.QTableWidgetItem(str(labels[label]))
            item.setFlags(QtCore.Qt.NoItemFlags)
            self.tableWidgetRemap.setItem(row, 1, item)
            self.tableWidgetRemap.setItem(row, 2, QtWidgets.QTableWidgetItem(self.remap[label]))
            row += 1
        self.tableWidgetRemap.blockSignals(False)

    def summarize_labels(self, file_name, truncated=True, occluded=True, difficult=True):
        """Read labels from original annotaiton file and summarize by file."""
        file = open(file_name, 'r')
        data = json.load(file)
        file.close()
        labels = {}
        if file_name not in self.label_cache:
            self.label_cache[file_name] = {}
            for file in data['images']:
                for annotation in data['images'][file]['annotations']:
                    if annotation['label'] not in self.label_cache[file_name]:
                        self.label_cache[file_name][annotation['label']] = {'full': 0, \
                            'truncated': 0, 'occluded': 0, 'difficult': 0}

                    if annotation['truncated'] == 'Y':
                        self.label_cache[file_name][annotation['label']]['truncated'] += 1
                    elif annotation['occluded'] == 'Y':
                        self.label_cache[file_name][annotation['label']]['occluded'] += 1
                    elif annotation['difficult'] == 'Y':
                        self.label_cache[file_name][annotation['label']]['difficult'] += 1
                    else:
                        self.label_cache[file_name][annotation['label']]['full'] += 1

        for label in self.label_cache[file_name]:
            if label not in labels:
                labels[label] = self.label_cache[file_name][label]['full']
            if truncated:
                labels[label] += self.label_cache[file_name][label]['truncated']
            if occluded:
                labels[label] += self.label_cache[file_name][label]['occluded']
            if difficult:
                labels[label] += self.label_cache[file_name][label]['difficult']
        return labels

    def update_remap_dictionary(self, row, column):
        """(Slot) Update remap dictionary when cell in table changes."""
        label = self.tableWidgetRemap.item(row, 0).text()
        self.remap[label] = self.tableWidgetRemap.item(row, column).text()
