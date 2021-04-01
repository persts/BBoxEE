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
from tabulate import tabulate
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from bboxee.gui import SelectModelDialog
from functools import reduce

if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
else:
    bundle_dir = os.path.dirname(__file__)
WIDGET, _ = uic.loadUiType(os.path.join(bundle_dir, 'accuracy_widget.ui'))


class AccuracyWidget(QtWidgets.QWidget, WIDGET):
    """Widget for assessing model accuracy."""

    def __init__(self, icon_size=24, parent=None):
        """Class init function."""
        QtWidgets.QWidget.__init__(self, parent)
        self.setupUi(self)

        self.directory = '.'
        self.bbx_file = ''
        self.image_list = []
        self.reference_data = {}
        self.labels = []
        self.annotator = None
        self.label_map = None

        self.pb_select_bbx.clicked.connect(self.load_from_file)
        self.pb_select_model.clicked.connect(self.select_model)
        self.pb_run.clicked.connect(self.annotate)
        self.pb_cancel.clicked.connect(self.cancel)
        self.tw_results.selectionModel().selectionChanged.connect(self.selection_changed)
        self.cb_remap_labels.stateChanged.connect(self.load_label_map)

        self.annotator = None
        self.model_selector = SelectModelDialog(self)
        self.model_selector.selected.connect(self.model_selected)

        self.scene = QtWidgets.QGraphicsScene()
        self.gv_display.setScene(self.scene)

        self.tw_results.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tw_results.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tw_results.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)

        self.tb_summary.setFontFamily("monospace")

    @staticmethod
    def IoU(a, b):
        xmin = max(a['bbox']['xmin'], b['bbox']['xmin'])
        ymin = max(a['bbox']['ymin'], b['bbox']['ymin'])
        xmax = min(a['bbox']['xmax'], b['bbox']['xmax'])
        ymax = min(a['bbox']['ymax'], b['bbox']['ymax'])

        intersection_area = max(xmax - xmin, 0) * max(ymax - ymin, 0)
        a_area = (a['bbox']['xmax'] - a['bbox']['xmin']) * (a['bbox']['ymax'] - a['bbox']['ymin'])
        b_area = (b['bbox']['xmax'] - b['bbox']['xmin']) * (b['bbox']['ymax'] - b['bbox']['ymin'])

        return intersection_area / (a_area + b_area - intersection_area)

    @staticmethod
    def find_matchs(matrix):
        # Prepare the prediction -> truth bbox match list
        pred_truth = [-1] * matrix.shape[0]
        for i in range(len(pred_truth)):
            # Get the index of the max IoU
            index = np.argmax(matrix[i])
            if matrix[i, index] > 0.0:
                try:
                    # See if Truth bbox index is already in list
                    pti = pred_truth.index(index)
                    # If it is get the IoU value
                    iou = matrix[pti, index]
                    # If the first Truth bbox IoU is less swap
                    # it out with the current, i.e, the better match
                    if iou < matrix[i, index]:
                        pred_truth[pti] = -1
                        pred_truth[i] = index
                except ValueError:
                    # Truth bbox was not already in list to add it
                    pred_truth[i] = index

        # Prepare the truth -> prediction bbox match list
        thruth_pred = [-1] * matrix.shape[1]
        for i in range(len(thruth_pred)):
            index = np.argmax(matrix[:, i])
            if matrix[index, i] > 0.0:
                try:
                    tpi = thruth_pred.index(index)
                    iou = matrix[index, tpi]
                    if iou < matrix[index, i]:
                        thruth_pred[tpi] = -1
                        thruth_pred[i] = index
                except ValueError:
                    thruth_pred[i] = index

        return pred_truth, thruth_pred

    def annotate(self):
        """(SLOT) Start the automated annotator."""
        self.scene.clear()
        self.tw_results.setRowCount(0)
        self.tb_summary.clear()

        self.annotator.threshold = self.dsb_threshold.value()
        self.annotator.image_directory = self.directory

        if self.cb_annotated_only.isChecked():
            image_list = [x for x in self.reference_data['images']]
            image_list = sorted(image_list)
        else:
            files = glob.glob(os.path.join(self.directory, '*'))
            image_format = [".jpg", ".jpeg", ".png"]
            f = (lambda x: os.path.splitext(x)[1].lower() in image_format)
            image_list = list(filter(f, files))
            image_list = [os.path.basename(x) for x in image_list]
            image_list = sorted(image_list)

        self.annotator.image_list = image_list
        self.image_list = image_list

        self.progress_bar.setFormat("Loading Model...")
        self.progress_bar.setRange(0, len(image_list))
        self.progress_bar.setValue(0)

        self.dsb_threshold.setDisabled(True)
        self.pb_run.setDisabled(True)
        self.pb_select_bbx.setDisabled(True)
        self.pb_select_model.setDisabled(True)
        self.annotator.start()

    def annotation_complete(self, predicted_data):
        """(SLOT) Automatic annotation complete, reenable gui, generate report"""
        self.pb_run.setEnabled(True)
        self.pb_select_bbx.setEnabled(True)
        self.pb_select_model.setEnabled(True)
        self.dsb_threshold.setEnabled(True)

        summary = self.summarize(predicted_data, self.reference_data)
        self.report(summary)

        self.tw_results.setRowCount(len(summary.keys()))
        for row, image in enumerate(summary):
            rec = summary[image]
            item = QtWidgets.QTableWidgetItem(image)
            self.tw_results.setItem(row, 0, item)

            item = QtWidgets.QTableWidgetItem(str(len(rec['predicted'])))
            item.setTextAlignment(QtCore.Qt.AlignHCenter)
            self.tw_results.setItem(row, 1, item)

            text = ''
            if len(rec['IoUs']) > 0:
                text = '{:0.4f}'.format(np.average(rec['IoUs']))
            item = QtWidgets.QTableWidgetItem(text)
            item.setTextAlignment(QtCore.Qt.AlignHCenter)
            self.tw_results.setItem(row, 2, item)

            text = str(rec['false_positive'])
            item = QtWidgets.QTableWidgetItem(text)
            item.setTextAlignment(QtCore.Qt.AlignHCenter)
            self.tw_results.setItem(row, 3, item)

            text = str(rec['false_negative'])
            item = QtWidgets.QTableWidgetItem(text)
            item.setTextAlignment(QtCore.Qt.AlignHCenter)
            self.tw_results.setItem(row, 4, item)
        self.summary = summary
        self.tw_results.selectRow(0)

    def annotation_progress(self, progress, image, annotations):
        """(SLOT) Show progress and current detections (annotations) as
        they are processed."""
        self.progress_bar.setValue(progress)

    def annotation_started(self):
        self.progress_bar.setFormat("%p%")

    def cancel(self):
        if self.annotator is not None:
            self.annotator.stop = True

    def load_from_file(self):
        """(Slot) Load existing annotation data from file."""
        file_name = QtWidgets.QFileDialog.getOpenFileName(self, 'Load Annotations', self.directory, 'BBoxEE (*.bbx)')
        if file_name[0] != '':
            file = open(file_name[0], 'r')
            self.reference_data = json.load(file)
            file.close()
            self.directory = os.path.split(file_name[0])[0]
            self.pb_select_model.setEnabled(True)

    def load_label_map(self):
        if self.cb_remap_labels.isChecked():
            file_name = (QtWidgets.QFileDialog.getOpenFileName(self, 'Load Remap File', self.directory, 'JSON (*.json)'))
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
                    msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
                    msg_box.exec()
                except PermissionError:
                    msg_box = QtWidgets.QMessageBox()
                    msg_box.setWindowTitle('Label Map')
                    msg_box.setText('{}'.format(file_name))
                    msg_box.setInformativeText(
                        'You do not have permission to read this file.')
                    msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
                    msg_box.exec()
        else:
            self.label_map = None

    def model_selected(self, annotator):
        """ (SLOT) save and hook up annotator."""
        self.annotator = annotator
        self.annotator.progress.connect(self.annotation_progress)
        self.annotator.finished.connect(self.annotation_complete)
        self.annotator.model_loaded.connect(self.annotation_started)
        self.pb_run.setEnabled(True)

    def report(self, summary):
        false_positive_labels = []
        false_negative_labels = []
        confusion_matrix = []
        for label in self.labels:
            false_positive_labels.append([label, 0])
            false_negative_labels.append([label, 0])
            confusion_matrix.append([0 for x in range(len(self.labels))])

        false_positives = 0
        false_negatives = 0
        total_matches = 0
        IoUs = []
        total_bounding_boxes = 0
        for image in summary:
            rec = summary[image]
            total_bounding_boxes += len(rec['reference'])
            IoUs += rec['IoUs']
            for label in rec['false_positive_labels']:
                index = self.labels.index(label)
                false_positive_labels[index][1] += 1
            for label in rec['false_negative_labels']:
                index = self.labels.index(label)
                false_negative_labels[index][1] += 1
            for p, r in rec['labels']:
                pi = self.labels.index(p)
                ri = self.labels.index(r)
                confusion_matrix[pi][ri] += 1
                total_matches += 1
            false_positives += rec['false_positive']
            false_negatives += rec['false_negative']

        correct = 0
        for i in range(len(self.labels)):
            correct += confusion_matrix[i][i]
        if total_matches == 0:
            accuracy = 0.0
        else:
            accuracy = correct / total_matches

        if len(IoUs) == 0:
            average_iou = 0
        else:
            average_iou = np.average(IoUs)

        for index, label in enumerate(self.labels):
            confusion_matrix[index] = [label] + confusion_matrix[index]

        self.tb_summary.append('Confusion Matrix:')
        self.tb_summary.append(tabulate(confusion_matrix, self.labels))
        self.tb_summary.append('--------------------------------------------')
        self.tb_summary.append('Accuracy: {:0.6f}'.format(accuracy))
        self.tb_summary.append('Confidence threshold: {:0.2f}'.format(self.dsb_threshold.value()))
        self.tb_summary.append('Total matching bounding boxes: {}'.format(total_matches))
        self.tb_summary.append('Average IoU: {:0.6f}'.format(average_iou))
        self.tb_summary.append('')
        self.tb_summary.append('')
        self.tb_summary.append('False Positive [ {} ]'.format(false_positives))
        self.tb_summary.append(tabulate(false_positive_labels, ['Label', 'Count']))
        self.tb_summary.append('')
        self.tb_summary.append('')
        self.tb_summary.append('False Negative [ {} ]'.format(false_negatives))
        self.tb_summary.append(tabulate(false_negative_labels, ['Label', 'Count']))

    def remap_label(self, label):
        if self.label_map is not None and label in self.label_map:
            return self.label_map[label]
        return label

    def save_label(self, label):
        if label not in self.labels:
            self.labels.append(label)

    def select_model(self):
        self.model_selector.show()

    def selection_changed(self, selected):
        if len(selected.indexes()) > 0:
            self.scene.clear()
            row = selected.indexes()[0].row()
            name = self.tw_results.item(row, 0).text()
            file_name = os.path.join(self.directory, name)
            img = Image.open(file_name)
            image = np.array(img)
            h, w, c = image.shape
            bpl = int(image.nbytes / h)
            if c == 4:
                qt_image = QtGui.QImage(image.data, w, h, QtGui.QImage.Format_RGBA8888)
            else:
                qt_image = QtGui.QImage(image.data, w, h, bpl, QtGui.QImage.Format_RGB888)
            self.scene.addPixmap(QtGui.QPixmap.fromImage(qt_image))
            bounding_rect = self.scene.itemsBoundingRect()
            self.gv_display.fitInView(bounding_rect, QtCore.Qt.KeepAspectRatio)

            brush = QtGui.QBrush(QtCore.Qt.yellow, QtCore.Qt.SolidPattern)
            pen = QtGui.QPen(brush, 2)

            for ann in self.summary[name]['reference']:
                bbox = ann['bbox']
                x = bbox['xmin'] * w
                y = bbox['ymin'] * h
                top_left = QtCore.QPointF(x, y)
                x = bbox['xmax'] * w
                y = bbox['ymax'] * h
                bottom_right = QtCore.QPointF(x, y)
                rect = QtCore.QRectF(top_left, bottom_right)
                self.scene.addRect(rect, pen)

            brush = QtGui.QBrush(QtCore.Qt.magenta, QtCore.Qt.SolidPattern)
            pen = QtGui.QPen(brush, 2)

            for ann in self.summary[name]['predicted']:
                bbox = ann['bbox']
                x = bbox['xmin'] * w
                y = bbox['ymin'] * h
                top_left = QtCore.QPointF(x, y)
                x = bbox['xmax'] * w
                y = bbox['ymax'] * h
                bottom_right = QtCore.QPointF(x, y)
                rect = QtCore.QRectF(top_left, bottom_right)
                self.scene.addRect(rect, pen)

    def summarize(self, predicted, reference):
        summary = {}

        for image in self.image_list:
            summary[image] = {
                'reference': [],
                'predicted': [],
                'IoUs': [],
                'labels': [],
                'false_positive': 0,
                'false_negative': 0,
                'false_positive_labels': [],
                'false_negative_labels': []
            }
            IoUs = []
            labels = []
            false_positive = 0
            false_negative = 0
            false_positive_labels = []
            false_negative_labels = []
            if image not in predicted['images']:
                if image in reference['images']:
                    negative = False
                    # Check the special negative label
                    for a in reference['images'][image]['annotations']:
                        if a['label'].lower() == 'negative':
                            negative = True
                    if not negative:
                        false_negative = len(reference['images'][image]['annotations'])
                        summary[image]['reference'] = reference['images'][image]['annotations']
                        for a in reference['images'][image]['annotations']:
                            label = self.remap_label(a['label'])
                            false_negative_labels.append(label)
                            self.save_label(label)
            elif image not in reference['images']:
                if image in predicted['images']:
                    false_positive = len(predicted['images'][image]['annotations'])
                    summary[image]['predicted'] = predicted['images'][image]['annotations']
                    for a in predicted['images'][image]['annotations']:
                        label = self.remap_label(a['label'])
                        false_positive_labels.append(a['label'])
                        self.save_label(label)
            else:
                pred = predicted['images'][image]['annotations']
                ref = reference['images'][image]['annotations']
                summary[image]['predicted'] = pred
                summary[image]['reference'] = ref

                matrix = np.zeros((len(pred), len(ref)))
                for pi, p in enumerate(pred):
                    for ri, r in enumerate(ref):
                        matrix[pi, ri] = AccuracyWidget.IoU(p, r)

                p_to_r, r_to_p = AccuracyWidget.find_matchs(matrix)

                IoUs = []
                for pi, p in enumerate(p_to_r):
                    if p != -1:
                        pl = self.remap_label(pred[pi]['label'])
                        rl = self.remap_label(ref[p]['label'])
                        labels.append((pl, rl))
                        self.save_label(pl)
                        self.save_label(rl)
                        IoUs.append(AccuracyWidget.IoU(pred[pi], ref[p]))
                    else:
                        label = self.remap_label(pred[pi]['label'])
                        false_positive_labels.append(label)
                        self.save_label(label)
                for ri, r in enumerate(r_to_p):
                    if r == -1:
                        label = self.remap_label(ref[ri]['label'])
                        false_negative_labels.append(label)
                        self.save_label(label)
                false_positive = reduce(lambda x, y: x + 1 if (y == -1) else x, p_to_r, 0)
                false_negative = reduce(lambda x, y: x + 1 if (y == -1) else x, r_to_p, 0)

            summary[image]['IoUs'] = IoUs
            summary[image]['labels'] = labels
            summary[image]['false_positive'] = false_positive
            summary[image]['false_negative'] = false_negative
            summary[image]['false_positive_labels'] = false_positive_labels
            summary[image]['false_negative_labels'] = false_negative_labels
        self.labels.sort()
        return summary
