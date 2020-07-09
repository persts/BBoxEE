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
import glob
import json
import ntpath
import os
import sys

# Usage check
if len(sys.argv) != 2:
    print('USAGE: python3 bbx2timelapse.py ROOT_FOLDER')
    print('EXAMPLE: python3 bbx2timelapse.py c:\\project\data')
    sys.exit()
base_path = sys.argv[1]

# Find all of the .bbx files
bbx_list = glob.glob(base_path + os.path.sep + '**/*.bbx', recursive=True)

timelapse = {"images": [], "detection_categories": {}}
categories = []

# Open each .bbx file
for bbx in bbx_list:
    base = ntpath.split(bbx)[0].replace(base_path + os.path.sep, '')
    base += os.path.sep
    base = base.replace('/', '\\')  # If processed on linux udpate sep
    file = open(bbx, 'r')
    data = json.load(file)
    file.close()
    # Get all of the annotations in the .bbx file and convert them to
    # a megadetector like json output for timelapse
    for image in data['images']:
        entry = {'file': base + image, 'detections': []}
        for a in data['images'][image]['annotations']:
            if a['label'] not in categories:
                categories.append(a['label'])
            detection = {'category': '', 'conf': 1.0, 'bbox': []}
            detection['category'] = str(categories.index(a['label']) + 1)
            detection['bbox'].append(a['bbox']['xmin'])
            detection['bbox'].append(a['bbox']['ymin'])
            detection['bbox'].append(a['bbox']['xmax'] - a['bbox']['xmin'])
            detection['bbox'].append(a['bbox']['ymax'] - a['bbox']['ymin'])
            entry['detections'].append(detection)
        timelapse['images'].append(entry)

# Build the detection category list
for index, cat in enumerate(categories):
    timelapse['detection_categories'][str(index + 1)] = cat

# Save the data
file = open('timelapse.json', 'w')
json.dump(timelapse, file, indent=4)
file.close()
