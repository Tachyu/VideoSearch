# from pyseeta import Detector
# from pyseeta import Aligner
# from pyseeta import Identifier
from Seeta.pyseeta.detector import Detector
from Seeta.pyseeta.aligner import Aligner
from Seeta.pyseeta.identifier import Identifier
import os
import logging
import uuid
import configparser
import queue
import threading
import time
import copy
import cv2

from BasicPart import BasicPart

try:
    from PIL import Image, ImageDraw
    import numpy as np
except ImportError:
    raise ImportError('Pillow can not be found!')

class FaceRecog(BasicPart):
    """
        人脸识别类
            startThread(queue, queue_lock)
            人脸识别队列

            getProcessedQueueAndLock()
            返回处理完毕图片存放的队列和锁
    """
    images_name = []

    def __init__(self, 
        threshold = None, 
        logfile   = None, 
        isShow    = False): 
        '''
            threshold: 人脸大小阈值
            logfile:   日志文件路径
            isShow:    显示图片处理过程
            
        '''
        BasicPart.__init__(self, logfile=logfile, isShow=isShow)
        self.__read_config()

        self.detector = Detector()
        self.aligner = Aligner()
        self.identifier = Identifier()

        if threshold != None:
            self.thresh = threshold
        
        self.detector.set_min_face_size(self.thresh)

    def __read_config(self):
        """读配置文件
        """
        self.thresh = self.config.getint('facerecog','threshold')

    def __process(self, item):
        # 重写处理方法 
        if item != None:
            if item['isIN']:
                name = str(item['id']) + "_IN_"
            else:
                name = str(item['id']) + "_OUT"
            item['name'] = name
            # print(sceneitem)
            result = self.__Recognation(name, item['data'])
        
            # 加入处理结果队列
            item['face_result'] = result
            self.output_queue.put(item)

    def __Recognation(self, name, img):
        # 处理图片, 返回feature和landmark信息
        image = Image.fromarray(cv2.cvtColor(img,cv2.COLOR_BGR2RGB))
        lands, faces, feats = self.__extract_features(image) 
        if self.isShow:
            logging.info("detecting %s: find %d faces"%(name, len(lands))) 
            draw = ImageDraw.Draw(image)
            for i, face in enumerate(faces):
                draw.rectangle([face.left, face.top, face.right, face.bottom], outline='red') 
            image.show()
        pic_face_dic = {}
        pic_face_dic['landmarks'] = lands
        pic_face_dic['feats']     = feats
        return pic_face_dic

    def detect(self):
        '''
         返回一个字典数组：长度等于图片数。例如：
         [
             {
                 'name':'1.jpg'，
                 'features':[[1,23,...],[2,3,....]],
                 'landmarks':[[1,2,3,4],[5,6,7,8]]                 
              },...
         ]
        '''
        pic_dic_list = []
        for pic in self.images_name:
            image = Image.open(pic).convert('RGB')
            lands, faces, feats = self.__extract_features(image) 
            logging.info("detecting %s: find %d faces"%(pic, len(lands))) 
            if self.isShow:
                draw = ImageDraw.Draw(image)
                for i, face in enumerate(faces):
                    draw.rectangle([face.left, face.top, face.right, face.bottom], outline='red') 
                image.show()
            pic_dic = {}
            pic_dic['name']      = pic
            pic_dic['landmarks'] = lands
            pic_dic['feats']     = feats
            pic_dic_list.append(pic_dic)
        return pic_dic_list


    def __extract_features(self, img):
        # detect face in image
        image_gray = img.convert('L')
        faces = self.detector.detect(image_gray)
                
        feats = []
        landmarks = []
        
        for detect_face in faces:
            landmark = self.aligner.align(image_gray, detect_face)
            landmarks.append(landmark)
            feat = self.identifier.extract_feature_with_crop(img, landmark)
            feats.append(feat)
        return landmarks, faces, feats 
    
    def __del__(self):
        '''
            释放资源
        '''
        self.detector.release()
        self.aligner.release()
        self.identifier.release()
    
if __name__ == '__main__':
    from VideoSample import VideoSample
    vname         = "Data/Videos/20170701_tiny.mp4"
    vsample       = VideoSample(useconfig = True, isShow = True)
    sceneQ, QLock = vsample.sample(vname)

    s_time = time.time()
    recog = FaceRecog(isShow=False)
    output_queue, out_over_lock = recog.getOutputQueueAndLock()
    recog.startThread(sceneQ, QLock)
    isProcessOver = False
    # 跳出循环条件：处理结束且队列为空
    while not output_queue.empty() or not isProcessOver:
        # 非阻塞
        try:
            sceneitem = output_queue.get(False)
            # print(sceneitem)
        except queue.Empty:
            if isProcessOver:
                break
            else:
                time.sleep(0.1)
        # 处理结束
        if out_over_lock.acquire(False):
            isProcessOver = True
    e_time = time.time()
    print("Face: time = "+str(e_time - s_time))

