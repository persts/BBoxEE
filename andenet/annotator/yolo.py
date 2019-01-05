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
import torch
import cv2
from PyQt5 import QtCore
from andenet import schema

from models import Darknet
from utils.parse_config import parse_data_config
from utils.utils import load_classes, non_max_suppression
from utils.datasets import load_images

class Annotator(QtCore.QThread):
    """Threaded worker to keep gui from freezing while annotating images."""

    progress = QtCore.pyqtSignal(int, str, dict)
    finished = QtCore.pyqtSignal(dict)

    def __init__(self, data_config, net_config, weights, image_size):
        """Class init function."""
        QtCore.QThread.__init__(self)
        self.image_list = []
        self.threshold = 0.9
        self.image_directory = ''
        self.data = None
        self.image_size = image_size

        self.device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
        self.data_config = parse_data_config(data_config)
        self.classes = load_classes(self.data_config['names'])  # Extracts class labels from file
        self.model = Darknet(net_config, image_size)

        checkpoint = torch.load(weights, map_location='cpu')
        self.model.load_state_dict(checkpoint['model'])

    def scale_detections(self, image, detections):
        img = cv2.imread(image)
        # The amount of padding that was added
        pad_x = max(img.shape[0] - img.shape[1], 0) * (self.image_size / max(img.shape))
        pad_y = max(img.shape[1] - img.shape[0], 0) * (self.image_size / max(img.shape))
        # Image height and width after padding is removed
        unpad_h = self.image_size - pad_y
        unpad_w = self.image_size - pad_x

        entry = schema.annotation_file_entry()
        for x1, y1, x2, y2, conf, cls_conf, cls_pred in detections:
            annotation = schema.annotation()
            annotation['created_by'] = 'machine'
            # Rescale coordinates to original dimensions
            box_h = ((y2 - y1) / unpad_h) * img.shape[0]
            box_w = ((x2 - x1) / unpad_w) * img.shape[1]
            y1 = (((y1 - pad_y // 2) / unpad_h) * img.shape[0]).round().item()
            x1 = (((x1 - pad_x // 2) / unpad_w) * img.shape[1]).round().item()
            x2 = (x1 + box_w).round().item()
            y2 = (y1 + box_h).round().item()
            x1, y1, x2, y2 = max(x1, 0), max(y1, 0), max(x2, 0), max(y2, 0)
            annotation['bbox']['xmin'] = x1 / img.shape[1]
            annotation['bbox']['xmax'] = x2 / img.shape[1]
            annotation['bbox']['ymin'] = y1 / img.shape[0]
            annotation['bbox']['ymax'] = y2 / img.shape[0]
            annotation['label'] = self.classes[int(cls_pred.item())]
            entry['annotations'].append(annotation)
        return entry

    def run(self):
        """The starting point for the thread."""
        conf_thres = 0.3
        nms_thres = 0.45
        self.data = schema.annotation_file()
        self.model.to(self.device).eval()
        dataloader = load_images(self.image_directory, batch_size=1, img_size=self.image_size)
        for count, (img_path, img) in enumerate(dataloader):
            with torch.no_grad():
                image_name = os.path.split(img_path[0])[1]
                img = torch.from_numpy(img).unsqueeze(0).to(self.device)
                pred = self.model(img)
                pred = pred[pred[:, :, 4] > conf_thres]

                if len(pred) > 0:
                    detections = non_max_suppression(pred.unsqueeze(0), conf_thres, nms_thres)
                    entry = self.scale_detections(img_path[0], detections[0])
                
                if len(entry['annotations']) > 0:
                    self.data['images'][image_name] = entry
            self.progress.emit(count + 1, image_name, entry)
        self.finished.emit(self.data)
