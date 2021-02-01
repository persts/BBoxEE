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
import datetime
import numpy as np
from shutil import copyfile
from PIL import Image
from PyQt5 import QtCore


class Exporter(QtCore.QThread):
    """Export annotated image into the COCO format."""

    progress = QtCore.pyqtSignal(int)
    exported = QtCore.pyqtSignal()

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
        self.info = {}
        self.directory = directory
        self.images = images
        self.label_map = label_map
        self.train_size = int((1.0 - validation_split) * len(self.images))

        self.masks = masks
        self.strip_metadata = strip_metadata

        for mask in masks:
            m = np.array(masks[mask], dtype='uint8')
            self.masks[mask] = np.dstack((m, m, m))

        # TODO: How handle negative images in COCO
        labels = set()
        for label in label_map:
            if label_map[label].lower() != 'exclude':
                if label_map[label] == '':
                    self.label_map[label] = label
                labels.add(self.label_map[label])
        self.labels = list(labels)
        self.labels.sort()

    def run(self):
        """
        The starting point for the thread.

        After creating and instance of the class, calling start() will call
        this function which exports all of the annotaiton examples to disk.
        """
        random.shuffle(self.images)

        license_name = ['No License']
        licenses = [{'id': 0, 'name': 'No License', 'url': ''}]

        # Build categories
        categories = [{"id": i,
                       "name": l,
                       "supercategory": "none"} for i, l in enumerate(
                           self.labels)]

        # Create new directories
        image_train_path = os.path.join(self.directory, 'train')
        image_val_path = os.path.join(self.directory, 'validation')
        os.makedirs(image_train_path)
        os.makedirs(image_val_path)

        prefix = 'train_'
        img_path = os.path.join(image_train_path, prefix)
        train = {'info': self.info,
                 'images': [],
                 'annotations': [],
                 'licenses': [],
                 'categories': categories}
        val = {'info': self.info,
               'images': [],
               'annotations': [],
               'licenses': [],
               'categories': categories}

        current = train
        annotation_count = 0
        for count, rec in enumerate(self.images):
            if count > self.train_size:
                current = val
                prefix = 'val_'
                img_path = os.path.join(image_val_path, prefix)
            img_file = img_path + '{:010d}.jpg'.format(count)

            src_file = os.path.join(rec['directory'], rec['file_name'])
            timestamp = os.path.getctime(src_file)
            timestamp = datetime.datetime.fromtimestamp(timestamp)
            rec['date_captured'] = str(timestamp)
            img = Image.open(src_file)
            size = img.size  # PIL (width, height)
            if self.strip_metadata:
                array = np.array(img)
                img.close()
                if rec['mask_name'] in self.masks:
                    array = array * self.masks[rec['mask_name']]
                img = Image.fromarray(array)
                img.save(img_file)
                img.close()
            else:
                img.close()
                copyfile(src_file, img_file)

            # Build license object
            if rec['license'] != '' and rec['license'] not in license_name:
                licenses.append({'id': len(license_name),
                                 'name': rec['license'],
                                 'url': rec['license_url']})
                license_name.append(rec['license'])
            if rec['license'] == '':
                license_num = 0
            else:
                license_num = license_name.index(rec['license'])

            # Store image entry
            image_rec = {}
            image_rec['id'] = count
            image_rec['width'] = size[0]
            image_rec['height'] = size[1]
            image_rec['file_name'] = prefix + '{:010d}.jpg'.format(count)
            image_rec['license'] = license_num
            image_rec['attribution'] = rec['attribution']
            image_rec['flickr_url'] = ''
            image_rec['coco_url'] = ''
            image_rec['date_captured'] = rec['date_captured']
            current['images'].append(image_rec)

            for ann in rec['annotations']:
                annotation_count += 1
                bbox = ann['bbox']
                width = (bbox['xmax'] - bbox['xmin']) * size[0]
                height = (bbox['ymax'] - bbox['ymin']) * size[1]
                annotation = {}
                annotation['id'] = annotation_count
                annotation['image_id'] = count
                remap = self.label_map[ann['label']]
                annotation['category_id'] = self.labels.index(remap)
                annotation['segmentation'] = []
                annotation['area'] = 0.0
                x = bbox['xmin'] * size[0]
                y = bbox['ymin'] * size[1]
                annotation['bbox'] = [x, y, width, height]
                annotation['iscrowd'] = 0
                current['annotations'].append(annotation)

            self.progress.emit(count + 1)
        train['licenses'] = licenses
        val['licenses'] = licenses

        file = open(os.path.join(self.directory, 'train.json'), 'w')
        json.dump(train, file, indent=4)
        file.close()

        file = open(os.path.join(self.directory, 'validation.json'), 'w')
        json.dump(val, file, indent=4)
        file.close()
        self.exported.emit()
