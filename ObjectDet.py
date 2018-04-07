import os
import logging
import uuid
import configparser
import queue
import threading
import time
import copy
import cv2
import colorsys
import imghdr
import os
import random

import numpy as np
from keras import backend as K
from keras.models import load_model


from ObjectDetect.yad2k.yad2k.models.keras_yolo import yolo_eval, yolo_head
import pickle
import zlib
import types
from BasicPart import BasicPart

# import warnings
# warnings.filterwarnings("ignore")

try:
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
except ImportError:
    raise ImportError('Pillow can not be found!')

class ObjectDet(BasicPart):
    """
        物体识别类
            StartDetectThread(queue, queue_lock)
            
            __Detect(img)

            getProcessedQueueAndLock()
    """

    def __init__(self, 
        logfile   = None, 
        isShow    = False): 
        '''
            useconfig：读取配置文件
            logfile:   日志文件路径
            isShow:    显示图片处理过程
            
        '''
        BasicPart.__init__(self, logfile=logfile, isShow=isShow)
        self.__read_config()
        self.__kerasinit()


    def __read_config(self):
        self.model_path      = self.config.get('yolo','model_path')
        self.anchors_path    = self.config.get('yolo','anchors_path')
        self.classes_path    = self.config.get('yolo','classes_path')
        self.score_threshold = self.config.getfloat('yolo','score_threshold')
        self.iou_threshold   = self.config.getfloat('yolo','iou_threshold')
        self.font            = self.config.get('yolo','font')

    def __kerasinit(self):
        

        # Read classes name
        with open(self.classes_path) as f:
            class_names = f.readlines()
        self.class_names = [c.strip() for c in class_names]

        # Read anchor file
        with open(self.anchors_path) as f:
            self.anchors = f.readline()
            self.anchors = [float(x) for x in self.anchors.split(',')]
            self.anchors = np.array(self.anchors).reshape(-1, 2)

        # Load Model    
        self.yolo_model = load_model(self.model_path)
        
        # plot_model(yolo_model, to_file='model.png')
        # Verify model, anchors, and classes are compatible
        self.num_classes = len(self.class_names)
        self.num_anchors = len(self.anchors)

        self.model_output_channels = self.yolo_model.layers[-1].output_shape[-1]
        assert self.model_output_channels == self.num_anchors * (self.num_classes + 5), \
            'Mismatch between model and given anchor and class sizes. ' \
            'Specify matching anchors and classes with --anchors_path and ' \
            '--classes_path flags.'
        if self.isShow: 
            logging.info('{} model, anchors, and classes loaded.'.format(self.model_path))

        # Check if model is fully convolutional, assuming channel last order.
        self.model_image_size = self.yolo_model.layers[0].input_shape[1:3]
        
        self.is_fixed_size = self.model_image_size != (None, None)

        if self.isShow:
            # Generate colors for drawing bounding boxes.
            hsv_tuples = [(x / len(class_names), 1., 1.)
                        for x in range(len(class_names))]
            self.colors = list(map(lambda x: colorsys.hsv_to_rgb(*x), hsv_tuples))
            self.colors = list(
                map(lambda x: (int(x[0] * 255), int(x[1] * 255), int(x[2] * 255)),
                    self.colors))
            random.seed(10101)  # Fixed seed for consistent colors across runs.
            random.shuffle(self.colors)  # Shuffle colors to decorrelate adjacent classes.
            random.seed(None)  # Reset seed to default.

        self.yolo_outputs = yolo_head(self.yolo_model.output, self.anchors, len(self.class_names))
        self.input_image_shape = K.placeholder(shape=(2, ))

        
        self.boxes, self.scores, self.classes = yolo_eval(
            self.yolo_outputs,
            self.input_image_shape,
            score_threshold = self.score_threshold,
            iou_threshold   = self.iou_threshold)
        logging.info("KERAS INIT OVER")


    def __PreProcess(self, img_array_data):
        """将数组型图片数据转换为网络输入的格式
        
        Arguments:
            img_array_data {narray} -- 数组型图片数据
        """
        image = Image.fromarray(cv2.cvtColor(img_array_data,cv2.COLOR_BGR2RGB))  
        if self.is_fixed_size:
            resized_image = image.resize(
                tuple(reversed(self.model_image_size)), Image.BICUBIC)
            image_data = np.array(resized_image, dtype='float32')
        else:
            # Due to skip connection + max pooling in YOLO_v2, inputs must have
            # width and height as multiples of 32.
            new_image_size = (image.width - (image.width % 32),
                            image.height - (image.height % 32))
            resized_image  = image.resize(new_image_size, Image.BICUBIC)
            image_data     = np.array(resized_image, dtype = 'float32')
        image_data /= 255.
        image_data = np.expand_dims(image_data, 0)  # Add batch dimension.
        return image, image_data        

    def __Detection(self, name, img):
        # 处理图片, 返回feature和tag信息
        logging.info("__Detection__Detection__Detection__Detection__Detection__Detection")
        image, image_data = self.__PreProcess(img)
        print("image: "+str(type(image)))
        print("image_data: "+str(type(image_data)))
        print("image.size" + str(image.size))
        print("image_data.size" + str(image_data.size))
        
        sess = K.get_session()
        out_boxes, \
        out_scores, \
        out_classes, \
        model_features = sess.run(
        [self.boxes, self.scores, self.classes, self.yolo_model.output],
        feed_dict={
            self.yolo_model.input: image_data,
            self.input_image_shape: [image.size[1], image.size[0]],
            K.learning_phase(): 0
        })
        image_tag_name           = np.choose(out_classes, self.class_names)

        image_obj_dic            = {}
        image_obj_dic['boxes']   = out_boxes
        image_obj_dic['scores']  = out_scores
        image_obj_dic['classes'] = image_tag_name
        image_obj_dic['feat']    = model_features
        if self.isShow:
            logging.info('Found {} boxes for {}'.format(len(out_boxes), name))
            font = ImageFont.truetype(
                    font=self.font,
                    size=np.floor(3e-2 * image.size[1] + 0.5).astype('int32'))
            thickness = (image.size[0] + image.size[1]) // 300
            
            true_images_classes.append(out_classes)

            for i, c in reversed(list(enumerate(out_classes))):
                predicted_class = class_names[c]
                box             = out_boxes[i]
                score           = out_scores[i]

                label           = '{} {:.2f}'.format(predicted_class, score)

                draw       = ImageDraw.Draw(image)
                label_size = draw.textsize(label, font)

                top, left, bottom, right = box
                top                      = max(0, np.floor(top + 0.5).astype('int32'))
                left                     = max(0, np.floor(left + 0.5).astype('int32'))
                bottom                   = min(image.size[1], np.floor(bottom + 0.5).astype('int32'))
                right                    = min(image.size[0], np.floor(right + 0.5).astype('int32'))
                print(label, (left, top), (right, bottom))

                if top - label_size[1] >= 0:
                    text_origin = np.array([left, top - label_size[1]])
                else:
                    text_origin = np.array([left, top + 1])

                # My kingdom for a good redistributable image drawing library.
                for i in range(thickness):
                    draw.rectangle(
                        [left + i, top + i, right - i, bottom - i],
                        outline=self.colors[c])
                draw.rectangle(
                    [tuple(text_origin), tuple(text_origin + label_size)],
                    fill=self.colors[c])
                draw.text(text_origin, label, fill=(0, 0, 0), font=font)
                del draw

        return image_obj_dic

    def __process(self, item):
        
        
        if 'name' not in item.keys():
            if item['isIN']:
                name = str(item['id']) + "_IN_"
            else:
                name = str(item['id']) + "_OUT"
            item['name'] = name
        
        result = self.__Detection(item['name'], item['data'])
        # 加入处理结果队列
        item['image_obj_dic'] = image_obj_dic
        self.output_queue.put(item)
        
    def startThread(self, input_queue, input_lock):
        logging.info('startThread startThread startThread startThread')
        self.input_Queue = input_queue
        self.input_over_lock = input_lock
        threading.Thread(target=self.__process_thread).start()

    def __process_thread(self):
        isProcessOver = False
        # 跳出循环条件：处理结束且队列为空
        while not self.input_Queue.empty() or not isProcessOver:
            # 非阻塞
            item = None
            try:
                item = self.input_Queue.get(False)
            except queue.Empty:
                if isProcessOver:
                    break
                else:
                    time.sleep(0.1)
            # 处理  
            self.__process(item)

            # 处理结束
            if self.input_over_lock.acquire(False):
                isProcessOver = True
        # 完毕
        self.out_over_lock.release()

    def __del__(self):
        '''
            释放资源
        '''
        # self.sess.close()
    
if __name__ == '__main__':
    from VideoSample import VideoSample
    vname         = "Data/Videos/20170701_small.mp4"
    vsample       = VideoSample(isShow = True)
    sceneQ, QLock = vsample.sample(vname)

    s_time = time.time()
    od = ObjectDet(isShow=False)
    output_queue, out_over_lock = od.getOutputQueueAndLock()
    od.startThread(sceneQ, QLock)
    isProcessOver = False
    # 跳出循环条件：处理结束且队列为空
    while not output_queue.empty() or not isProcessOver:
        # 非阻塞
        try:
            sceneitem = output_queue.get(False)
            print(sceneitem['image_obj_dic']['classes'])
            print(sceneitem['name'])
            
        except queue.Empty:
            if isProcessOver:
                break
            else:
                time.sleep(0.1)
        # 处理结束
        if out_over_lock.acquire(False):
            isProcessOver = True
    e_time = time.time()

    print("OD: time = "+str(e_time - s_time))
