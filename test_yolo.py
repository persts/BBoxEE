import torch
import cv2

from andenet import schema

from models import Darknet
from utils.parse_config import parse_data_config
from utils.utils import load_classes, non_max_suppression
from utils.datasets import load_images

DATA_CONFIG = '/home/pete/devel/python/yolov3/andenet/cfg/andenet.data'
NET_CONFIG = '/home/pete/devel/python/yolov3/andenet/cfg/yolov3.cfg'
WEIGHTS = '/home/pete/devel/python/yolov3/andenet/weights/best.pt'
IMG_SIZE = 416

device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
data_config = parse_data_config(DATA_CONFIG)
model = Darknet(NET_CONFIG, IMG_SIZE)

checkpoint = torch.load(WEIGHTS, map_location='cpu')
model.load_state_dict(checkpoint['model'])

model.to(device).eval()

def scale_detections(image, detections):
    img = cv2.imread(image)
    # The amount of padding that was added
    pad_x = max(img.shape[0] - img.shape[1], 0) * (img_size / max(img.shape))
    pad_y = max(img.shape[1] - img.shape[0], 0) * (img_size / max(img.shape))
    # Image height and width after padding is removed
    unpad_h = img_size - pad_y
    unpad_w = img_size - pad_x

    entry = schema.annotation_file_entry()
    for x1, y1, x2, y2, conf, cls_conf, cls_pred in detections:
        annotation = schema.annotation()
        annotation['created_by'] = 'machine'
        # Rescale coordinates to original dimensions
        box_h = ((y2 - y1) / unpad_h) * img.shape[0]
        box_w = ((x2 - x1) / unpad_w) * img.shape[1]
        y1 = (((y1 - pad_y // 2) / unpad_h) * img.shape[0]).round().item()
        x1 = (((x1 - pad_x // 2) / unpad_w) * img.shape[1]).round().item()
        x2 = (x1 + box_w).round().item()
        y2 = (y1 + box_h).round().item()
        x1, y1, x2, y2 = max(x1, 0), max(y1, 0), max(x2, 0), max(y2, 0)
        annotation['bbox']['xmin'] = x1 / img.shape[1]
        annotation['bbox']['xmax'] = x2 / img.shape[1]
        annotation['bbox']['ymin'] = y1 / img.shape[0]
        annotation['bbox']['ymax'] = y2 / img.shape[0]
        annotation['label'] = classes[int(cls_pred.item())]
        entry['annotations'].append(annotation)
    return entry


img_size = 416
conf_thres = 0.3
nms_thres = 0.45
classes = load_classes(data_config['names'])  # Extracts class labels from file
dataloader = load_images('/home/pete/devel/python/yolov3/andenet/sample/', batch_size=1, img_size=img_size)
for i, (img_path, img) in enumerate(dataloader):
    with torch.no_grad():
        img = torch.from_numpy(img).unsqueeze(0).to(device)
        pred = model(img)
        pred = pred[pred[:, :, 4] > conf_thres]

        if len(pred) > 0:
            detections = non_max_suppression(pred.unsqueeze(0), conf_thres, nms_thres)
            entry = scale_detections(img_path[0], detections[0])
        print(entry)
    break
