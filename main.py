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
import pickle
import zlib
import types
from queue import Queue

from ObjectDet import ObjectDet
from FaceRecog import FaceRecog
from DBHandler import DBHandler

class main:
    """主入口程序
    """
    def __init__(self, videoname):
        self.videoname = videoname
        self.__mkdirs()
        pass

    def __mkdirs(self):
        """创建Data目录下各个目录
        """
        dirs = [
            'Data/Content',
            'Data/Content/Feats',
            'Data/Faces',
            'Data/Faces/Feats',
            'Data/Faces/Samples']
        for d in dirs:
            if not os.path.exists(d):
                os.mkdir(d)

    def start(self):
        vsample       = VideoSample(isShow = False)
        sceneQ, sceneLock = vsample.sample(self.videoname)
        s_time = time.time()

        # 物体识别
        od = ObjectDet(isShow=False)
        od.startThread(sceneQ, sceneLock)
        od_output_queue, od_over_lock = od.getOutputQueueAndLock()

        # 人脸识别
        fr = FaceRecog(isShow=False)
        fr.startThread(od_output_queue, od_over_lock)
        fr_output_queue, fr_over_lock = fr.getOutputQueueAndLock()

        isProcessOver = False
        # 跳出循环条件：处理结束且队列为空
        while not fr_output_queue.empty() or not isProcessOver:
            # 非阻塞
            try:
                sceneitem = fr_output_queue.get(False)
                # print(sceneitem['image_obj_dic']['classes'])
                # print(sceneitem['name'])
                
            except queue.Empty:
                if isProcessOver:
                    break
                else:
                    time.sleep(0.1)
            # 处理结束
            if fr_over_lock.acquire(False):
                isProcessOver = True
        e_time = time.time()

        print("OD+FR: time = "+str(e_time - s_time))

if __name__ == "__main__":
    main("Data/Videos/20170701_small.mp4").start()