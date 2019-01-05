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
# along with this software.  If not, see <http://www.gnu.org/licenses/>.
#
# --------------------------------------------------------------------------
import os
import io
import hashlib
import numpy as np
import tensorflow as tf
from PIL import Image
from PyQt5 import QtCore
from object_detection.utils import dataset_util


class TfrExporter(QtCore.QThread):
    """Export annotated image examples into the Tensorflow TFRecord format."""

    progress = QtCore.pyqtSignal(int)
    exported = QtCore.pyqtSignal()

    def __init__(self, directory, metadata, image_data, labels, validation_split):
        """
        Class init function.

        Args:
            directory (str): Destination directory
            metadata (dict): List of all of the annotated examples to be used for trianing
            image_data (File): File handler to image data
            split (float): Percent of training data to use for validation
        """
        QtCore.QThread.__init__(self)
        self.directory = directory
        self.metadata = metadata
        self.image_data = image_data
        self.labels = labels
        self.train_size = int((1.0 - validation_split) * len(self.metadata))

    def run(self):
        """
        The starting point for the thread.

        After creating and instance of the class, calling start() will call this
        function which exports all of the annotaiton examples to disk.
        """
        counter = 0
        train_writer = tf.python_io.TFRecordWriter(os.path.join(self.directory, 'training.record'))
        validation_writer = tf.python_io.TFRecordWriter(os.path.join(self.directory, 'validation.record'))
        for example in self.metadata:
            file_name = os.path.join(example['directory'], example['file_name'])
            # Seek to the start of the data block then read in the image data
            self.image_data.seek(example['image_data']['start'])
            raw = self.image_data.read(example['image_data']['size'])
            # Turn into a virtual file stream and load the image as if from disk
            jpeg_file = io.BytesIO(raw)
            encoded_jpg = jpeg_file.getvalue()
            key = hashlib.sha256(encoded_jpg).hexdigest()
            
            xmins = []
            ymins = []
            xmaxs = []
            ymaxs = []
            classes = []
            classes_text = []
            occluded = []
            truncated = []
            difficult = []
            for annotation in example['annotations']:
                label = annotation['label']
                xmins.append(annotation['bbox']['xmin'])
                ymins.append(annotation['bbox']['ymin'])
                xmaxs.append(annotation['bbox']['xmax'])
                ymaxs.append(annotation['bbox']['ymax'])
                classes_text.append(label.encode('utf8'))
                classes.append(self.labels.index(label) + 1)
                if annotation['occluded'] == 'Y':
                    occluded.append(1)
                else:
                    occluded.append(0)

                if annotation['truncated'] == 'Y':
                    truncated.append(1)
                else:
                    truncated.append(0)

                if annotation['difficult'] == 'Y':
                    difficult.append(1)
                else:
                    difficult.append(0)

            feature_dict = {
                'image/height': dataset_util.int64_feature(example['image_data']['height']),
                'image/width': dataset_util.int64_feature(example['image_data']['width']),
                'image/filename': dataset_util.bytes_feature(file_name.encode('utf8')),
                'image/source_id': dataset_util.bytes_feature(file_name.encode('utf8')),
                'image/key/sha256': dataset_util.bytes_feature(key.encode('utf8')),
                'image/encoded': dataset_util.bytes_feature(encoded_jpg),
                'image/format': dataset_util.bytes_feature('jpeg'.encode('utf8')),
                'image/object/bbox/xmin': dataset_util.float_list_feature(xmins),
                'image/object/bbox/xmax': dataset_util.float_list_feature(xmaxs),
                'image/object/bbox/ymin': dataset_util.float_list_feature(ymins),
                'image/object/bbox/ymax': dataset_util.float_list_feature(ymaxs),
                'image/object/class/text': dataset_util.bytes_list_feature(classes_text),
                'image/object/class/label': dataset_util.int64_list_feature(classes),
                'image/object/difficult': dataset_util.int64_list_feature(difficult),
                'image/object/truncated': dataset_util.int64_list_feature(truncated),
                'image/object/occluded': dataset_util.int64_list_feature(occluded),
            }
            tf_example = tf.train.Example(features=tf.train.Features(feature=feature_dict))
            if counter <= self.train_size:
                train_writer.write(tf_example.SerializeToString())
            else:
                validation_writer.write(tf_example.SerializeToString())
            counter += 1
            self.progress.emit(counter)
        train_writer.close()
        validation_writer.close()
        file = open(os.path.join(self.directory, 'label_map.pbtxt'), 'w')
        for counter in range(len(self.labels)):
            file.write("item {{\n name: \"{}\"\n id: {}\n}}\n".format(self.labels[counter], counter + 1))
        file.close()
        self.exported.emit()
        
