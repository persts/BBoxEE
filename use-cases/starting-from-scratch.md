# Starting a New Camera Trapping Project

Taylor is starting a new camera trapping initiative monitoring Fisher Cats and has just returned from the field with 10 micro SD cards full of images. Taylor is interested in training an object detection model to help automate future sorting and labeling of images from the camera traps.

As Taylor is just starting, they are using the computer file system as a pseudo database. Taylor creates a project directory with sub directories for each camera. For each SD card, Taylor creates a new directory in the corresponding camera's directory naming the new directory with the date the card was pulled and then copies the images from SD card into that directory.

Taylor's cameras were set to trigger when something walked in front of the camera but also to take images at regular intervals, which has resulted in tens of thousands images, most of them not containing and animal. Taylor's main objective at this initial stage of the project is to create labeled bounding boxes to train an object detector, not to fully review all of the image data. So Taylor decides to leverage an existing model, Microsoft AI4Earth's [MegaDetector](https://github.com/microsoft/CameraTraps/blob/master/megadetector.md), and the automated annotation functionality in BBoxEE to filter out the blank images so they can focus on images containing animals.

Taylor launches BBoxEE and selects the first directory of images they are going to work on. Taylor then loads MegaDetector by clicking the ***Select Model*** button in the Automated Annotation panel and sets a threshold of 0.6 before clicking the ***Annotate*** button. While Taylor's workstation has a very good GPU, MegaDetector is a relatively slow, but pretty accurate, model and Taylor decides to head home for the evening while the initial bounding boxes are generated. 

When Taylor arrives in the morning they can see that the annotation process has completed. Taylor's next task is to review all of the bounding boxes that were automatically generated. Reviewing entails adjusting the bounding box edges when needed, deleting false positive detections, adding possible missed detections when multiple animals are in an image or are very close to each other, and assigning an actual label; MegaDetector can only label detections as *animal, person,* or *vehicle*.

Taylor does not need to systematically step through each image, they can simply press **Shift** + **Space Bar** to jump to the first/next image with a bounding box, thereby skipping all of the potentially blank images in-between and saving time.

Taylor spends the next several days generating and reviewing bounding boxes for the remaining data. When all of the bounding boxes have been reviewed, Taylor exports the images and bounding boxes into multiple shards and starts training a model of their choice. While the model is training, Taylor can now go back and review all of the data to see if there were any false negatives from the initial bounding box generation process.

After the next collection event occurs, Taylor will repeat the bounding box generation and review process using their newly trained model and the new data. 

This process is repeated until a production level model has been achieved. 

