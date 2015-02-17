""" 
 @file
 @brief This file contains the clip properties model, used by the properties view
 @author Jonathan Thomas <jonathan@openshot.org>
 
 @section LICENSE
 
 Copyright (c) 2008-2014 OpenShot Studios, LLC
 (http://www.openshotstudios.com). This file is part of
 OpenShot Video Editor (http://www.openshot.org), an open-source project
 dedicated to delivering high quality video editing and animation solutions
 to the world.
 
 OpenShot Video Editor is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.
 
 OpenShot Video Editor is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.
 
 You should have received a copy of the GNU General Public License
 along with OpenShot Library.  If not, see <http://www.gnu.org/licenses/>.
 """

import os, types
from urllib.parse import urlparse
from collections import OrderedDict
from classes import updates
from classes import info
from classes.query import File, Clip
from classes.logger import log
from classes.settings import SettingStore
from classes.app import get_app
from PyQt5.QtCore import QMimeData, QSize, Qt, QCoreApplication, QPoint, QFileInfo
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QTreeWidget, QApplication, QMessageBox, QTreeWidgetItem, QAbstractItemView
import openshot # Python module for libopenshot (required video editing module installed separately)

try:
    import json
except ImportError:
    import simplejson as json

class ClipStandardItemModel(QStandardItemModel):
	
	def __init__(self, parent=None):
		QStandardItemModel.__init__(self)
		
	def mimeData(self, indexes):
		
		# Create MimeData for drag operation
		data = QMimeData()

		# Get list of all selected file ids
		property_names = []
		for item in indexes:
			selected_row = self.itemFromIndex(item).row()
			property_names.append(self.item(selected_row, 0).data())
		data.setText(json.dumps(property_names))

		# Return Mimedata
		return data


class ClipPropertiesModel():
	
	# Update the selected item (which drives what properties show up)
	def update_item(self, item_id, item_type):
		# Clear previous selection
		self.selected = []
		
		if item_type == "clip":
			c = None
			clips = get_app().window.timeline_sync.timeline.Clips()
			for clip in clips:
				if clip.Id() == item_id:
					c = clip
					break
				
			self.selected.append(c)
		
		# Update the model data
		self.update_model(get_app().window.txtPropertyFilter.text())
		
	# Update the values of the selected clip, based on the current frame
	def update_frame(self, frame_number):
		# Update frame number
		self.frame_number = frame_number

		# Update the model data
		self.update_model(get_app().window.txtPropertyFilter.text())
			
	
	def value_updated(self, item):
		log.info("itemChanged to %s" % item.text())
		
	
	def update_model(self, filter=""):
		log.info("updating clip properties model.")
		app = get_app()
		
		# Get a generic emtpy clip
		if self.selected:
			c = self.selected[0]
			
			# example code to add a keyframe
			#c.alpha.AddPoint(1, 1.0);
			#c.alpha.AddPoint(750, 0.0);
			#c.location_x.AddPoint(1, 100.0);
			#c.location_x.AddPoint(300, 25.0);
			
			# Get raw unordered JSON properties
			raw_properties = json.loads(c.PropertiesJSON(self.frame_number))

			# Check if the properties changed for this clip?
			if raw_properties["hash"]["memo"] != self.previous_hash:
				self.previous_hash = raw_properties["hash"]["memo"]
			else:
				# Properties don't need to be updated (they haven't changed)
				return
			
			# Clear previous model data (if any)
			self.model.clear()
	
			# Add Headers
			self.model.setHorizontalHeaderLabels(["Property", "Value" ])

			# Sort the list of properties 
			all_properties = OrderedDict(sorted(raw_properties.items(), key=lambda x: x[1]['name']))
	
			# Loop through properties, and build a model	
			for property in all_properties.items():
				label = property[1]["name"]
				name = property[1]["name"]
				value = property[1]["value"]
				type = property[1]["type"]
				memo = property[1]["memo"]
				readonly = property[1]["readonly"]
				keyframe = property[1]["keyframe"]
				points = property[1]["points"]
				
				# Hide filtered out properties
				if filter and filter.lower() not in name.lower():
					continue
				
				row = []
				
				# Append Property Name
				col = QStandardItem("Property")
				col.setText(label)
				if keyframe and points > 1:
					col.setBackground(QColor("green")) # Highlight keyframe background
				elif points > 1:
					col.setBackground(QColor(42, 130, 218)) # Highlight interpolated value background
				col.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
				row.append(col)
				
				# Append Value
				col = QStandardItem("Value")
				col.setText(str(value))
				if keyframe and points > 1:
					col.setBackground(QColor("green")) # Highlight keyframe background
				elif points > 1:
					col.setBackground(QColor(42, 130, 218)) # Highlight interpolated value background
				col.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsEditable)
				row.append(col)
	
				# Append ROW to MODEL (if does not already exist in model)
				self.model.appendRow(row)
				
		else:
			# Clear previous properties hash
			self.previous_hash = ""
			
			# Clear previous model data (if any)
			self.model.clear()
	
			# Add Headers
			self.model.setHorizontalHeaderLabels(["Property", "Value" ])



	def __init__(self, *args):
		
		# Keep track of the selected items (clips, transitions, etc...)
		self.selected = []
		self.frame_number = 1
		self.previous_hash = ""

		# Create standard model 
		self.model = ClipStandardItemModel()
		self.model.setColumnCount(2)

		# Connect data changed signal
		self.model.itemChanged.connect(self.value_updated)
		