# Bounding Box Editor and Exporter (BBoxEE)

BBoxEE is a open-source tool for annotating bounding boxes and exporting data to training object detectors. BBoxEE was specifically developed for the [Animal Detection Network (Andenet)](http://biodiversityinformatics.amnh.org/ml4conservation/animal-detection-network/) initiative, however, it is not limited to annotating camera trap data and can be used for any bounding box annotation task.

BBoxEE is actively under development by Peter Ersts of the [Center for Biodiversity and Conservation at the American Museum of Natural History](https://www.amnh.org/our-research/center-for-biodiversity-conservation). Additional documentation will be forthcoming.

------
## Quick Start Guide
We have put together a [quick start guide](https://github.com/persts/BBoxEE/blob/master/doc/Quick%20Start%20Guide.pdf). This quick start guide is intended to introduce the basic functionality of BBoxEE. It is not intended to be a comprehensive user guide. Additional documentation will follow.

------
## Installation

### Dependencies
BBoxEE is being developed with Python 3.8.10 on Ubuntu 20.04 with the following libraries:

* PyQt6 (6.3.1)
* Pillow (9.2.0)
* Numpy (1.23.2)
* Tabulate (0.8.10)
* TensorFlow (2.10.0)
* Torch (1.12.1+cu113)

Build a virtual environment and install the dependencies:
```bash
cd [Your BBoxEE Workspace]

[Linux]
python -m venv bboxee-env
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
### YOLO5 (Torch) Support
Clone the YOLO5 repo and install dependencies
```bash
cd [Your BBoxEE Workspace]

[Linux]
git clone https://github.com/ultralytics/yolov5 YOLO5
python -m pip install -r YOLO5/requirements.txt
export PYTHONPATH=$PYTHONPATH:[Your BBoxEE workspace]/yolov5

[Windows]
git clone https://github.com/ultralytics/yolov5 YOLO5
python -m pip install -r YOLO5\requirements.txt
set PYTHONPATH=%PYTHONPATH%;[Your BBoxEE workspace]\yolov5
```
### Note about YOLO5 support
Some models may not work with the newest versions of Torch. If you get an exception when trying to use a model that looks similar to the messages below, 

```code
File "___lib/python3.8/site-packages/torch/nn/modules/upsampling.py", line 154, in forward
    recompute_scale_factor=self.recompute_scale_factor)

File "___/lib/python3.8/site-packages/torch/nn/modules/module.py", line 1207, in __getattr__
    raise AttributeError("'{}' object has no attribute '{}'".format(
```
You can upgrade your existing model with the following code as a template.
```bash
import torch

ckpt = torch.load('model.0.1.pt')
for m in ckpt['model'].modules():
    if type(m) is torch.nn.Upsample:
        m.recompute_scale_factor = None
torch.save(ckpt, './model.0.2.pt')
```
**At the time of writing this, M1 GPU (MPS) support is only available with PyTorch >= v1.13, which has to be installed from the nighly builds.
```bash
pip3 install --pre torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/nightly/cpu
```
