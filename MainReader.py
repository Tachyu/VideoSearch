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

import pickle
from DBHandler import DBHandler
from VideoSample import VideoSample
from BasicPart import BasicPart

class MainReader(BasicPart):
    """视频入库主入口程序
    """
    def __init__(self, 
        videoinfo, 
        logfile=None, 
        isShow=False):
        """初始化
        
        Arguments:
            videoinfo {视频信息} -- {'name','datetime','descrption'}
        
        Keyword Arguments:
            logfile {string} -- 可选，log文件名 (default: {None})
            isShow {bool} -- 是否显示处理过程 (default: {False})
        """
        BasicPart.__init__(self, logfile, isShow)
        self.videoinfo = videoinfo
        self.__mkdirs()
        self.dbhandler = DBHandler()
        self.save_video()
        self.item_list = []
        pass

    def read_config(self):
        # content          = Data/Content
        # content_feat     = Data/Content/Feats
        # faces            = Data/Faces
        # facesfeat        = Data/Faces/Feats
        # facessample      = Data/Faces/Samples
        # objects          = Data/Objects
        self.group               = self.config.getint('database','group')
        self.dir                 = {}
        self.dir['content']      = self.config.get('datadir','content')
        self.dir['content_feat'] = self.config.get('datadir','content_feat')
        self.dir['faces']        = self.config.get('datadir','faces')
        self.dir['faces_feat']   = self.config.get('datadir','faces_feat')
        self.dir['faces_sample'] = self.config.get('datadir','faces_sample')
        self.dir['objects']      = self.config.get('datadir','objects')
        
    def __mkdirs(self):
        """创建Data目录下各个目录
        """
        for d in self.dir.values():
            if not os.path.exists(d):
                os.mkdir(d)
            

    def __init_pipeline(self):
        s_time = time.time()        
        process_line = []
        from ObjectDet import ObjectDet
        process_line.append(ObjectDet(isShow=self.isShow, picShow=False))

        from FaceRecog import FaceRecog
        process_line.append(FaceRecog(isShow=self.isShow, picShow=False))

        self.videosample = VideoSample(isShow = self.isShow, save_images = True)
        i_queue, i_lock  = self.videosample.sample(self.videoinfo['name'])
        
        self.s_time = time.time()
        for processer in process_line:
            processer.startThread(i_queue,i_lock)
            i_queue, i_lock = processer.getOutputQueueAndLock()
        return i_queue, i_lock

    def process(self, item):
        self.item_list.append(item)

    def process_faces_thread(self):
        # 存储与处理人脸信息的线程
        # 数据库存储， addmanyFaceFeats
        self.lg("save_face")                
        faces_num    = 0 # 视频中全部人脸数目
        # personids 暂定为全部None
        face_feat_dic_list = []       
        for index, item in enumerate(self.item_list):
            cur_face_num   = len(item['face_result']['feats'])
            if cur_face_num == 0:
                continue
            cur_pic_id   = self.db_picid_list[index]            
            cur_pic_list = [cur_pic_id] * cur_face_num
            cur_person_ids = [None] * cur_face_num              
            # 提交数据库   
            cur_db_faceid = self.dbhandler.addmanyFaceFeats(cur_pic_list, cur_person_ids)
            faces_num += cur_face_num

            for index, feat in enumerate(item['face_result']['feats']):
                ff_dic = {}
                ff_dic['ffid'] = cur_db_faceid[index]
                ff_dic['feat'] = feat
                # 存储到特征列表
                face_feat_dic_list.append(ff_dic)
        
        # 保存特征文件
        self.__store_feat(self.dir['faces_feat'], 'ff', face_feat_dic_list)    
        # 完成
        self.face_finish_lock.release()
    
    def process_pic_thread(self):
        # 存储与处理图片特征信息的线程,
        # 第一个步骤，之后才可以存储人脸和物体
        # 数据库存储， addmanyPicFeats
        self.lg("save_pics")                
        picfeat_dic_list = []
        pic_scene_list   = []
        pic_id_list      = []  
        pic_feat_list    = []                    
        for item in self.item_list:
            cur_scene_id  = self.db_scene_id[item['id']]
            pic_scene_list.append(cur_scene_id)
            pic_feat_list.append(item['image_obj_dic']['feat'])
                          
        # 提交数据库
        self.db_picid_list = self.dbhandler.addmanyPicFeats(pic_scene_list)
        # 可以处理其他信息了
        self.db_picid_lock.release()
        
        for index, feat in enumerate(pic_feat_list):
            sf_dic = {}
            sf_dic['sfid'] = self.db_picid_list[index]
            sf_dic['feat'] = feat
            # 存储到特征列表
            picfeat_dic_list.append(sf_dic)
        
        # 保存特征文件
        self.__store_feat(self.dir['content_feat'], 'sf', picfeat_dic_list)    
        pass

    def process_obj_thread(self):
        # 存储与处理物体信息的线程
        # 不涉及数据库存储
        self.lg("save_objs")        
        obj_dic_list = []                
        for index, item in enumerate(self.item_list):
            cur_pic_id  = self.db_picid_list[index]
            obj_dic = {}
            obj_dic['picid'] = cur_pic_id
            obj_dic['objs']  = item['image_obj_dic']['tag_name']
            obj_dic['boxes'] = item['image_obj_dic']['boxes']
            obj_dic_list.append(obj_dic)

        # 保存文件
        self.__store_feat(self.dir['objects'], 'ob', obj_dic_list) 
        # 完成
        self.obj_finish_lock.release()   
        pass
   
    def __store_feat(self, dirname, feat_type, data):
        filename = str(self.videoinfo['id']) + '_' + feat_type + '.pkl' 
        filename = os.path.join(dirname, filename)
        with open(filename, 'wb') as f:
            pickle.dump(data, f)
        self.lg(filename +" is stored")
        pass

    def save_scene(self):
        """数据库中存储场景信息, 建立场景id与数据库场景id的映射
            self.db_scene_id[i] <- self.scene_id[i] = i
        """
        self.lg("save_scene")                                                                                                                                                                                       
        sceens_id,starttime,length = self.videosample.getSceneInfo()                                                                                                                                                                                                                                                                                                                                                                         
        numSceens = len(sceens_id)
        videoids = [self.videoinfo['id']] * numSceens
        self.db_scene_id = self.dbhandler.addmanySceneInfo(videoids, starttime, length)
        pass

    def save_video(self):
        """数据库中存储视频信息
        """
        self.videoinfo['id'] = self.dbhandler.addVideoInfo(
            self.videoinfo[                                                                                                                                                                                                                                                                                                                                                                 'name'], 
            self.videoinfo['descrption'])                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
        self.dbhandler.commit()
        self.lg("Video: %s has been stored in database, id=%d."
        %(self.videoinfo['name'],self.videoinfo['id']))

    def store_procedure(self):
        self.db_picid_lock = threading.Lock()
        self.face_finish_lock = threading.Lock()
        self.obj_finish_lock = threading.Lock()
        
        # 存储场景
        self.save_scene()

        # 存储pic
        self.db_picid_lock.acquire()        
        threading.Thread(target=self.process_pic_thread()).start()
        self.db_picid_lock.acquire()

        # 存储人脸
        self.face_finish_lock.acquire()
        threading.Thread(target=self.process_faces_thread()).start()

        # 存储物体
        self.obj_finish_lock.acquire()
        threading.Thread(target=self.process_obj_thread()).start()

        # 等待结束
        self.obj_finish_lock.acquire()
        self.face_finish_lock.acquire()
        pass

    def after_process(self):
        self.e_time = time.time()
        self.lg("OD+FR: time = "+str(self.e_time - self.s_time))
        self.lg("[START] Store procedure.")
        self.store_procedure()
        self.lg("[OVER]  Store procedure.")
        
    def start(self):
        input_queue, input_lock = self.__init_pipeline()
        self.startThread(input_queue, input_lock)

        

if __name__ == "__main__":
    # main("Data/Videos/20170701_small.mp4",isShow=False).start()
    videoinfo = {}
    videoinfo['name'] = "Data/Videos/20170825.mp4"
    des = ''
    with open('Data/Videos/Descriptions/20170825.txt','r') as df:
        des = df.read()
    videoinfo['descrption'] = des
    MainReader(videoinfo,isShow=True).start()
    