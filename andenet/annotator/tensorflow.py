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
import json
from PIL import Image
from PyQt5 import QtCore
from andenet import schema
import tensorflow as tf
import numpy as np


class Annotator(QtCore.QThread):
    """Threaded worker to keep gui from freezing while annotating images."""

    progress = QtCore.pyqtSignal(int, str, dict)
    finished = QtCore.pyqtSignal(dict)

    def __init__(self, inference_graph, label_map):
        """Class init function."""
        QtCore.QThread.__init__(self)
        self.image_list = []
        self.threshold = 0.9
        self.image_directory = ''
        self.data = None
        self.detection_graph = tf.Graph()
        self.label_map = self.build_label_map(label_map)
        with self.detection_graph.as_default():
            graph_def = self.detection_graph.as_graph_def()
            with tf.io.gfile.GFile(inference_graph, 'rb') as fid:
                serialized_graph = fid.read()
                graph_def.ParseFromString(serialized_graph)
                tf.import_graph_def(graph_def, name='')

    def build_label_map(self, file_name):
        # see if we can use this to eliminated the need for
        # label_map_util dependency
        a = open(file_name, 'r')
        string = a.read()
        a.close()
        string = (string.replace('item ', '').
                  replace('}', '},').
                  replace('\n', '').
                  replace(' name:', '"name":').
                  replace(' id:', ', "id":'))
        string = "[{}]".format(string[0:-1])
        j = json.loads(string)
        label_map = {}
        for entry in j:
            label_map[entry['id']] = entry['name']
        return label_map

    def run(self):
        """The starting point for the thread."""
        self.data = schema.annotation_file()
        counter = 0
        with self.detection_graph.as_default():
            with tf.Session(graph=self.detection_graph) as sess:
                # Definite input and output Tensors for detection_graph
                image_tensor = (self.detection_graph.
                                get_tensor_by_name('image_tensor:0'))
                # Each box represents a part of the image where a
                # particular object was detected.
                d_boxes = (self.detection_graph.
                           get_tensor_by_name('detection_boxes:0'))
                # Each score represent how level of confidence for each of
                # the objects. Score is shown on the result image,
                # together with the class label.
                d_scores = (self.detection_graph.
                            get_tensor_by_name('detection_scores:0'))
                d_classes = (self.detection_graph.
                             get_tensor_by_name('detection_classes:0'))
                num_detections = (self.detection_graph.
                                  get_tensor_by_name('num_detections:0'))
                for img in self.image_list:
                    image = Image.open(self.image_directory + img)
                    # the array based representation of the image will be
                    # used later in order to prepare the result image with
                    # boxes and labels on it.
                    image_np = np.array(image)
                    # Expand dimensions since the model expects images
                    # to have shape: [1, None, None, 3]
                    image_np_expanded = np.expand_dims(image_np, axis=0)
                    # Actual detection.
                    fd = {image_tensor: image_np_expanded}
                    (boxes, scores, classes, num) = sess.run([d_boxes,
                                                              d_scores,
                                                              d_classes,
                                                              num_detections],
                                                             feed_dict=fd)
                    boxes = np.squeeze(boxes)
                    scores = np.squeeze(scores)
                    classes = np.squeeze(classes)
                    entry = schema.annotation_file_entry()
                    for i in range(len(scores)):
                        if scores[i] >= self.threshold:
                            annotation = schema.annotation()
                            annotation['created_by'] = 'machine'
                            bbox = boxes[i]
                            annotation['bbox']['xmin'] = float(bbox[1])
                            annotation['bbox']['xmax'] = float(bbox[3])
                            annotation['bbox']['ymin'] = float(bbox[0])
                            annotation['bbox']['ymax'] = float(bbox[2])
                            if classes[i] in self.label_map:
                                label = self.label_map[classes[i]]
                            else:
                                label = 'unknown'
                            # label = self.category_index[classes[i]]['name']
                            annotation['label'] = label
                            entry['annotations'].append(annotation)
                    if len(entry['annotations']) > 0:
                        self.data['images'][img] = entry
                    image.close()
                    counter += 1
                    self.progress.emit(counter, img, entry)
        self.finished.emit(self.data)
