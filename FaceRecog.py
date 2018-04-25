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
            处理后item格式:
             {'id','isIN', '','face_result':}
             pic_face_dic['landmarks'] = lands
             pic_face_dic['feats']     = feats
            startThread(queue, queue_lock)
            人脸识别队列

            getProcessedQueueAndLock()
            返回处理完毕图片存放的队列和锁
    """
    images_name = []

    def __init__(self, 
        threshold = None, 
        logfile   = None,
        picShow   = False,          
        isShow    = False): 
        '''
            threshold: 人脸大小阈值
            logfile:   日志文件路径
            isShow:    显示图片处理过程
            
        '''
        BasicPart.__init__(self, logfile=logfile, isShow=isShow)
        self.picShow  = picShow
        self.detector = Detector()
        self.aligner = Aligner()
        self.identifier = Identifier()
        # self.thresh = self.config.getint('facerecog','threshold')
        if threshold != None:
            self.thresh = threshold
        
        self.detector.set_min_face_size(self.thresh)

    def read_config(self):
        """读配置文件
        """
        self.thresh = self.config.getint('facerecog','threshold')

    def __Recognation(self, name, img=None):
        # 处理图片, 返回feature和landmark信息
        if img is not None: # 从视频中传来的
            image = Image.fromarray(cv2.cvtColor(img,cv2.COLOR_BGR2RGB))
        else:
            image = Image.open(name)

        lands, faces, feats = self.__extract_features(image) 
        self.lg("detecting %s: find %d faces"%(name, len(lands))) 
        if self.picShow:
            draw = ImageDraw.Draw(image)
            for i, face in enumerate(faces):
                draw.rectangle([face.left, face.top, face.right, face.bottom], outline='red') 
            image.show()
        pic_face_dic = {}
        pic_face_dic['landmarks'] = lands
        pic_face_dic['feats']     = feats
        return pic_face_dic



    def extract_image_face_feature(self, imagename):
        
        '''
            pic_face_dic['landmarks'] = lands
            pic_face_dic['feats']     = feats
        '''
        pic_face_dic = self.__Recognation(imagename)
        return pic_face_dic

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
            # 降维至一维数组
            feat = np.array(feat).flatten()
            feats.append(feat)
        return landmarks, faces, feats 
    
    def __del__(self):
        '''
            释放资源
        '''
        self.detector.release()
        self.aligner.release()
        self.identifier.release()
   
    def process(self, item):
        # 重写处理方法 
        if item != None:
            if 'name' not in item.keys():
                if item['isIN']:
                    name = str(item['id']) + "_IN_"
                else:
                    name = str(item['id']) + "_OUT"
                item['name'] = name
            result = self.__Recognation(item['name'], item['data'])
        
            # 加入处理结果队列
            item['face_result'] = result
            self.output_queue.put(item)
        else:
            logging.warn("FaceRecog.process: NONE!")




if __name__ == '__main__':
    from VideoSample import VideoSample
    vname         = "Data/Videos/20170701_small.mp4"
    vsample       = VideoSample(isShow = True)
    sceneQ, sceneLock = vsample.sample(vname)

    s_time = time.time()

    recog = FaceRecog(isShow=True)
    output_queue, out_over_lock = recog.getOutputQueueAndLock()
    recog.startThread(sceneQ, sceneLock)
    time.sleep(3)
    # isProcessOver = False
    # # 跳出循环条件：处理结束且队列为空
    # while not output_queue.empty() or not isProcessOver:
    #     # 非阻塞
    #     try:
    #         sceneitem = output_queue.get(False)
    #         # print(sceneitem['id'])
    #     except queue.Empty:
    #         if isProcessOver:
    #             break
    #         else:
    #             time.sleep(0.1)
    #     # 处理结束
    #     if out_over_lock.acquire(False):
    #         isProcessOver = True
    e_time = time.time()
    print("Face: time = "+str(e_time - s_time))

