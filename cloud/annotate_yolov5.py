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
import sys
import json
import torch
import ntpath
import numpy as np
from PIL import Image
from yolov5.utils.augmentations import letterbox
from yolov5.utils.general import non_max_suppression, scale_boxes, xyxy2xywh
from tqdm import tqdm

# Usage check
if len(sys.argv) != 6:
    print('USAGE: python3 annotate_yolov5.py TOP_DATA_FOLDER MODEL SHAPE STRIDE CONFIDENCE')
    print('EXAMPLE: python3 annotate_yolov5.py ../demo ../models/md_v5a.0.1.pt 1280 64 0.8')
    sys.exit()
FORMATS = [".jpg", ".jpeg", ".png"]
PATH = sys.argv[1]
MODEL = sys.argv[2]
SHAPE = int(sys.argv[3])
STRIDE = int(sys.argv[4])
THRESHOLD = float(sys.argv[5])


# Helper functions so bboxee.schema does not have to be in pythonpath
def annotation_file():
    """Factory for the annotation file."""
    return {'mask': None,
            'mask_name': '',
            'images': {},
            'analysts': [],
            'review': [],
            'skip_export': [],
            'schema': '1.1.0'}


def annotation_file_entry():
    """Factory for the annotation file entry."""
    return {'attribution': '',
            'license': '',
            'license_url': '',
            'annotations': []}


def annotation_block():
    """Factory for an annotation block."""
    return {'created_by': '',
            'updated_by': '',
            'confidence': 1.0,
            'bbox': {'xmin': 0,
                     'xmax': 0,
                     'ymin': 0,
                     'ymax': 0},
            'label': 'N/A',
            'occluded': 'N',
            'truncated': 'N',
            'difficult': 'N',
            'schema': '1.0.0'}


# Find all of the folders containing images
folders = []
walk_data = os.walk(PATH)
for dirpath, dirs, files in walk_data:
    f = (lambda x: os.path.splitext(x)[1].lower() in FORMATS)
    image_list = list(filter(f, files))
    if len(image_list) > 0:
        folders.append((dirpath, image_list))

# Load model
device = 'cpu'
if torch.cuda.is_available():
    device = 'cuda:0'
try:
    if torch.backends.mps.is_built and torch.backends.mps.is_available():
        device = 'mps'
except AttributeError:
    pass
checkpoint = torch.load(MODEL)
# Patch for older YOLOv5 models
for m in checkpoint['model'].modules():
    if isinstance(m, torch.nn.Upsample) and not hasattr(m, 'recompute_scale_factor'):
        m.recompute_scale_factor = None
model = checkpoint['model'].float().fuse().eval().to(device)

# Loop through all of the folder with images and process each image
for index, (folder, images) in enumerate(folders):
    print('Processing folder [{}] ({} of {})'.format(folder, str(index + 1), str(len(folders))))
    bbx_file_name = '{}{}{}.bbx'.format(folder, os.path.sep, ntpath.split(folder)[1])
    bbx_data = annotation_file()
    bbx_data['analysts'].append('Machine Generated')

    # Pass each image through model
    for i in tqdm(range(len(images))):
        image_name = images[i]
        file_name = os.path.join(folder, image_name)

        image = Image.open(file_name)
        img_original = np.asarray(image)
        image.close()
        # padded resize
        img = letterbox(img_original, new_shape=SHAPE, stride=STRIDE, auto=True)[0]  # JIT requires auto=False
        img = img.transpose((2, 0, 1))  # HWC to CHW; PIL Image is RGB already
        img = np.ascontiguousarray(img)
        img = torch.from_numpy(img)
        img = img.float()
        img /= 255
        img = torch.unsqueeze(img, 0).to(device)
        pred: list = model(img)[0]
        pred = non_max_suppression(prediction=pred.cpu(), conf_thres=THRESHOLD)
        gn = torch.tensor(img_original.shape)[[1, 0, 1, 0]]  # normalization gain whwh
        entry = annotation_file_entry()
        for det in pred:
            if len(det):
                # Rescale boxes
                det[:, :4] = scale_boxes(img.shape[2:], det[:, :4], img_original.shape).round()
                for *box, conf, cls in reversed(det):
                    annotation = annotation_block()
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
                    annotation['label'] = model.names[int(cls.item())]
                    annotation['confidence'] = conf.item()
                    entry['annotations'].append(annotation)
        if len(entry['annotations']) > 0:
            bbx_data['images'][image_name] = entry

    # Dump annotations
    bbxfile = open(bbx_file_name, 'w')
    json.dump(bbx_data, bbxfile, indent=2)
    bbxfile.close()
