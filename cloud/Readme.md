# Cloud based assisted annotation

You can use the scripts in this folder if would like to use the assisted annotation functionality of BBoxEE on a bunch of image folders or on a cloud based platform like AWS or Azure. 

These annotation scripts will recursively process all directories contained with in the root "data" directory.

## Tensorflow 1.15 on Ubuntu 18.04

Follow the [TensorFlow GPU instrucitons](https://www.tensorflow.org/install/gpu) if you need to install the required NVIDIA and CUDA libraries. Tested with CUDA Toolkit 10.0 and cuDNN 7.6.


```bash
sudo apt install python3-venv
mkdir pythonenv
python3 -m venv pythonenv/bboxee
source pythonenv/bboxee/bin/activate
pip install --upgrade pip
pip install --upgrade pillow
pip install tqdm
pip install numpy
pip install tensorflow-gpu==1.15
```

### Usage
Upload your data, model, label_map.pbtxt, and annotate_tf_1x.py to your working directory.

```bash
python3 annotate_tf_1x.py ./images ./models/md_v4.1.0.pb ./models/label_map.pbtxt 0.8
```

Sit back and wait for your .bbx files to be created.