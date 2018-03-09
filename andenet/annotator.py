import os
from PIL import Image
from PyQt5 import QtCore
from andenet import schema
import tensorflow as tf
import numpy as np
from utils import label_map_util


class Annotator(QtCore.QThread):
    """Threaded worker to keep gui from freezing while processing images."""

    progress = QtCore.pyqtSignal(int)
    finished = QtCore.pyqtSignal(dict)

    def __init__(self, directory):
        """Class init function."""
        QtCore.QThread.__init__(self)
        self.image_list = []
        self.threshold = 0.9
        self.image_directory = ''
        self.data = None
        self.detection_graph = tf.Graph()
        self.label_map = label_map_util.load_labelmap(directory + os.path.sep + 'label_map.pbtxt')
        self.categories = label_map_util.convert_label_map_to_categories(self.label_map, max_num_classes=100, use_display_name=True)
        self.category_index = label_map_util.create_category_index(self.categories)
        od_graph_def = tf.GraphDef()
        with self.detection_graph.as_default():
            od_graph_def = tf.GraphDef()
            with tf.gfile.GFile(directory + os.path.sep + 'frozen_inference_graph.pb', 'rb') as fid:
                serialized_graph = fid.read()
                od_graph_def.ParseFromString(serialized_graph)
                tf.import_graph_def(od_graph_def, name='')

    def run(self):
        """The starting point for the thread."""
        self.data = schema.annotation_file()
        counter = 0
        with self.detection_graph.as_default():
            with tf.Session(graph=self.detection_graph) as sess:
                # Definite input and output Tensors for detection_graph
                image_tensor = self.detection_graph.get_tensor_by_name('image_tensor:0')
                # Each box represents a part of the image where a particular object was detected.
                detection_boxes = self.detection_graph.get_tensor_by_name('detection_boxes:0')
                # Each score represent how level of confidence for each of the objects.
                # Score is shown on the result image, together with the class label.
                detection_scores = self.detection_graph.get_tensor_by_name('detection_scores:0')
                detection_classes = self.detection_graph.get_tensor_by_name('detection_classes:0')
                num_detections = self.detection_graph.get_tensor_by_name('num_detections:0')
                for img in self.image_list:
                    image = Image.open(self.image_directory + img)
                    # the array based representation of the image will be used later in order to prepare the
                    # result image with boxes and labels on it.
                    image_np = np.array(image)
                    # Expand dimensions since the model expects images to have shape: [1, None, None, 3]
                    image_np_expanded = np.expand_dims(image_np, axis=0)
                    # Actual detection.
                    (boxes, scores, classes, num) = sess.run([detection_boxes, detection_scores, detection_classes, num_detections], feed_dict={image_tensor: image_np_expanded})
                    boxes = np.squeeze(boxes)
                    scores = np.squeeze(scores)
                    classes = np.squeeze(classes)
                    entry = schema.annotation_file_entry()
                    for i in range(len(scores)):
                        if scores[i] >= self.threshold:
                            annotation = schema.annotation()
                            annotation['created_by'] = 'machine'
                            bbox = boxes[i]
                            annotation['bbox']['xmin'] = float(bbox[1])
                            annotation['bbox']['xmax'] = float(bbox[3])
                            annotation['bbox']['ymin'] = float(bbox[0])
                            annotation['bbox']['ymax'] = float(bbox[2])
                            annotation['label'] = self.category_index[classes[i]]['name']
                            entry['annotations'].append(annotation)
                    if len(entry['annotations']) > 0:
                        self.data['images'][img] = entry
                    image.close()
                    counter += 1
                    self.progress.emit(counter)
        self.finished.emit(self.data)
