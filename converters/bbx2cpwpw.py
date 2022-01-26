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
from tqdm import tqdm
from PIL import Image
from PIL.ExifTags import TAGS

for key, value in TAGS.items():
    if value == "ExifOffset":
        break
EXIF_OFFSET = key

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

# Ask for .bbx file
BBX_FILE = input('Enter the path and file name of your .bbx file: ')
BBX_FILE = os.path.abspath(BBX_FILE)
IMAGE_PATH = os.path.dirname(BBX_FILE) + os.sep
try:
    f = open(BBX_FILE)
    DATA = json.load(f)
    f.close()
except FileNotFoundError:
    print('Unable to open .bbx file.')
    sys.exit(0)

# Check species labels match
print('Verifing species names...')
for image in DATA['images']:
    annotations = DATA['images'][image]['annotations']
    for a in annotations:
        if a['label'].lower() not in SPECIES:
            print("Species list in the database does not contain [{}]".format(a['label']))
            sys.exit(0)
print()

# Load observers and ask for ID number
observers = {}
results = cur.execute('Select ObserverID, LastName, FirstName from Observers').fetchall()
for rec in results:
    observers[str(rec[0])] = '{}, {}'.format(rec[1], rec[2])
    print('{}: {},{}'.format(rec[0], rec[1], rec[2]))
OBSID = {}
for obs in DATA['analysts']:
    obsid = input('Which ObserverID should be associated with observer [{}]? '.format(obs))
    if obsid not in observers:
        print('That ObserverID is not recognized')
        sys.exit(0)
    OBSID[obs] = obsid
print()

# Load VisitIDs
# TODO: Make just one SQL statement(?)
# Pull StudyAreas data, StudyAreaID, StudyAreaName
study_area = {}
results = cur.execute('select StudyAreaID, StudyAreaName from StudyAreas').fetchall()
for rec in results:
    study_area[rec[0]] = rec[1]
# Pull CameraLocations data, LocationID, StudyAreaID, LocationName
locations = {}
results = cur.execute('select LocationID, StudyAreaID, LocationName from CameraLocations').fetchall()
for rec in results:
    locations[rec[0]] = (rec[1], rec[2])
# Pull Visits data, VisitID, LocationID, VisitTypeID=2 (Pull) order by VisitDate
visit_type = {1: 'Check', 2: 'Pull'}
visit_id_list = []
results = cur.execute('select VisitID, LocationID, VisitDate, VisitTypeID from Visits where VisitTypeID = 2 or VisitTypeID = 1 order by VisitDate asc').fetchall()
for rec in results:
    visit_id_list.append(str(rec[0]))
    print('{}: {} - {} [{}] ({})'.format(rec[0], study_area[locations[rec[1]][0]], locations[rec[1]][1], rec[2], visit_type[rec[3]]))
VISITID = input('Which VisitID should the data be associated with? ')
if VISITID not in visit_id_list:
    print('That VisitID is not recognized')
    sys.exit(0)

# Get all image files
files = glob.glob(IMAGE_PATH + '*')
image_format = [".jpg", ".jpeg", ".png"]
f = (lambda x: os.path.splitext(x)[1].lower() in image_format)
image_list = list(filter(f, files))
image_list = [os.path.basename(x) for x in image_list]
image_list = sorted(image_list)

# Import data
counter = 1
for name in tqdm(image_list):
    file_name = os.path.join(IMAGE_PATH, name)
    img = Image.open(file_name)
    exif = img.getexif()
    img.close()
    info = exif.get_ifd(EXIF_OFFSET)
    try:
        created = info[36867]
        timestamp = datetime.datetime.fromisoformat(created.replace(':', '-', 2))
    except KeyError:
        timestamp = None
    cur.execute('INSERT INTO Photos (ImageNum, FileName, ImageDate, FilePath, VisitID) VALUES (?, ?, ?, ?, ?)', (counter, name, timestamp, IMAGE_PATH, VISITID))
    conn.commit()
    image_rec_id = float(cur.execute('SELECT @@Identity').fetchone()[0])
    counter += 1

    if name in DATA['images']:
        detections = {}
        anno = DATA['images'][name]['annotations']
        for a in anno:
            bbox = a['bbox']
            XLen = (bbox['xmax'] - bbox['xmin'])
            YLen = (bbox['ymax'] - bbox['ymin'])
            TagX = bbox['xmin'] + (XLen / 2.0)
            TagY = bbox['ymin'] + (YLen / 2.0)
            for obs in OBSID.keys():
                cur.execute('INSERT INTO PhotoTags (TagX, TagY, XLen, YLen, ImageID, ObsID) values (?, ?, ?, ?, ?, ?)', (TagX, TagY, XLen, YLen, image_rec_id, OBSID[obs]))
            if a['label'] not in detections:
                detections[a['label']] = 1.0
            else:
                detections[a['label']] += 1.0

        for d in detections.keys():
            for obs in OBSID.keys():
                cur.execute('INSERT INTO Detections (SpeciesID, Individuals, ObsID, ImageID) values (?, ?, ?, ?)', (SPECIES[d.lower()], detections[d], OBSID[obs], image_rec_id))
    else:
        for obs in OBSID.keys():
            cur.execute('INSERT INTO Detections (SpeciesID, Individuals, ObsID, ImageID) values (?, ?, ?, ?)', (SPECIES['none'], 1.0, OBSID[obs], image_rec_id))
    conn.commit()
