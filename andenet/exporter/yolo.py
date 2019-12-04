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
from PIL import Image
from PyQt5 import QtCore


class Exporter(QtCore.QThread):
    """Export annotated images into the Darknet yolov3 format."""

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

    def run(self):
        """
        The starting point for the thread.

        After creating and instance of the class, calling start() will call this
        function which exports all of the annotaiton examples to disk.
        """
        # Create new directories
        cfg_path  = os.path.join(self.directory, 'cfg')
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
        for count, rec in enumerate(self.metadata):
            if 'flagged' not in rec or rec['flagged'] == False:
                if count > self.train_size:
                    img_path = os.path.join(image_val_path, 'val_')
                    label_path = os.path.join(label_val_path, 'val_')
                    current = val
                img_file = img_path + '{:010d}.jpg'.format(count)
                label_file = label_path + '{:010d}.txt'.format(count)
                current.append(img_file)
                # Seek to the start of the data block then read in the image data
                self.image_data.seek(rec['image_data']['start'])
                raw = self.image_data.read(rec['image_data']['size'])
                # Turn into a virtual file stream and load the image as if from disk
                stream = io.BytesIO(raw)
                img = Image.open(stream)
                img.save(img_file)
                img.close()
                
                file = open(label_file, 'w')
                nl = ""
                for a in rec['annotations']:
                    bbox = a['bbox']
                    label = self.labels.index(a['label'])
                    width = bbox['xmax'] - bbox['xmin']
                    height = bbox['ymax'] - bbox['ymin']
                    x = bbox['xmin'] + (width / 2.0)
                    y = bbox['ymin'] + (height / 2.0)
                    file.write("{}{} {} {} {} {}".format(nl, label, x, y, width, height))
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
        file.write('train={}\n'.format(os.path.join(self.directory, 'train.txt')))
        file.write('valid={}\n'.format(os.path.join(self.directory, 'val.txt')))
        file.write('names={}\n'.format(os.path.join(self.directory, 'names.txt')))
        file.write('backup=backup/\n')
        file.write('eval=coco\n')
        file.close()
