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


def annotation_file():
    """Factory for the Animal Detection Network annotation file."""
    return {'mask': None,
            'mask_name': '',
            'images': {},
            'analysts': [],
            'review': [],
            'skip_export': [],
            'schema': '1.1.0'}


def annotation_file_entry():
    """Factory for the Animal Detection Network annotation file entry."""
    return {'attribution': '',
            'license': '',
            'license_url': '',
            'annotations': []}


def annotation():
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


def package():
    """Factory Animal Detection Network package."""
    return {'labels': [], 'metadata': []}


def package_entry():
    """Factory for an entry in the Animal Detection Network package."""
    return {'date_captured': '',
            'attribution': '',
            'license': '',
            'license_url': '',
            'file_name': '',
            'mask_name': '',
            'directory': '',
            'annotations': []}
