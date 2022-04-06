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
print('{:<12}Last, First'.format('ObserverID'))
for rec in results:
    observers[str(rec[0])] = '{}, {}'.format(rec[1], rec[2])
    print('{:<12}{}, {}'.format(*rec))
OBSID = {}
for obs in DATA['analysts']:
    obsid = input('Which ObserverID should be associated with observer [{}]? '.format(obs))
    if obsid not in observers:
        print('That ObserverID is not recognized')
        sys.exit(0)
    OBSID[obs] = obsid
STATUS_ID = 1
if len(OBSID) > 1:
    # If more than one observer, detection status is going to be considered verified
    STATUS_ID = 2
print()

# Load VisitIDs
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
files = glob.glob(IMAGE_PATH + '*')
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
    exif = img.getexif()
    img.close()
    info = exif.get_ifd(EXIF_OFFSET)
    try:
        created = info[36867]
        timestamp = datetime.datetime.fromisoformat(created.replace(':', '-', 2))
    except KeyError:
        # en: default to date modified in case 36867 (date taken) is unavailable
        #   some makes/firmware versions don't include 36867 in the exif
        timestamp = os.path.getmtime(file_name)
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

    detection = False
    detections = {}
    if name in DATA['images']:
        anno = DATA['images'][name]['annotations']
        for a in anno:
            detection = True
            bbox = a['bbox']
            XLen = (bbox['xmax'] - bbox['xmin'])
            YLen = (bbox['ymax'] - bbox['ymin'])
            TagX = bbox['xmin'] + (XLen / 2.0)
            TagY = bbox['ymin'] + (YLen / 2.0)
            for obs in OBSID.keys():
                cur.execute(
                    '''INSERT INTO PhotoTags (TagX, TagY, XLen, YLen, ImageID, ObsID)
                    VALUES (?, ?, ?, ?, ?, ?)''', (TagX, TagY, XLen, YLen, image_rec_id, OBSID[obs]))
            if a['label'] not in detections:
                detections[a['label']] = 1.0
            else:
                detections[a['label']] += 1.0

        for d in detections.keys():
            for obs in OBSID.keys():
                cur.execute(
                    '''INSERT INTO Detections (SpeciesID, Individuals, ObsID, ImageID, StatusID)
                    VALUES (?, ?, ?, ?, ?)''', (SPECIES[d.lower()], detections[d], OBSID[obs], image_rec_id, STATUS_ID))
    else:
        for obs in OBSID.keys():
            cur.execute(
                '''INSERT INTO Detections (SpeciesID, Individuals, ObsID, ImageID, StatusID)
                VALUES (?, ?, ?, ?, ?)''', (SPECIES['none'], 1.0, OBSID[obs], image_rec_id, STATUS_ID))
    if len(OBSID) > 1:
        cur.execute(
            '''UPDATE Photos
                SET Pending = False, Verified = True, ObsCount = ?
                WHERE ImageID = ?''', (len(OBSID), image_rec_id))
    cur.execute(
        '''UPDATE Photos
            SET MultiSp = ?, NotNone = ?
            WHERE ImageID = ?''', ((len(detections) > 1), detection, image_rec_id))
    conn.commit()

# en: Update active start and end fields
cur.execute('UPDATE Visits SET ActiveStart = ?, ActiveEnd = ? WHERE VisitID = ?', (active_start, active_end, VISITID))
conn.commit()
