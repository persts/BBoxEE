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
import random
import numpy as np
from PyQt5 import QtCore, QtWidgets, uic

EXTRACT, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'extract_widget.ui'))


# Thread to find all of the *.roi files and prevent the gui from blocking
class Globber(QtCore.QThread):
    finished = QtCore.pyqtSignal(list)

    def __init__(self):
        QtCore.QThread.__init__(self)
        self.directory = ''

    def run(self):
        fileList = glob.glob(self.directory + os.path.sep + '**/*.adn', recursive=True)
        self.finished.emit(fileList)


class ExtractWidget(QtWidgets.QWidget, EXTRACT):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self)
        self.setupUi(self)
        self.remap = {}
        self.globber = Globber()
        self.globber.finished.connect(self.displayFiles)

        self.pushButtonSelectDirectory.clicked.connect(self.loadAnnotationFiles)
        self.pushButtonExport.clicked.connect(self.export)

        self.tableWidgetFiles.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tableWidgetFiles.selectionModel().selectionChanged.connect(self.loadRemapTable)
        self.tableWidgetFiles.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)

        self.tableWidgetRemap.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.tableWidgetRemap.cellChanged.connect(self.cellChanged)

        self.checkBoxTruncated.stateChanged.connect(self.loadRemapTable)
        self.checkBoxOccluded.stateChanged.connect(self.loadRemapTable)
        self.checkBoxDifficult.stateChanged.connect(self.loadRemapTable)

        self.radioButtonTensorFlow.toggled.connect(self.toggleTensorflow)

    def cellChanged(self, theRow, theColumn):
        label = self.tableWidgetRemap.item(theRow, 0).text()
        self.remap[label] = self.tableWidgetRemap.item(theRow, theColumn).text()

    def displayFiles(self, theFileList):
        self.pushButtonSelectDirectory.setEnabled(True)
        self.progressBar.setRange(0, 1)
        self.tableWidgetFiles.setRowCount(len(theFileList))
        for index in range(len(theFileList)):
            file_name = theFileList[index]
            item = QtWidgets.QTableWidgetItem(file_name)
            item.setFlags(QtCore.Qt.ItemIsSelectable)
            self.tableWidgetFiles.setItem(index, 0, item)
            labels = self.extractLabels(file_name)
            string = ''
            for c in labels:
                string += c + ': ' + str(labels[c]) + "\n"
            item = QtWidgets.QTableWidgetItem(string)
            item.setFlags(QtCore.Qt.NoItemFlags)
            self.tableWidgetFiles.setItem(index, 1, item)
            self.tableWidgetFiles.resizeRowToContents(index)
        self.tableWidgetFiles.resizeColumnToContents(1)

    def export(self):
        truncated = self.checkBoxTruncated.isChecked()
        occluded = self.checkBoxOccluded.isChecked()
        difficult = self.checkBoxDifficult.isChecked()
        validation_split = self.doubleSpinBoxValidation.value()
        examples = []
        masks = {}
        train_examples = []
        validation_examples = []
        # Loop through all of the selected rows
        for index in self.tableWidgetFiles.selectionModel().selectedRows():
            file_name = self.tableWidgetFiles.item(index.row(), 0).text()
            # open the andenet annotation file
            file = open(file_name, 'r')
            data = json.load(file)
            file.close()
            # Create a dictionary of the masks
            directory = data['directory']
            if data['mask_name'] != '':
                mask = np.array(data['mask'], dtype='uint8')
                masks[data['mask_name']] = np.dstack((mask, mask, mask))
            for file in data['images']:
                example = {'directory': directory, 'mask_name': data['mask_name'], 'file': file, 'annotations': []}
                for annotation in data['images'][file]:
                    if truncated and annotation['truncated'] == 'Y':
                        pass
                    elif occluded and annotation['occluded'] == 'Y':
                        pass
                    elif difficult and annotation['difficult'] == 'Y':
                        pass
                    else:
                        example['annotations'].append(annotation)
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
            if new_key not in remap['lookup']:
                remap['lookup'].append(new_key)
        # pass data to exporter
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select destination')
        if directory != '':
            self.pushButtonExport.setEnabled(False)
            self.progressBar.setRange(0, len(examples))
            if self.radioButtonTensorFlow.isChecked():
                train_size = int((1.0 - validation_split) * len(examples))
                train_examples = examples[:train_size]
                validation_examples = examples[train_size:]
                from andenet import TfExporter
                self.exporter = TfExporter(directory, train_examples, validation_examples, masks, remap)
            if self.radioButtonAndenet.isChecked():
                from andenet import AndenetExporter
                self.exporter = AndenetExporter(directory, examples, masks, remap)

            self.exporter.progress.connect(self.progressBar.setValue)
            self.exporter.exported.connect(self.exportComplete)
            self.exporter.start()

    def exportComplete(self):
        self.pushButtonExport.setEnabled(True)

    def extractLabels(self, theFile, truncated=True, occluded=True, difficult=True):
        file = open(theFile, 'r')
        data = json.load(file)
        file.close()
        labels = {}
        for file in data['images']:
            for annotation in data['images'][file]:
                if not truncated and annotation['truncated'] == 'Y':
                    pass
                elif not occluded and annotation['occluded'] == 'Y':
                    pass
                elif not difficult and annotation['difficult'] == 'Y':
                    pass
                else:
                    if annotation['label'] not in labels:
                        labels[annotation['label']] = 0
                    labels[annotation['label']] += 1
        return labels

    def loadAnnotationFiles(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self)
        if directory != '':
            self.pushButtonSelectDirectory.setEnabled(False)
            self.progressBar.setRange(0, 0)
            self.globber.directory = directory
            self.globber.start()

    def loadRemapTable(self):
        labels = {}
        truncated = not self.checkBoxTruncated.isChecked()
        occluded = not self.checkBoxOccluded.isChecked()
        difficult = not self.checkBoxDifficult.isChecked()
        for index in self.tableWidgetFiles.selectionModel().selectedRows():
            file = self.tableWidgetFiles.item(index.row(), 0).text()
            l = self.extractLabels(file, truncated=truncated, occluded=occluded, difficult=difficult)
            for label in l:
                if label in labels:
                    labels[label] += l[label]
                else:
                    labels[label] = l[label]
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

    def toggleTensorflow(self, checked):
        if checked:
            self.doubleSpinBoxValidation.setEnabled(True)
        else:
            self.doubleSpinBoxValidation.setEnabled(False)
