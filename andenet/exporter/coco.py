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
import io
import json
from PIL import Image
from PyQt5 import QtCore


class Exporter(QtCore.QThread):
    """Export annotated image into the COCO format."""

    progress = QtCore.pyqtSignal(int)
    exported = QtCore.pyqtSignal()

    def __init__(self, directory, metadata, image_data, labels, validation_split):
        """
        Class init function.

        Args:
            directory (str): Destination directory
            metadata (dict): List of all of the annotated examples to be used for trianing
            image_data (File): File handler to image data
            labels (list): Class/label names
            validation_split (float): Percent of training data to use for validation
        """
        QtCore.QThread.__init__(self)
        self.directory = directory
        self.metadata = metadata
        self.image_data = image_data
        self.labels = labels
        self.train_size = int((1.0 - validation_split) * len(self.metadata))
        self.info = {}

    def run(self):
        """
        The starting point for the thread.

        After creating and instance of the class, calling start() will call this
        function which exports all of the annotaiton examples to disk.
        """
        license_name = ['No License']
        licenses = [{'id': 0, 'name': 'No License', 'url': ''}]

        # Build categories
        categories = [{"id": i, "name": l, "supercategory": "none"} \
            for i, l in enumerate(self.labels)]

        # Create new directories
        image_train_path = os.path.join(self.directory, 'train')
        image_val_path = os.path.join(self.directory, 'validation')
        os.makedirs(image_train_path)
        os.makedirs(image_val_path)

        prefix = 'train_'
        img_path = os.path.join(image_train_path, prefix)
        train = {'info': self.info, 'images': [], 'annotations': [], \
            'licenses': [], 'categories': categories}
        val = {'info': self.info, 'images': [], 'annotations': [], \
            'licenses': [], 'categories': categories}

        current = train
        annotation_count = 0
        for count, rec in enumerate(self.metadata):
            if 'flagged' not in rec or rec['flagged'] == False:
                if count > self.train_size:
                    current = val
                    prefix = 'val_'
                    img_path = os.path.join(image_val_path, prefix)
                img_file = img_path + '{:010d}.jpg'.format(count)
                # Seek to the start of the data block then read in the image data
                self.image_data.seek(rec['image_data']['start'])
                raw = self.image_data.read(rec['image_data']['size'])
                # Turn into a virtual file stream and load the image as if from disk
                stream = io.BytesIO(raw)
                img = Image.open(stream)
                img.save(img_file)
                size = img.size
                img.close()

                # Build license object
                if rec['license'] != '' and rec['license'] not in license_name:
                    licenses.append({'id': len(license_name), \
                        'name': rec['license'], 'url': rec['license_url']})
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
                    annotation['category_id'] = self.labels.index(ann['label'])
                    annotation['segmentation'] = []
                    annotation['area'] = 0.0
                    annotation['bbox'] = [bbox['xmin'] * size[0], bbox['ymin'] * size[1], width, height]
                    annotation['iscrowd'] = 0
                    current['annotations'].append(annotation)

            self.progress.emit(count + 1)
        train['licenses'] = licenses
        val['licenses'] = licenses

        file = open(os.path.join(self.directory, 'training.json'), 'w')
        json.dump(train, file)
        file.close()

        file = open(os.path.join(self.directory, 'validation.json'), 'w')
        json.dump(val, file)
        file.close()
