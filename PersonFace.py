import os
import logging
import uuid
import configparser
import queue
import threading
import time
import copy
import cv2

import numpy as np
from BasicPart import BasicPart

try:
    from PIL import Image, ImageDraw
    import numpy as np
except ImportError:
    raise ImportError('Pillow can not be found!')

class PersonFace(BasicPart):
    """PersonFace，人物人脸录入及比对模块
    Arguments:
        BasicPart {[type]} -- [description]
    """
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
        from DBHandler import DBHandler
        self.handler = DBHandler()        
        # self.initFR()
        # self.initFI()        

    def initFI(self):
        """初始化索引模块
        """
        from FeatureIndex import FeatureIndex
        prefix = 'Person'
        self.fi = FeatureIndex(index_prefix=prefix,isShow = self.isShow)    
    
    def initFR(self):
        """初始化人脸特征提取模块
        """
        from FaceRecog import FaceRecog
        self.fr = FaceRecog(isShow = self.isShow, picShow = self.picShow)

    def read_config(self):
        """读配置文件
        """
        self.dir = {}
        self.thresh = self.config.getint('facerecog','threshold')
        self.dir['faces']        = self.config.get('datadir','faces')
        self.dir['faces_feat']   = self.config.get('datadir','faces_feat')
        self.dir['faces_sample'] = self.config.get('datadir','faces_sample')
    
    def storePersonToDB(self):
        """将人物存到PersonInfo表，返回id
        """
        self.person_ids = self.handler.addmanyPesons(self.person_names)

    def index_person(self):
        """对sample文件夹下所有人物人脸图片建立索引
        """
        person_list  = []
        self.person_names   = os.listdir(self.dir['faces_sample'])
        # 存数据库，获取id
        self.storePersonToDB()
        self.person_pic_feats = []
        self.person_pic_ids   = []
        
        for index, person_name in enumerate(self.person_names):
            # 每一个人物对应一个文件夹
            full_path = sample_dir + '/' + person_name

            pic_list = os.listdir(full_path)
            num_faces = len(pic_list)
            self.lg('detecting %s: find %d pictures'%(person_name, num_faces))
            for face_pic in pic_list:
                face_pic = full_path + '/' + face_pic
                pic_face_dic = self.fr.extract_image_face_feature(face_pic)
                feat = pic_face_dic['feats'][0]
                self.person_pic_feats.append(feat)
                self.person_pic_ids.append(self.person_ids[index])
        
        # 建立索引
        self.initFI()
        self.fi.create_person_index(self.person_feats, self.person_ids)

    def setFeatureIndex(self, fi):
        """设置FI对象，用于查询时，从外部导入已载入索引的索引对象
        
        Arguments:
            fi {FeatureIndex} -- 索引检索对象
        """
        self.fi = fi

    def idenity(self, facefeat):
        """确定人物身份，返回人物名及人物id
        
        Arguments:
            facefeat {data} -- 待确定的人脸特征
        """
        # 首先进行query
        results = self.fi.queryPerson(facefeat)

        # 确定人物身份:
        # 加权计算每个人物的分数[0.55, 0.5, 0.45, 0.4, 0.35,...]
        score_weight = [0.55 - i * 0.05 for i in range(10)]
        score        = [w * s for s in results]
        
        # 计算每个结果的得分
        

        return personid, personname

if __name__ == '__main__':
    PersonFace(isShow=True).index_person()