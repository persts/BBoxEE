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
import json
import ntpath
import sys

# Usage check
if len(sys.argv) != 3:
    print('USAGE: python3 megadetector2bbx.py JSON_FILE CONFIDENCE')
    print('EXAMPLE: python3 megadetector2bbx.py MDv4_1Output.json 0.8')
    sys.exit()
FILE_NAME = sys.argv[1]
CONF = float(sys.argv[2])


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
            'bbox': {'xmin': 0,
                     'xmax': 0,
                     'ymin': 0,
                     'ymax': 0},
            'label': 'N/A',
            'occluded': 'N',
            'truncated': 'N',
            'difficult': 'N',
            'schema': '1.0.0'}


# Load the data
file = open(FILE_NAME, 'r')
data_in = json.load(file)
file.close()

# Find all of the base paths
s = set()
for image in data_in['images']:
    s.add(ntpath.split(image['file'])[0])
paths = list(s)

# Display the list of paths and ask user which one to use
for index, path in enumerate(paths):
    print('{} {}'.format(str(index).ljust(5), path))

index = 0
if len(paths) > 1:
    try:
        index = int(input('Create bbx file for which path (0 - {}): '.format(len(paths) - 1)))
    except ValueError:
        print('"Invalid number...aborting')
        sys.exit()

if index < 0 or index > len(paths):
    print('Index out of range...aborting')
    sys.exit()

base_path = paths[index]

# initialize the bbx object
bbx = annotation_file()
bbx['analysts'].append('MegaDetetector')
labels = data_in['detection_categories']

# Look through the images and convert bboxes to bbx format
for image in data_in['images']:
    base, file = ntpath.split(image['file'])
    if base == base_path:
        annotations = []
        for detection in image['detections']:
            if detection['conf'] >= CONF:
                annotation = annotation_block()
                annotation['created_by'] = 'machine'
                annotation['label'] = labels[detection['category']]
                annotation['bbox']['xmin'] = detection['bbox'][0]
                annotation['bbox']['xmax'] = detection['bbox'][0] + detection['bbox'][2]
                annotation['bbox']['ymin'] = detection['bbox'][1]
                annotation['bbox']['ymax'] = detection['bbox'][1] + detection['bbox'][3]
                annotations.append(annotation)
        if len(annotations) > 0:
            bbx['images'][file] = annotation_file_entry()
            bbx['images'][file]['annotations'] = annotations

# Save the bbx file
file_name = '{}.bbx'.format(ntpath.split(base_path)[1])
file = open(file_name, 'w')
json.dump(bbx, file, indent=4)
file.close()
print('{} has been created.'.format(file_name))
print('Move the bbx file to {}.'.format(base_path))
