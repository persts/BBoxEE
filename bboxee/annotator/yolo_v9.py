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
import torch
from PyQt6 import QtCore
from bboxee import schema
from ultralytics import YOLO


class Annotator(QtCore.QThread):
    """Threaded worker to keep gui from freezing while annotating images."""

    progress = QtCore.pyqtSignal(int, str, dict)
    finished = QtCore.pyqtSignal(dict)
    model_loaded = QtCore.pyqtSignal()

    def __init__(self, model_file):
        """Class init function."""
        QtCore.QThread.__init__(self)
        self.stop = False
        self.image_list = []
        self.threshold = 0.95
        self.starting_image = 0
        self.image_directory = ''
        self.data = None
        self.model = None
        self.model_file = model_file
        self.device = 'cpu'
        if torch.cuda.is_available():
            self.device = 'cuda:0'
        try:
            if torch.backends.mps.is_built and torch.backends.mps.is_available():
                self.device = 'mps'
        except AttributeError:
            pass

    def run(self):
        """The starting point for the thread."""
        self.stop = False
        self.data = schema.annotation_file()
        self.data['analysts'].append('Machine Generated')

        if self.model is None:
            self.model = YOLO(self.model_file)

        self.model_loaded.emit()
        for count, image_name in enumerate(self.image_list):
            if count >= self.starting_image:
                if self.stop:
                    break
                file_name = os.path.join(self.image_directory, image_name)
                if os.path.exists(file_name):
                    results = self.model(file_name)
                    boxes = results[0].boxes.cpu()
                    entry = schema.annotation_file_entry()
                    for index, conf in enumerate(boxes.conf):
                        if conf >= self.threshold:
                            annotation = schema.annotation()
                            annotation['created_by'] = 'machine'
                            annotation['bbox']['xmin'] = boxes.xyxyn[index][0]
                            annotation['bbox']['ymin'] = boxes.xyxyn[index][1]
                            annotation['bbox']['xmax'] = boxes.xyxyn[index][2]
                            annotation['bbox']['ymax'] = boxes.xyxyn[index][3]
                            annotation['label'] = self.model.names[int(boxes.cls[index])]
                            annotation['confidence'] = conf
                            entry['annotations'].append(annotation)
                    if len(entry['annotations']) > 0:
                        self.data['images'][image_name] = entry
                    self.progress.emit(count + 1, image_name, entry)
        self.finished.emit(self.data)

    def stop_annotation(self):
        self.stop = True
