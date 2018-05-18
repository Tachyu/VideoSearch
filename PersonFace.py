import os
import logging
import uuid
import configparser
import queue
import threading
import time
import copy
import cv2

import pandas as pd
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
        self.initFR()
        # 缓存
        self.dbcache = {}
        # self.initFI()        

    def initFI(self):
        """初始化索引模块
        """
        from FeatureIndex import FeatureIndex
        prefixs = ['Person']
        self.fi = FeatureIndex(index_prefixs=prefixs,isShow = self.isShow)    
    
    def initFR(self):
        """初始化人脸特征提取模块
        """
        from FaceRecog import FaceRecog
        self.fr = FaceRecog(isShow = self.isShow, picShow = self.picShow)

    def read_config(self):
        """读配置文件
        """
        self.dir = {}
        self.maxdistance         = self.config.getint('facerecog','max_distance')
        self.thresh              = self.config.getint('facerecog','threshold')
        self.dir['faces']        = self.config.get('datadir','faces')
        self.dir['faces_feat']   = self.config.get('datadir','faces_feat')
        self.dir['faces_sample'] = self.config.get('datadir','faces_sample')
    
    def storePersonToDB(self):
        """将人物存到PersonInfo表，返回id
        """
        self.person_ids = self.handler.addmanyPerson(self.person_names)

    def index_person(self, person_list = [], prefix="Person"):
        """对sample文件夹下所有人物人脸图片建立索引
            或只建立某个人的索引
        """
        if len(person_list) == 0:
            self.person_names   = os.listdir(self.dir['faces_sample'])
        else:
            self.person_names   = person_list
        # 存数据库，获取id
        self.storePersonToDB()
        self.person_pic_feats = []
        self.person_pic_ids   = []
        
        for index, person_name in enumerate(self.person_names):
            # 每一个人物对应一个文件夹
            full_path = self.dir['faces_sample'] + '/' + person_name

            pic_list = os.listdir(full_path)
            num_faces = len(pic_list)
            for face_pic in pic_list:
                face_pic = full_path + '/' + face_pic
                pic_face_dic = self.fr.extract_image_face_feature(face_pic)
                feat = pic_face_dic['feats'][0]
                self.person_pic_feats.append(feat)
                self.person_pic_ids.append(self.person_ids[index])
        
        # 建立索引
        self.initFI()
        self.fi.create_person_index(self.person_pic_feats, self.person_pic_ids, prefix)

    def setFeatureIndex(self, fi):
        """设置FI对象，用于查询时，从外部导入已载入索引的索引对象
        
        Arguments:
            fi {FeatureIndex} -- 索引检索对象
        """
        self.fi = fi

    def identify_pic_person(self, imagename):
        """确定图片中人物名字以及id
        
        Arguments:
            imagename {string} -- 图片名
        
        Returns:
            personid, personname
        """
        face_dic = self.fr.extract_image_face_feature(imagename)
        if len(face_dic['feats']) > 0:
            personid, personname = self.idenity(face_dic['feats'][0])
        else:
            personid=-1
            personname="无人物"            
        return personid, personname
        # print(result)

    def idenity(self, facefeat):
        """确定人物身份，返回人物名及人物id
        
        Arguments:
            facefeat {data} -- 待确定的人脸特征
            -1, unknown 未识别人物
        """
        # 首先进行query
        results, distance = self.fi.queryPerson(facefeat)

        # 若高于最远距离,则为未知人物,返回None,''
        if distance[0] > self.maxdistance:
            personid = -1
            personname = 'unknown'
        else:            
            # 确定人物身份:
            # kmean
            max_count_id = pd.value_counts(results, sort=True).index[0]
            # 计算每个结果的得分
            personid = int(max_count_id)
            # 首先查询缓存,若miss后再查询数据库
            if personid in self.dbcache.keys():
                personname = self.dbcache[personid]
            else:
                personname = self.handler.queryPersonById(personid)[0][1]
                self.dbcache[personid] = personname
        return personid, personname

if __name__ == '__main__':
    from FeatureIndex import FeatureIndex
    pf = PersonFace(True)
    fi = FeatureIndex(True, person_index_prefixs=["Person"])
    fi.load_person_index()
    pf.setFeatureIndex(fi)
    pid, name = pf.identify_pic_person('/var/www/html/SiteVideo/upload/cap_20171031_001213_01.jpg')
    print(pid)
    print(name)    
    # PersonFace(isShow=True).index_person(person_list=["赵乐际","汪洋","栗战书","俞正声"],prefix="Person2")
    # PersonFace(isShow=True).index_person(person_list=[],prefix="Person")
    