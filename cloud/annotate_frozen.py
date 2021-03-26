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
import ntpath
import numpy as np
from PIL import Image
from tqdm import tqdm

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow.compat.v1 as tf  # noqa: E402

# Usage check
if len(sys.argv) != 5:
    print('USAGE: python3 annotate_frozen.py TOP_FOLDER MODEL LABEL_MAP CONFIDENCE')
    print('EXAMPLE: python3 annotate_frozen.py ../demo ../models/md_v4.1.0.pb ../models/label_map.pbtxt 0.8')
    sys.exit()
FORMATS = [".jpg", ".jpeg", ".png"]
PATH = sys.argv[1]
MODEL = sys.argv[2]
LABEL_MAP = sys.argv[3]
THRESHOLD = float(sys.argv[4])


# Helper functions so bboxee.schema does not have to be in pythonpath
def annotation_file():
    """Factory for the annotation file."""
    return {'mask': None,
            'mask_name': '',
            'images': {},
            'analysts': [],
            'schema': '1.0.0'}


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


def build_label_map(file_name):
    # see if we can use this to eliminated the need for
    # label_map_util dependency
    a = open(file_name, 'r')
    string = a.read()
    a.close()
    lines = string.split("\n")
    parsed = ''
    comma = ''
    for line in lines:
        if line == '':
            pass
        elif line.find('item') != -1:
            parsed += '{'
        elif line.find('}') != -1:
            comma = ''
            parsed += '},'
        else:
            parts = line.replace('\\', '').replace('\'', '"').split(':')
            parsed += '{} "{}":{}'.format(comma, parts[0].lstrip(), parts[1])
            comma = ','

    string = "[{}]".format(parsed[0:-1])
    j = json.loads(string)
    label_map = {}
    for entry in j:
        if 'display_name' in entry:
            label_map[entry['id']] = entry['display_name']
        else:
            label_map[entry['id']] = entry['name']
    return label_map


# Find all of the folders containing images
folders = []
walk_data = os.walk(PATH)
for dirpath, dirs, files in walk_data:
    f = (lambda x: os.path.splitext(x)[1].lower() in FORMATS)
    image_list = list(filter(f, files))
    if len(image_list) > 0:
        folders.append((dirpath, image_list))

# Parse label map
label_map = build_label_map(LABEL_MAP)


# Create the detection graph and read in model
detection_graph = tf.Graph()
graph_def = tf.GraphDef()
with tf.io.gfile.GFile(MODEL, 'rb') as fid:
    serialized_graph = fid.read()
    graph_def.ParseFromString(serialized_graph)

with detection_graph.as_default():
    # Import graph
    tf.import_graph_def(graph_def, name='')

    # Begin processing loop
    with tf.Session(graph=detection_graph) as sess:
        image_tensor = (detection_graph.get_tensor_by_name('image_tensor:0'))
        d_boxes = (detection_graph.get_tensor_by_name('detection_boxes:0'))
        d_scores = (detection_graph.get_tensor_by_name('detection_scores:0'))
        d_classes = (detection_graph.get_tensor_by_name('detection_classes:0'))
        num_detections = (detection_graph.get_tensor_by_name('num_detections:0'))

        # Loop through all of the folder with images and process each image
        for index, (folder, images) in enumerate(folders):
            print('Processing folder [{}] ({} of {})'.format(folder, str(index + 1), str(len(folders))))
            bbx_file_name = '{}{}{}.bbx'.format(folder, os.path.sep, ntpath.split(folder)[1])
            bbx_data = annotation_file()
            bbx_data['analysts'].append('Machine Generated')

            # Pass each image through model
            for i in tqdm(range(len(images))):
                img = images[i]
                file_name = os.path.join(folder, img)
                image = Image.open(file_name)
                image_np = np.array(image)
                image_np_expanded = np.expand_dims(image_np, axis=0)
                image.close()
                fd = {image_tensor: image_np_expanded}
                (boxes, scores, classes, num) = sess.run([d_boxes,
                                                         d_scores,
                                                         d_classes,
                                                         num_detections],
                                                         feed_dict=fd)
                boxes = np.squeeze(boxes)
                scores = np.squeeze(scores)
                classes = np.squeeze(classes)
                entry = annotation_file_entry()
                for i in range(len(scores)):
                    if scores[i] >= THRESHOLD:
                        annotation = annotation_block()
                        annotation['created_by'] = 'machine'
                        annotation['confidence'] = float(scores[i])
                        bbox = boxes[i]
                        annotation['bbox']['xmin'] = float(bbox[1])
                        annotation['bbox']['xmax'] = float(bbox[3])
                        annotation['bbox']['ymin'] = float(bbox[0])
                        annotation['bbox']['ymax'] = float(bbox[2])
                        label = 'unknown'
                        if classes[i] in label_map:
                            label = label_map[classes[i]]
                        annotation['label'] = label
                        entry['annotations'].append(annotation)
                if len(entry['annotations']) > 0:
                    bbx_data['images'][img] = entry

            # Dump annotations
            bbxfile = open(bbx_file_name, 'w')
            json.dump(bbx_data, bbxfile)
            bbxfile.close()
