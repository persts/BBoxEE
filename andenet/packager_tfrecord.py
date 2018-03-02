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
from PIL import Image
from PyQt5 import QtCore
import tensorflow as tf
import numpy as np
from object_detection.utils import dataset_util


class TfrPackager(QtCore.QThread):
    """Package annotated image examples into the Tensorflow TFRecord format."""

    progress = QtCore.pyqtSignal(int)
    packaged = QtCore.pyqtSignal()

    def __init__(self, directory, train_examples, validation_examples, masks, remap):
        """
        Class init function.

        Args:
            directory (str): Destination directory
            train_examples (list): List of all of the annotated examples to be used for trianing
            validation_examples (list): List of all of the annotated examples to be used for validation
            masks (dict): Dictionary holding the masks index by mask name
            remap (dict): A lookup table for renaming classes
        """
        QtCore.QThread.__init__(self)
        self.directory = directory
        self.examples = [train_examples, validation_examples]
        self.masks = masks
        self.remap = remap

    def run(self):
        """
        The starting point for the thread.

        After creating and instance of the class, calling start() will call this
        function which processes and saves all of the annotaiton examples to disk.
        """
        counter = 0
        for examples in self.examples:
            writer = None
            if examples == self.examples[0]:
                writer = tf.python_io.TFRecordWriter(self.directory + os.path.sep + 'training.record')
            else:
                writer = tf.python_io.TFRecordWriter(self.directory + os.path.sep + 'validation.record')
            for example in examples:
                file_name = example['directory'] + os.path.sep + example['file_name']
                img = Image.open(file_name)
                height = img.size[1]
                width = img.size[0]
                # Turn image into an array to remove metadata and apply mask if there is one
                array = np.array(img)
                if example['mask_name'] != '':
                    array = array * self.masks[example['mask_name']]
                # Convert array back into an image and save in memory as a jpeg
                img = Image.fromarray(array)
                jpeg_file = io.BytesIO()
                img.save(jpeg_file, format='JPEG')
                img.close()
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
                    label = self.remap[annotation['label']]
                    if label.lower() != 'exclude':
                        xmins.append(annotation['bbox']['xmin'])
                        ymins.append(annotation['bbox']['ymin'])
                        xmaxs.append(annotation['bbox']['xmax'])
                        ymaxs.append(annotation['bbox']['ymax'])
                        classes_text.append(label.encode('utf8'))
                        classes.append(self.remap['lookup'].index(label) + 1)
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
                    'image/height': dataset_util.int64_feature(height),
                    'image/width': dataset_util.int64_feature(width),
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
                # Check to see if an annotation was excluded and was the only annotation for the file
                if len(xmins) > 0:
                    tf_example = tf.train.Example(features=tf.train.Features(feature=feature_dict))
                    writer.write(tf_example.SerializeToString())
                counter += 1
                self.progress.emit(counter)
            writer.close()
            self.packaged.emit()
        file = open(self.directory + os.path.sep + 'label_map.pbtxt', 'w')
        for counter in range(len(self.remap['lookup'])):
            file.write("item {{\n name: \"{}\"\n id: {}\n}}\n".format(self.remap['lookup'][counter], counter + 1))
        file.close()
