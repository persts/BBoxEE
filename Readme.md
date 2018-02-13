# Animal Detection Network (Andenet)

The goal of Andenet is to provide a standardized dataset to be used as a baseline for developing and evaluating deep machine learning pipelines for projects interested in automatically detecting and labeling animals in trail camera (camera trap) archives.

Andenet-Desktop is a suite of tools for annotating, preparing, and exploring training data from trail cameras (camera traps).

Andenet is actively under development by Peter Ersts and Ned Horning of the [Center for Biodiversity and Conservation at the American Museum of Natural History](https://www.amnh.org/our-research/center-for-biodiversity-conservation). Additional documentation will be forthcoming.

## Installation

### Dependencies

Andenet is being developed on Ubuntu 16.04 with the following libraries:

* PyQt5 (5.5.1)
* TKinter (3.5.1)
* Protobuf (3.5.1)
* Pillow (4.2.1)
* lxml (3.5.0)
* TensorFlow (1.4.1)
* tf Slim (which is included in the "tensorflow/models/research/" checkout)

Install GUI libraries:

``` bash
sudo apt install python3-pyqt5 python3-tk
```

Install pip3 matplotlib and upgrade dependencies:

```bash
sudo apt install python3-pip
sudo -H pip3 install --upgrade pip
sudo -H pip3 install --upgrade pillow
sudo -H pip3 install --upgrade lxml
sudo -h pip3 install matplotlib
```

For detailed steps to install TensorFlow, follow the [TensorFlow installation instructions](https://www.tensorflow.org/install/). A typical user can install Tensorflow using one of the following commands:

``` bash
# For CPU
sudo -H pip3 install tensorflow
# For GPU
sudo -H pip3 install tensorflow-gpu
```
Clone TensorFlow's models repo:

``` bash
git clone https://github.com/tensorflow/models
```
### Protobuf Compilation

The TensorFlow Object Detection API uses Protobufs to configure model and training parameters. Before the framework can be used, the Protobuf libraries must be compiled. This should be done by running the following command from the models/research/ directory:


``` bash
sudo apt install protobuf-compiler
# From models/research/
protoc object_detection/protos/*.proto --python_out=.
```

### Add Libraries to PYTHONPATH

When running locally, the tensorflow/models/research/ and slim directories should be appended to PYTHONPATH. This can be done by running the following from tensorflow/models/research/:


``` bash
# From tensorflow/models/research/
export PYTHONPATH=$PYTHONPATH:`pwd`:`pwd`/slim:`pwd`/object_detection
```
Note: This command needs to run from every new terminal you start. If you wish to avoid running this manually, you can add it as a new line to the end of your ~/.bashrc file.

## Launching Andenet-Desktop
```bash
git clone https://github.com/persts/andenet-desktop.git
cd andenet-desktop
python3 main.py
```
