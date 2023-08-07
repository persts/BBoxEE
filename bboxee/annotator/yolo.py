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
from PIL import Image
from PyQt6 import QtCore
from bboxee import schema
import numpy as np
import torch
from utils.augmentations import letterbox
from utils.general import non_max_suppression, scale_boxes, xyxy2xywh


class Annotator(QtCore.QThread):
    """Threaded worker to keep gui from freezing while annotating images."""

    progress = QtCore.pyqtSignal(int, str, dict)
    finished = QtCore.pyqtSignal(dict)
    model_loaded = QtCore.pyqtSignal()

    def __init__(self, model_file, image_size, stride):
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
        self.image_size = image_size
        self.stride = stride
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
            checkpoint = torch.load(self.model_file)
            # Patch for older YOLOv5 models
            for m in checkpoint['model'].modules():
                if isinstance(m, torch.nn.Upsample) and not hasattr(m, 'recompute_scale_factor'):
                    m.recompute_scale_factor = None
            self.model = checkpoint['model'].float().fuse().eval().to(self.device)

        self.model_loaded.emit()
        for count, image_name in enumerate(self.image_list):
            if count >= self.starting_image:
                if self.stop:
                    break
                file_name = os.path.join(self.image_directory, image_name)
                if os.path.exists(file_name):
                    image = Image.open(file_name)
                    img_original = np.asarray(image)
                    image.close()
                    # padded resize
                    img = letterbox(img_original, new_shape=self.image_size, stride=self.stride, auto=True)[0]  # JIT requires auto=False
                    img = img.transpose((2, 0, 1))  # HWC to CHW; PIL Image is RGB already
                    img = np.ascontiguousarray(img)
                    img = torch.from_numpy(img)
                    img = img.float()
                    img /= 255
                    img = torch.unsqueeze(img, 0).to(self.device)
                    pred: list = self.model(img)[0]
                    pred = non_max_suppression(prediction=pred.cpu(), conf_thres=self.threshold)
                    gn = torch.tensor(img_original.shape)[[1, 0, 1, 0]]  # normalization gain whwh

                    entry = schema.annotation_file_entry()
                    for det in pred:
                        if len(det):
                            # Rescale boxes
                            det[:, :4] = scale_boxes(img.shape[2:], det[:, :4], img_original.shape).round()
                            for *box, conf, cls in reversed(det):
                                annotation = schema.annotation()
                                annotation['created_by'] = 'machine'
                                # normalized center-x, center-y, width and height
                                bbox = (xyxy2xywh(torch.tensor(box).view(1, 4)) / gn).view(-1).tolist()
                                x_center, y_center, width_of_box, height_of_box = bbox
                                x_min = x_center - width_of_box / 2.0
                                y_min = y_center - height_of_box / 2.0
                                x_max = x_center + width_of_box / 2.0
                                y_max = y_center + height_of_box / 2.0
                                annotation['bbox']['xmin'] = x_min
                                annotation['bbox']['xmax'] = x_max
                                annotation['bbox']['ymin'] = y_min
                                annotation['bbox']['ymax'] = y_max
                                annotation['label'] = self.model.names[int(cls.item())]
                                annotation['confidence'] = conf.item()
                                entry['annotations'].append(annotation)
                    if len(entry['annotations']) > 0:
                        self.data['images'][image_name] = entry
                    self.progress.emit(count + 1, image_name, entry)
        self.finished.emit(self.data)

    def stop_annotation(self):
        self.stop = True
