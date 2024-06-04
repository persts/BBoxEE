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
import random
import numpy as np
from shutil import copy2
from PIL import Image
from PyQt6 import QtCore


class Exporter(QtCore.QThread):
    """Export annotated images into the YOLOv9 format."""

    progress = QtCore.pyqtSignal(int)
    exported = QtCore.pyqtSignal(int, int)
    error = QtCore.pyqtSignal(str)

    def __init__(self,
                 directory,
                 images,
                 label_map,
                 validation_split,
                 shards=0,
                 masks={},
                 strip_metadata=False):
        """
        Class init function.

        Args:
            directory (str): Destination directory
            image_data (File): Image and Annotation List
            labels_map (dict): Class/label names
            validation_split (float): Percent to use for validation
            masks (dict): Binary arrays for masking metadata
            strip_metadata (bool): Flag for stripping metadata
        """
        QtCore.QThread.__init__(self)
        self.directory = directory
        self.images = images
        self.label_map = label_map
        self.train_size = int((1.0 - validation_split) * len(self.images))
        self.stop = False

        self.masks = masks
        self.strip_metadata = strip_metadata

        for mask in masks:
            m = np.array(masks[mask], dtype='uint8')
            self.masks[mask] = np.dstack((m, m, m))

        labels = set()
        for label in label_map:
            if label_map[label].lower() != 'exclude' and label.lower() != 'negative':
                if label_map[label] == '':
                    self.label_map[label] = label
                labels.add(self.label_map[label])
        self.labels = list(labels)
        self.labels.sort()

    def run(self):
        """
        The starting point for the thread.

        After creating an instance of the class, calling start() will call
        this function which exports all of the annotaiton examples to disk.
        """
        self.stop = False
        random.shuffle(self.images)

        # Create new directories
        try:
            train = os.path.join(self.directory, 'train')
            os.makedirs(train)
            image_train_path = os.path.join(train, 'images')
            os.makedirs(image_train_path)
            label_train_path = os.path.join(train, 'labels')
            os.makedirs(label_train_path)

            validation = os.path.join(self.directory, 'validation')
            os.makedirs(validation)
            image_val_path = os.path.join(validation, 'images')
            os.makedirs(image_val_path)
            label_val_path = os.path.join(validation, 'labels')
            os.makedirs(label_val_path)
        except FileExistsError:
            self.exported.emit(0, 0)
            self.error.emit('Image and label directory already exists in\n{}'.format(self.directory))
            return None
        except PermissionError:
            self.exported.emit(0, 0)
            self.error.emit('You do not have write permission on \n{}'.format(self.directory))
            return None

        # Create yaml file
        file = open(os.path.join(self.directory, 'dataset.yaml'), 'w')
        file.write("train: {}\n".format(train))
        file.write("val: {}\n".format(validation))
        file.write("nc: {}\n".format(len(self.labels)))
        file.write("names:\n")
        for index, label in enumerate(self.labels):
            file.write(f"  {index}: {label}")
        file.close()

        img_path = os.path.join(image_train_path, 'train_')
        label_path = os.path.join(label_train_path, 'train_')
        count = 0
        for index, rec in enumerate(self.images):
            if self.stop:
                break
            if index == self.train_size:
                img_path = os.path.join(image_val_path, 'val_')
                label_path = os.path.join(label_val_path, 'val_')
                count = 0
            img_file = img_path + '{:010d}.jpg'.format(count)
            label_file = label_path + '{:010d}.txt'.format(count)

            src_file = os.path.join(rec['directory'], rec['file_name'])
            if os.path.exists(src_file):
                if self.strip_metadata:
                    img = Image.open(src_file)
                    array = np.array(img)
                    img.close()
                    if rec['mask_name'] in self.masks:
                        array = array * self.masks[rec['mask_name']]
                    img = Image.fromarray(array)
                    img.save(img_file)
                    img.close()
                else:
                    copy2(src_file, img_file)

                nl = ""
                label_string = ''
                for ann in rec['annotations']:
                    if ann['label'].lower() == 'negative':
                        label_string = ''
                        break
                    bbox = ann['bbox']
                    remap = self.label_map[ann['label']]
                    label = self.labels.index(remap)
                    width = bbox['xmax'] - bbox['xmin']
                    height = bbox['ymax'] - bbox['ymin']
                    x = bbox['xmin'] + (width / 2.0)
                    y = bbox['ymin'] + (height / 2.0)
                    template = "{}{} {} {} {} {}"
                    label_string += template.format(nl, label, x, y, width, height)
                    nl = "\n"

                file = open(label_file, 'w')
                file.write(label_string)
                file.close()
                count += 1
                self.progress.emit(index + 1)

        file = open(os.path.join(self.directory, 'label_remap.json'), 'w')
        json.dump(self.label_map, file, indent=4)
        file.close()
        self.exported.emit(self.train_size, len(self.images) - self.train_size)
