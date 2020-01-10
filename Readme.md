# Bounding Box Editor and Exporter (BBoxEE)

BBoxEE is a open-source tool for annotating bounding boxes and exporting data to training object detectors. BBoxEE was specifically developed for the [Animal Detection Network (Andenet)](http://biodiversityinformatics.amnh.org/ml4conservation/animal-detection-network/) initiative, however, it is not limited to annotating camera trap data and can be used for any bounding box annotation task.

BBoxEE is actively under development by Peter Ersts and Ned Horning of the [Center for Biodiversity and Conservation at the American Museum of Natural History](https://www.amnh.org/our-research/center-for-biodiversity-conservation). Additional documentation will be forthcoming.



## Installation

### Dependencies
BBoxEE is being developed on Ubuntu 18.04 with the following libraries:

* PyQt5 (5.10.1)
* TKinter (3.6.9)
* Pillow (6.1.0)
* Numpy (1.17.0)

Install GUI libraries:

``` bash
sudo apt install python3-pyqt5 python3-tk
```
Install pip3 and install / upgrade dependencies:

```bash
sudo apt install python3-pip
sudo -H pip3 install numpy
sudo -H pip3 install --upgrade pillow
```

### Launching BBoxEE
```bash
git clone https://github.com/persts/BBoxEE
cd BBoxEE
python3 main.py
```
This is all you need to do to begin using the base annotation functionality of BBoxEE.

------

## Assisted Annotation and Exporting

Assisted Annotation is the ability to load an existing object detection model and use the model's prediction(s) as initial annotated bounding box. Assisted Annotation is useful approach for visually assessing the accuracy and precision of your model as you continue to collect additional training data. 

Exporting to some formats may require additional libraries / frameworks.

## Assisted Annotation with Tensorflow and TFRecord Export

### Additional Dependencies:
* lxml (4.4.2)
* TensorFlow (1.15.0)

```bash
sudo -H pip3 install --upgrade lxml
sudo -H pip3 install matplotlib
```

For detailed steps to install TensorFlow, follow the [TensorFlow installation instructions](https://www.tensorflow.org/install/). A typical user can install Tensorflow using one of the following commands:

``` bash
# For CPU
sudo -H pip3 install tensorflow==1.15
# For GPU
sudo -H pip3 install tensorflow-gpu==1.15
```

## Assisted Annotation with YOLOv3 (Torch)

### Additional Dependencies:
* Torch (1.0.0)
* Matplotlib (3.0.2)
* Opencv-python (3.4.5.20)

``` bash
sudo -H pip3 install torch
sudo -H pip3 install matplotlib
sudo -H pip3 install opencv-python
```

Clone Ultralytics YOLOv3 repo:
``` bash
git clone https://github.com/ultralytics/yolov3 DESTINATION
```
### PYTHONPATH
Add Libraries to PYTHONPATH:
``` bash
export PYTHONPATH=$PYTHONPATH:DESTINATION
```
Note: This export command needs to run from every new terminal you start. If you wish to avoid running this manually, you can add it as a new line to the end of your ~/.bashrc file.

## Quick Start Guide
We have put together a [quick start guide](https://github.com/persts/BBoxEE/blob/master/doc/Quick%20Start%20Guide.pdf). This quick start guide is intended to introduce the basic functionality of BBoxEE. It is not intended to be a comprehensive user guide. Additional documentation will follow.