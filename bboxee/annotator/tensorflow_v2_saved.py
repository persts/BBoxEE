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
import json
from PIL import Image
from PyQt5 import QtCore
from bboxee import schema
import tensorflow as tf
import numpy as np


class Annotator(QtCore.QThread):
    """Threaded worker to keep gui from freezing while annotating images."""

    progress = QtCore.pyqtSignal(int, str, dict)
    finished = QtCore.pyqtSignal(dict)

    def __init__(self, model_dir, label_map):
        """Class init function."""
        QtCore.QThread.__init__(self)
        self.stop = False
        self.image_list = []
        self.threshold = 0.95
        self.image_directory = ''
        self.data = None
        self.model_dir = model_dir
        self.label_map = self.build_label_map(label_map)

    def build_label_map(self, file_name):
        # see if we can use this to eliminated the need for
        # label_map_util dependency
        a = open(file_name, 'r')
        string = a.read()
        a.close()
        lines = string.split("\n")
        parsed = ''
        comma = ''
        for line in lines:
            if line == '':
                pass
            elif line.find('item') != -1:
                parsed += '{'
            elif line.find('}') != -1:
                comma = ''
                parsed += '},'
            else:
                parts = line.replace('\\', '').replace('\'', '"').split(':')
                parsed += '{} "{}":{}'.format(comma, parts[0].lstrip(), parts[1])
                comma = ','

        string = "[{}]".format(parsed[0:-1])
        j = json.loads(string)
        label_map = {}
        for entry in j:
            if 'display_name' in entry:
                label_map[entry['id']] = entry['display_name']
            else:
                label_map[entry['id']] = entry['name']
        return label_map

    def run(self):
        """The starting point for the thread."""
        self.stop = False
        self.data = schema.annotation_file()
        self.data['analysts'].append('Machine Generated')
        model = tf.saved_model.load(self.model_dir)
        counter = 0
        for img in self.image_list:
            if self.stop:
                break
            file_name = os.path.join(self.image_directory, img)
            image = Image.open(file_name)
            # the array based representation of the image will be
            # used later in order to prepare the result image with
            # boxes and labels on it.
            image_np = np.array(image)
            # Expand dimensions since the model expects images
            # to have shape: [1, None, None, 3]
            image_np_expanded = np.expand_dims(image_np, axis=0)
            # Actual detection.
            dets = model(image_np_expanded)
            entry = schema.annotation_file_entry()
            scores = dets['detection_scores'][0].numpy()
            boxes = dets['detection_boxes'][0].numpy()
            classes = dets['detection_classes'][0].numpy()
            for index, score in enumerate(scores):
                if score >= self.threshold:
                    annotation = schema.annotation()
                    annotation['created_by'] = 'machine'
                    annotation['confidence'] = float(score)
                    bbox = boxes[index]
                    annotation['bbox']['xmin'] = float(bbox[1])
                    annotation['bbox']['xmax'] = float(bbox[3])
                    annotation['bbox']['ymin'] = float(bbox[0])
                    annotation['bbox']['ymax'] = float(bbox[2])
                    class_number = int(classes[index])
                    if class_number in self.label_map:
                        label = self.label_map[class_number]
                    else:
                        label = 'unknown'
                    annotation['label'] = label
                    entry['annotations'].append(annotation)
            if len(entry['annotations']) > 0:
                self.data['images'][img] = entry
            image.close()
            counter += 1
            self.progress.emit(counter, img, entry)
        self.finished.emit(self.data)

    def stop_annotation(self):
        self.stop = True
