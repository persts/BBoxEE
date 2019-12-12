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
import random
import numpy as np
from shutil import copyfile
from PIL import Image
from PyQt5 import QtCore


class Exporter(QtCore.QThread):
    """Export annotated images into the Darknet yolov3 format."""

    progress = QtCore.pyqtSignal(int)
    exported = QtCore.pyqtSignal()

    def __init__(self,
                 directory,
                 images,
                 label_map,
                 validation_split,
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

        self.masks = masks
        self.strip_metadata = strip_metadata

        for mask in masks:
            m = np.array(masks[mask], dtype='uint8')
            self.masks[mask] = np.dstack((m, m, m))

        self.labels = []
        for label in label_map:
            if label_map[label].lower() != 'exclude':
                if label_map[label] == '':
                    label_map[label] = label
                self.labels.append(label_map[label])

    def run(self):
        """
        The starting point for the thread.

        After creating and instance of the class, calling start() will call
        this function which exports all of the annotaiton examples to disk.
        """
        random.shuffle(self.images)

        # Create new directories
        cfg_path = os.path.join(self.directory, 'cfg')
        os.makedirs(cfg_path)

        image_path = os.path.join(self.directory, 'images')
        os.makedirs(image_path)
        image_train_path = os.path.join(image_path, 'train')
        image_val_path = os.path.join(image_path, 'valiation')
        os.makedirs(image_train_path)
        os.makedirs(image_val_path)

        label_path = os.path.join(self.directory, 'labels')
        os.makedirs(label_path)
        label_train_path = os.path.join(label_path, 'train')
        label_val_path = os.path.join(label_path, 'valiation')
        os.makedirs(label_train_path)
        os.makedirs(label_val_path)

        img_path = os.path.join(image_train_path, 'train_')
        label_path = os.path.join(label_train_path, 'train_')
        train = []
        val = []
        current = train
        for count, rec in enumerate(self.images):
            if count > self.train_size:
                img_path = os.path.join(image_val_path, 'val_')
                label_path = os.path.join(label_val_path, 'val_')
                current = val
            img_file = img_path + '{:010d}.jpg'.format(count)
            label_file = label_path + '{:010d}.txt'.format(count)
            current.append(img_file)

            src_file = os.path.join(rec['directory'], rec['file_name'])
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
                copyfile(src_file, img_file)

            file = open(label_file, 'w')
            nl = ""
            for a in rec['annotations']:
                bbox = a['bbox']
                remap = self.label_map[a['label']]
                label = self.labels.index(remap)
                width = bbox['xmax'] - bbox['xmin']
                height = bbox['ymax'] - bbox['ymin']
                x = bbox['xmin'] + (width / 2.0)
                y = bbox['ymin'] + (height / 2.0)
                template = "{}{} {} {} {} {}"
                file.write(template.format(nl, label, x, y, width, height))
                nl = "\n"
            file.close()

            # TODO: Really need to export the license information for each file

            self.progress.emit(count + 1)

        nl = ""
        file = open(os.path.join(self.directory, 'names.txt'), 'w')
        for label in self.labels:
            file.write('{}{}'.format(nl, label))
            nl = "\n"
        file.close()

        nl = ""
        file = open(os.path.join(self.directory, 'train.txt'), 'w')
        for file_name in train:
            file.write('{}{}'.format(nl, file_name))
            nl = "\n"
        file.close()

        nl = ""
        file = open(os.path.join(self.directory, 'val.txt'), 'w')
        for file_name in val:
            file.write('{}{}'.format(nl, file_name))
            nl = "\n"
        file.close()

        file = open(os.path.join(cfg_path, 'andenet.data'), 'w')
        file.write('classes={}\n'.format(len(self.labels)))
        file_name = os.path.join(self.directory, 'train.txt')
        file.write('train={}\n'.format(file_name))
        file_name = os.path.join(self.directory, 'val.txt')
        file.write('valid={}\n'.format(file_name))
        file_name = os.path.join(self.directory, 'names.txt')
        file.write('names={}\n'.format(file_name))
        file.write('backup=backup/\n')
        file.write('eval=coco\n')
        file.close()
        self.exported.emit()
