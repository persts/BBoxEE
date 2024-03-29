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
import glob
import pyodbc
import datetime
import numpy as np
from tqdm import tqdm
import tensorflow as tf
from PIL import Image
from PIL.ExifTags import TAGS

for key, value in TAGS.items():
    if value == "ExifOffset":
        break
EXIF_OFFSET = key


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


if 'Microsoft Access Driver (*.mdb, *.accdb)' not in pyodbc.drivers():
    print('No Microsoft Access Driver found.')
    sys.exit(0)

print('----------------------------------------------------------------------------')
print('DO NOT RUN THIS SCRIPT ON YOUR MAIN DATABASE WITHOUT CREATING A BACKUP FIRST!')
print('----------------------------------------------------------------------------')
print()
print()
print('Example database path: c:\\database\\import-test.accdb')
print()
# Ask for database file and open
database = input("Enter the path and file name of your database: ")
try:
    conn = pyodbc.connect('DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + database)
    cur = conn.cursor()
except pyodbc.Error:
    print('Unable to open database.')
    sys.exit(0)

# Load species list
SPECIES = {}
results = cur.execute('Select SpeciesID, CommonName from Species').fetchall()
for rec in results:
    SPECIES[rec[1].lower()] = rec[0]
if "none" not in SPECIES:
    print('"None" label is missing from the species list')
    sys.exit(0)

# Ask for labelmap file
label_map_file = input('Enter the path and file name of your label map: ')
label_map_file = os.path.abspath(label_map_file)
LABEL_MAP = build_label_map(label_map_file)

# Check species labels match
print('Verifing species names...')
for label in LABEL_MAP:
    if LABEL_MAP[label].lower() not in SPECIES:
        print("Species list in the database does not contain [{}]".format(LABEL_MAP[label]))
        sys.exit(0)
print()

# Ask for the saved model
model_dir = input('Enter the path and file name of your saved model: ')
print('Loading model...')
MODEL = tf.saved_model.load(model_dir)
print()

# Get detection threshold
value = input('Enter the confidence threshold (0.1 to 1.0): ')
THRESHOLD = float(value)
if THRESHOLD == 0.0:
    print('Invalid threshold value.')
    sys.exit(0)

# Ask for image folder
IMAGE_PATH = input('Enter the path and folder name with your images: ')
IMAGE_PATH = os.path.abspath(IMAGE_PATH) + os.sep
print()

# Load observers and ask for ID number
observers = {}
results = cur.execute('Select ObserverID, LastName, FirstName from Observers').fetchall()
print('{:<12}Last, First'.format('ObserverID'))
for rec in results:
    observers[str(rec[0])] = '{}, {}'.format(rec[1], rec[2])
    print('{:<12}{}, {}'.format(*rec))
OBSID = input('Which ObserverID should the data be associated with? ')
if OBSID not in observers:
    print('That ObserverID is not recognized')
    sys.exit(0)
print()

# Load VisitIDs
# en: converted to one SQL statement
visit_id_list = []
results = cur.execute(
    '''select Visits.VisitID,
        StudyAreas.StudyAreaName,  CameraLocations.LocationName,
        Format(Visits.VisitDate, 'short date') As VisitDate,
        lkupVisitTypes.VisitType
    from ((StudyAreas inner join
      CameraLocations on
        StudyAreas.StudyAreaID = CameraLocations.StudyAreaID) inner join
      Visits on
        CameraLocations.LocationID = Visits.LocationID) inner join
      lkupVisitTypes on
        Visits.VisitTypeID = lkupVisitTypes.ID
    where Visits.VisitTypeID < 3
    order by Visits.VisitDate, Visits.VisitID;''').fetchall()
print('{:<12}Description'.format('VisitID'))
for rec in results:
    visit_id_list.append(str(rec[0]))
    print('{:<12}{} - {} - {} ({})'.format(*rec))
VISITID = input('Which VisitID should the data be associated with? ')
if VISITID not in visit_id_list:
    print('That VisitID is not recognized')
    sys.exit(0)

# Get all image files
files = glob.glob(os.path.join(IMAGE_PATH, '*'))
image_format = [".jpg", ".jpeg", ".png"]
f = (lambda x: os.path.splitext(x)[1].lower() in image_format)
image_list = list(filter(f, files))
image_list = [os.path.basename(x) for x in image_list]
image_list = sorted(image_list)

# Import data
counter = 1
active_start = None
active_end = None
for name in tqdm(image_list):
    file_name = os.path.join(IMAGE_PATH, name)
    img = Image.open(file_name)
    image_np = np.array(img)
    exif = img.getexif()
    img.close()
    info = exif.get_ifd(EXIF_OFFSET)
    try:
        created = info[36867]
        timestamp = datetime.datetime.fromisoformat(created.replace(':', '-', 2))
    except KeyError:
        # en: default to date modified in case 36867 (date taken) is unavailable
        #   some makes/firmware versions don't include 36867 in the exif
        timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(file_name))
    # en: added Pending and ObsCount flags
    cur.execute(
        '''INSERT INTO Photos (ImageNum, FileName, ImageDate, FilePath, VisitID, Pending, ObsCount)
        VALUES (?, ?, ?, ?, ?, True, 1 )''', (counter, name, timestamp, IMAGE_PATH, VISITID))
    conn.commit()
    image_rec_id = float(cur.execute('SELECT @@Identity').fetchone()[0])
    # en: retain date of first photo for updating Visits table
    #   uses min/max in case filenames are not in chronological order
    if counter == 1:
        active_start = timestamp
        active_end = timestamp
    else:
        active_start = min(active_start, timestamp)
        active_end = max(active_end, timestamp)
    counter += 1

    # Expand dimensions since the model expects images
    # to have shape: [1, None, None, 3]
    image_np_expanded = np.expand_dims(image_np, axis=0)
    # Actual detection.
    dets = MODEL(image_np_expanded)
    scores = dets['detection_scores'][0].numpy()
    boxes = dets['detection_boxes'][0].numpy()
    classes = dets['detection_classes'][0].numpy()
    detection = False
    detections = {}
    for index, score in enumerate(scores):
        if score >= THRESHOLD:
            detection = True
            bbox = boxes[index]
            xmin = float(bbox[1])
            xmax = float(bbox[3])
            ymin = float(bbox[0])
            ymax = float(bbox[2])
            class_number = int(classes[index])
            label = LABEL_MAP[class_number]
            XLen = xmax - xmin
            YLen = ymax - ymin
            TagX = xmin + (XLen / 2.0)
            TagY = ymin + (YLen / 2.0)
            cur.execute(
                '''INSERT INTO PhotoTags (TagX, TagY, XLen, YLen, ImageID, ObsID)
                VALUES (?, ?, ?, ?, ?, ?)''', (TagX, TagY, XLen, YLen, image_rec_id, OBSID))
            if label not in detections:
                detections[label] = 1.0
            else:
                detections[label] += 1.0

    if detection:
        for d in detections.keys():
            cur.execute(
                '''INSERT INTO Detections (SpeciesID, Individuals, ObsID, ImageID)
                VALUES (?, ?, ?, ?)''', (SPECIES[d.lower()], detections[d], OBSID, image_rec_id))
    else:
        cur.execute(
            '''INSERT INTO Detections (SpeciesID, Individuals, ObsID, ImageID)
            VALUES (?, ?, ?, ?)''', (SPECIES['none'], 1.0, OBSID, image_rec_id))
    # en: update flags in photos table based on detection info
    cur.execute(
        '''UPDATE Photos
        SET MultiSp = ?, NotNone = ?
        WHERE ImageID = ?''', ((len(detections) > 1), detection, image_rec_id))
    conn.commit()

# en: Update active start and end fields
cur.execute('UPDATE Visits SET ActiveStart = ?, ActiveEnd = ? WHERE VisitID = ?', (active_start, active_end, VISITID))
conn.commit()

# en: alternate version - probably less efficient but it avoids extra lines in
#   the for loop
# results = cur.execute('Select Min(ImageDate) As ActiveStart, Max(ImageDate) As ActiveEnd from Visits where VisitID = ?', VISITID).fetchall()
# cur.execute('UPDATE Visits SET ActiveStart = ?, ActiveEnd = ? WHERE VisitID = ?', (results[0], results[1], VISITID))
# conn.commit()

# could be done in a single SQL statement in MS Access using DMin and DMax, but
#   those aren't available via the access ODBC driver
