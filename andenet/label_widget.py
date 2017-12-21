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
import pickle
import datetime
import numpy as np
from PIL import Image, ImageQt
from .label_assistant import LabelAssistant
from PyQt5 import QtCore, QtGui, QtWidgets, uic

LABEL, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'label_widget.ui'))


class LabelWidget(QtWidgets.QWidget, LABEL):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self)
        self.setupUi(self)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setWindowTitle('Annotation Tool')
        self.directory = '.'
        self.currentFileName = ''
        self.rois = []
        self.selectedRow = -1
        self.currentImage = 1
        self.imageList = []
        self.mask = None
        self.data = self._baseSchema()
        self.dataDirty = False
        self.assistant = LabelAssistant(self)
        self.assistant.submitted.connect(self.updateAnnotation)

        self.graphicsScene = QtWidgets.QGraphicsScene()
        self.graphicsView.setScene(self.graphicsScene)
        self.graphicsView.roiCreated.connect(self.roiCreated)
        self.graphicsView.roiResized.connect(self.updateRoi)

        self.pushButtonAnnotatedNext.clicked.connect(self.nextAnnotatedImage)
        self.pushButtonAnnotatedPrevious.clicked.connect(self.previousAnnotatedImage)
        self.pushButtonDirectory.clicked.connect(self.loadFromDirectory)
        self.pushButtonLabelFile.clicked.connect(self.loadFromFile)
        self.pushButtonNext.clicked.connect(self.nextImage)
        self.pushButtonPrevious.clicked.connect(self.previousImage)
        self.pushButtonSave.clicked.connect(self.save)
        self.pushButtonSelectMask.clicked.connect(self.selectMask)
        self.lineEditCurrentImage.editingFinished.connect(self.jumpToImage)
        self.tableWidgetLabels.selectionModel().currentRowChanged.connect(self.rowChanged)
        self.tableWidgetLabels.cellChanged.connect(self.cellChanged)
        self.tableWidgetLabels.cellDoubleClicked.connect(self.deleteRow)

        self.tableWidgetLabels.horizontalHeader().setStretchLastSection(False)
        self.tableWidgetLabels.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)

    def _annotationSchema(self):
        return {'bbox': None, 'label': 'N/A', 'occluded': 'N', 'truncated': 'N', 'difficult': 'N'}

    def _baseSchema(self):
        return {'directory': '', 'mask': None, 'mask_name': '', 'images': {}, 'schema': 'v1'}

    def cellChanged(self, theRow, theColumn):
        text = self.tableWidgetLabels.item(theRow, theColumn).text()
        column = self.tableWidgetLabels.horizontalHeaderItem(theColumn).text().lower()
        if column == 'occluded' or column == 'truncated' or column == 'difficult':
            if text in ['Y', 'y', 'N', 'n']:
                text = text.upper()
            else:
                text = self.data['images'][self.currentFileName][theRow][column]
                self.tableWidgetLabels.setItem(theRow, theColumn, QtWidgets.QTableWidgetItem(text))
        else:
            text = text.lower()
        self.data['images'][self.currentFileName][theRow][column] = text
        self.setDirty(True)

    def deleteRow(self, theRow, theColumn):
        self.tableWidgetLabels.selectionModel().blockSignals(True)
        self.tableWidgetLabels.removeRow(theRow)
        self.graphicsView.roiSelector.hide()
        del self.data['images'][self.currentFileName][theRow]
        self.tableWidgetLabels.selectionModel().blockSignals(False)
        self.selectedRow = -1
        self.displayRois()

    def displayRois(self):
        if len(self.rois) > 0:
            for roi in self.rois:
                self.graphicsScene.removeItem(roi)
            self.rois = []
        if self.currentFileName in self.data['images']:
            for i in range(len(self.data['images'][self.currentFileName])):
                roi = self.data['images'][self.currentFileName][i]
                if i == self.selectedRow:
                    rect = QtCore.QRectF(roi['bbox'][0], roi['bbox'][1], roi['bbox'][2], roi['bbox'][3])
                    self.graphicsView.showRoiSelector(rect)
                else:
                    rect = QtCore.QRectF(roi['bbox'][0], roi['bbox'][1], roi['bbox'][2], roi['bbox'][3])
                    rect = self.graphicsScene.addRect(rect, QtGui.QPen(QtGui.QBrush(QtCore.Qt.yellow, QtCore.Qt.SolidPattern), 3))
                    self.rois.append(rect)

    def displayLabelData(self):
        self.tableWidgetLabels.setRowCount(0)
        self.tableWidgetLabels.blockSignals(True)
        if self.currentFileName in self.data['images']:
            rows = len(self.data['images'][self.currentFileName])
            self.tableWidgetLabels.setRowCount(rows)
            for row in range(rows):
                self.tableWidgetLabels.setItem(row, 0, QtWidgets.QTableWidgetItem(self.data['images'][self.currentFileName][row]['label']))
                self.tableWidgetLabels.setItem(row, 1, QtWidgets.QTableWidgetItem(self.data['images'][self.currentFileName][row]['truncated']))
                self.tableWidgetLabels.setItem(row, 2, QtWidgets.QTableWidgetItem(self.data['images'][self.currentFileName][row]['occluded']))
                self.tableWidgetLabels.setItem(row, 3, QtWidgets.QTableWidgetItem(self.data['images'][self.currentFileName][row]['difficult']))
        # self.tableWidgetLabels.resizeColumnToContents(0)
        self.tableWidgetLabels.blockSignals(False)

    def jumpToImage(self):
        try:
            imageNum = int(self.lineEditCurrentImage.text())
            if imageNum <= len(self.imageList) and imageNum >= 1:
                self.currentImage = imageNum
                self.loadImage()
            else:
                self.lineEditCurrentImage.setText(str(self.currentImage))
        except ValueError:
            self.lineEditCurrentImage.setText(str(self.currentImage))

    def loadFromDirectory(self):
        if self.dataDirty:
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
            self.data['directory'] = self.directory
            self.mask = None
            self.loadImageList()
            self.pushButtonSelectMask.setEnabled(True)

    def loadFromFile(self):
        if self.dataDirty:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setText('Annotations have been modified.')
            msgBox.setInformativeText('Do you want to save your changes?')
            msgBox.setStandardButtons(QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Save)
            response = msgBox.exec()
            if response == QtWidgets.QMessageBox.Save:
                self.save()
        fileName = QtWidgets.QFileDialog.getOpenFileName(self, 'Load Annotations', self.directory, 'Andenet (*.adn)')
        if fileName[0] != '':
            file = open(fileName[0], 'rb')
            self.data = pickle.load(file)
            file.close()
            self.directory = self.data['directory']
            self.mask = self.data['mask']
            self.loadImageList()
            self.setDirty(False)
            self.pushButtonSelectMask.setEnabled(True)

    def loadImageList(self):
        if self.directory != '':
            self.imageList = []
            self.directory += os.path.sep
            files = glob.glob(self.directory + '*')
            imageType = [".jpg", ".jpeg", ".png"]
            for file in files:
                ext = os.path.splitext(file)[1]
                if ext.lower() in imageType:
                    name = os.path.basename(file)
                    self.imageList.append(name)
            self.imageList = sorted(self.imageList)
            self.currentImage = 1
            self.labelImages.setText('of ' + str(len(self.imageList)))
            self.lineEditCurrentImage.setText('1')
            self.loadImage()

    def loadImage(self):
        self.graphicsView.roiSelector.hide()
        self.graphicsScene.clear()
        self.rois = []
        self.selectedRow = -1
        self.currentFileName = self.imageList[self.currentImage - 1]
        file = os.path.join(self.directory, self.currentFileName)
        img = Image.open(file)
        self.currentImageSize = img.size
        if self.mask is not None:
            img = np.array(img) * self.mask
            img = Image.fromarray(img)

        self.qImage = ImageQt.ImageQt(img)
        self.graphicsScene.addPixmap(QtGui.QPixmap.fromImage(self.qImage))
        img.close()
        img = None
        self.graphicsView.fitInView(self.graphicsScene.itemsBoundingRect(), QtCore.Qt.KeepAspectRatio)
        self.graphicsView.setSceneRect(self.graphicsScene.itemsBoundingRect())
        self.displayRois()
        self.displayLabelData()
        self.graphicsView.setFocus()

    def nextAnnotatedImage(self):
        tmpList = sorted(self.data['images'].keys())
        current = self.imageList[self.currentImage - 1]
        if current in tmpList:
            index = tmpList.index(current)
            if index + 1 < len(tmpList):
                self.currentImage = self.imageList.index(tmpList[index + 1]) + 1
        else:
            index = 0
            while(index < len(tmpList) and tmpList[index] < current):
                index += 1
            if index < len(tmpList):
                self.currentImage = self.imageList.index(tmpList[index]) + 1
        self.lineEditCurrentImage.setText(str(self.currentImage))
        self.loadImage()

    def nextImage(self):
        if self.currentImage < len(self.imageList):
            self.currentImage += 1
            self.lineEditCurrentImage.setText(str(self.currentImage))
            self.loadImage()

    def previousAnnotatedImage(self):
        tmpList = sorted(self.data['images'].keys())
        current = self.imageList[self.currentImage - 1]
        if current in tmpList:
            index = tmpList.index(current)
            if index - 1 >= 0:
                self.currentImage = self.imageList.index(tmpList[index - 1]) + 1
        else:
            index = len(tmpList) - 1
            while(index >= 0 and tmpList[index] > current):
                index -= 1
            if index >= 0:
                self.currentImage = self.imageList.index(tmpList[index]) + 1
        self.lineEditCurrentImage.setText(str(self.currentImage))
        self.loadImage()

    def previousImage(self):
        if self.currentImage > 1:
            self.currentImage -= 1
            self.lineEditCurrentImage.setText(str(self.currentImage))
            self.loadImage()

    def resizeEvent(self, theEvent):
        self.graphicsView.fitInView(self.graphicsScene.itemsBoundingRect(), QtCore.Qt.KeepAspectRatio)
        self.displayRois()

    def roiCreated(self, theRect):
        if theRect.width() > 0 and theRect.height() > 0:
            self.setDirty(True)
            if self.currentFileName not in self.data['images']:
                self.data['images'][self.currentFileName] = []
            metadata = self._annotationSchema()
            metadata['bbox'] = [theRect.x(), theRect.y(), theRect.width(), theRect.height()]
            self.data['images'][self.currentFileName].append(metadata)
            self.displayLabelData()
            self.selectedRow = self.tableWidgetLabels.rowCount() - 1
        self.displayRois()
        pos = self.mapToGlobal(self.graphicsView.pos())
        self.assistant.move(pos.x() + (self.graphicsView.width() - self.assistant.width()) / 2, pos.y() + (self.graphicsView.height() - self.assistant.height()) / 2)
        self.assistant.show()

    def rowChanged(self, theModelIndex):
        self.selectedRow = theModelIndex.row()
        self.displayRois()

    def save(self):
        file = QtWidgets.QFileDialog.getSaveFileName(self, 'Save Annotations', self.directory + 'untitled.adn', 'Andenet (*.adn)')
        if file[0] != '':
            self.data['timestamp'] = '{:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now())
            fileObject = open(file[0], 'wb')
            pickle.dump(self.data, fileObject)
            fileObject.close()
            self.setDirty(False)

    def selectMask(self):
        filterStr = str(self.currentImageSize[0]) + '_' + str(self.currentImageSize[1]) + '.png'
        file = QtWidgets.QFileDialog.getOpenFileName(self, 'Select Mask', './masks/', 'PNG (*' + filterStr + ')')
        if file[0] != '':
            img = Image.open(file[0])
            if self.currentImageSize == img.size:
                img = np.array(img)
                img = np.clip(img, 0, 1)
                self.mask = img
                self.data['mask'] = img
                self.data['mask_name'] = os.path.split(file[0])[1]
                self.setDirty(True)
            else:
                print('TODO: Display Message')
                self.mask = None
        self.loadImage()

    def setDirty(self, isDirty):
        if isDirty:
            self.dataDirty = True
            self.pushButtonSave.setEnabled(True)
        else:
            self.dataDirty = False
            self.pushButtonSave.setEnabled(False)

    def updateAnnotation(self, theData):
        for key in theData.keys():
            self.data['images'][self.currentFileName][self.selectedRow][key] = theData[key]
        self.displayLabelData()

    def updateRoi(self, theRect):
        if theRect.width() > 0 and theRect.height() > 0:
            self.setDirty(True)
            self.data['images'][self.currentFileName][self.selectedRow]['bbox'] = [theRect.x(), theRect.y(), theRect.width(), theRect.height()]
