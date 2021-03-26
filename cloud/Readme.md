# Cloud based assisted annotation

You can use the scripts in this directory if would like to use the assisted annotation functionality of BBoxEE on a bunch of image directories or on a cloud based platform like AWS or Azure. 

These annotation scripts will recursively process all directories contained with in the root "data" directory.

## Tensorflow 2.4 on Ubuntu 20.04

Follow the [TensorFlow GPU instrucitons](https://www.tensorflow.org/install/gpu) if you need to install the required NVIDIA and CUDA libraries.


```bash
sudo apt install python3-venv
mkdir pythonenv
python3 -m venv pythonenv/bboxee
source pythonenv/bboxee/bin/activate
python -m pip install --upgrade pip
python -m pip install --upgrade pillow
python -m pip install tqdm
python -m pip install numpy
python -m pip install tensorflow
```

### Usage
```bash
python annotate_frozen.py ./images ./models/md_v4.1.0.pb ./models/label_map.pbtxt 0.8

of

python annotate_saved.py ./images ./models/saved_model/ ./models/label_map.pbtxt 0.8
```

Sit back and wait for your .bbx files to be created.