# Bounding Box Editor and Exporter (BBoxEE)

BBoxEE is a open-source tool for annotating bounding boxes and exporting data to training object detectors. BBoxEE was specifically developed for the [Animal Detection Network (Andenet)]([http://biodiversityinformatics.amnh.org/ml4conservation/animal-detection-network/](https://www.amnh.org/research/center-for-biodiversity-conservation/research-and-conservation/biodiversity-informatics/machine-learning-for-conservation)) initiative, however, it is not limited to annotating camera trap data and can be used for any bounding box annotation task.

BBoxEE is actively under development by Peter Ersts of the [Center for Biodiversity and Conservation at the American Museum of Natural History](https://www.amnh.org/our-research/center-for-biodiversity-conservation). Additional documentation will be forthcoming.

------
## Quick Start Guide
We have put together a [quick start guide](https://github.com/persts/BBoxEE/blob/master/doc/Quick%20Start%20Guide.pdf). This quick start guide is intended to introduce the basic functionality of BBoxEE. It is not intended to be a comprehensive user guide. Additional documentation will follow.

------
## Installation

### Dependencies
BBoxEE is being developed with Python 3.8.10 on Ubuntu 20.04 with the following libraries:

* PyQt6 (6.5.3)
* Pillow (10.1.0)
* Numpy (1.24.3)
* Tabulate (0.9.0)
* TensorFlow (2.13.1)
* Torch (2.1.0)
* yolov5 (7.0.13)

Build a virtual environment and install the dependencies:
```bash
cd [Your BBoxEE Workspace]

[Apple M1 Note]
If you follow the Linux steps PyQt6 may not install due to clang not finding Python.h

You can resolve this by adding and additional environmental variable with the following:

export C_INCLUDE_PATH=/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Headers

[Linux & OSX]
python3 -m venv bboxee-env
source bboxee-env/bin/activate
git clone https://github.com/persts/BBoxEE
python -m pip install --upgrade pip
python -m pip install -r BBoxEE/requirements.txt

[Windows]
python -m venv bboxee-env
bboxee-env\Scripts\activate.bat
git clone https://github.com/persts/BBoxEE
python -m pip install --upgrade pip
python -m pip install -r BBoxEE\requirements.txt
```

### Launch BBoxEE
```bash
cd BBoxEE
python main.py
```
