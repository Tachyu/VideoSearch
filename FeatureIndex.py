# coding: utf-8
import sys 

import time 
import math 
import os
import numpy as np
import logging
from BasicPart import BasicPart
import nmslib 
from sklearn.neighbors import NearestNeighbors
import pickle

class FeatureIndex(BasicPart):
    """索引建立，读取，检索类
    
    Arguments:
        BasicPart {BasicPart} -- 父类
    """
    def __init__(self, 
        index_prefix='test',
        logfile=None, 
        isShow=False):
        BasicPart.__init__(self, logfile, isShow)
        self.isfaceLoad = False
        self.iscontLoad = False
        self.ispersLoad = False        
        self.index_prefix = index_prefix
        pass
    
    def read_config(self):
        self.dir                  = {}
        self.dir['content']       = self.config.get('datadir','content')
        self.dir['content_feat']  = self.config.get('datadir','content_feat')
        self.dir['faces']         = self.config.get('datadir','faces')
        self.dir['faces_feat']    = self.config.get('datadir','faces_feat')
        self.dir['faces_sample']  = self.config.get('datadir','faces_sample')
        self.dir['objects']       = self.config.get('datadir','objects')
        self.dir['faces_index']   = self.config.get('datadir','faces_index')
        self.dir['content_index'] = self.config.get('datadir','content_index')

        self.dir['person_index']  = self.config.get('datadir','person_index')
        
        
        self.M                    = self.config.getint('nms', 'M')
        self.efConstruction       = self.config.getint('nms', 'efConstruction')
        self.efSearch             = self.config.getint('nms', 'efSearch')
        self.space_name           = self.config.get('nms', 'space_name')
        self.num_threads          = self.config.getint('nms', 'num_threads')



    def __create_index(self):
        """初始化索引对象
        """
        index = nmslib.init(method='hnsw', space=self.space_name, data_type=nmslib.DataType.DENSE_VECTOR)
        return index

    def __queryitem(self, id_list, index, item, K):
        """索引中查询一个对象，返回查到的结果对应的编号
        
        Arguments:
            id_list {list} -- 索引对应的编号列表
            index {Index对象} -- Index
            item {data} -- 要查询的特征数据
            K {int} -- K值，即返回最大结果数
        """
        # Setting query-time parameters
        query_time_params = {'efSearch': self.efSearch}
        index.setQueryTimeParams(query_time_params)

        size = len(item)
        item = np.array(item)
        item = item.reshape((1,size))
        
        nbrs = index.knnQueryBatch(item, 
        k = K, 
        num_threads = self.num_threads)

        targets = nbrs[0][0]
        distance= nbrs[0][1]
        result = [id_list[int(i)] for i in targets]
        # TODO: 返回距离
        return result, distance

    def __read_featfile(self, id_name, path):
        """读特征文件，返回特征数据以及特征编号列表
        
        Arguments:
            id_name {string} -- 特征文件编号名
            path {string} -- 特征文件文件夹路径
        """
        features_files = []
        dirs = os.listdir(path)
        for d in dirs:
            if os.path.splitext(d)[1] == '.pkl':
                features_files.append(d)
        self.lg("Load %d files from %s"%(len(features_files), path))
        
        features_data_list = []
        for ff_name in features_files:
            ff_name = os.path.join(path, ff_name)
            with open(ff_name,"rb") as ff:
                features_data_list += pickle.load(ff, encoding="utf8")

        num_feats = len(features_data_list)
        self.lg("Feature Count = %d"%(num_feats))
        id_list = []
        feat_list = []
        for i in range(num_feats):
            id_list.append(features_data_list[i][id_name])
            feat_list.append(features_data_list[i]['feat'])                    
        return id_list, feat_list

    def __add_dataToindex(self, index, data):
        """添加数据到索引类，返回添加好数据的index类
        
        Arguments:
            index {[Index索引类]} -- [索引对象]
            data {[data]} -- [特征列表]
        """
        index_time_params = {'M': self.M, 
        'indexThreadQty': self.num_threads, 
        'efConstruction': self.efConstruction}
        index.addDataPointBatch(data)
        self.lg("Add DataPoint to index...")
        index.createIndex(index_time_params)
        return index

    def __get_index_id_path(self, index_prefix, index_type):
        """获得对应prefix和索引类型的索引文件名及编号名
        
        Arguments:
            index_prefix {string} -- 要导入的索引文件前缀
            index_type {string} -- 要导入的索引文件类型，face_index, content_index
        """
        index_file_name = index_prefix+"_%s.bin"%index_type
        index_path= self.dir[index_type]
        index_dir = os.path.join(index_path, index_file_name) 

        id_file_name = index_prefix+"_%s.npy"%index_type
        id_dir = os.path.join(index_path, id_file_name)
        return index_dir, id_dir


    def __save_feat_index(self, feat_type, index_type, index_prefix, id_name, isSave):
        """创建并保存索引到文件，返回载入索引的Index类及编号
        
        Arguments:
            feat_type {string} -- 特征文件类型-face_feat, content_feat
            index_type {string} -- 索引文件类型-face_index, content_index
            index_prefix {string} -- 索引文件前缀名
            id_name {string} -- 特征文件对应的编号名
            isSave {bool} -- 是否保存到文件
        Returns:
            index {Index类} -- 索引类
            id_list {list} -- 编号列表
        """
        feat_dir           = self.dir[feat_type]
        index_dir          = self.dir[index_type]
        
        id_list, feat_list = self.__read_featfile(id_name, feat_dir)
        index              = self.__create_index()
        index              = self.__add_dataToindex(index,feat_list)
    
        # save
        if isSave:
            index_dir, id_dir = self.__get_index_id_path(index_prefix, index_type)
            index.saveIndex(index_dir)
            # 保存id文件
            np.save(id_dir, id_list)

        return index, id_list

    def create_facefeat_index(self, prefix, isSave=True):
        """创建人脸数据索引
        
        Arguments:
            prefix {string} -- 要创建的索引文件前缀
        
        Keyword Arguments:
            isSave {bool} -- [是否保存到文件] (default: {True})
        """
        return self.__save_feat_index('faces_feat', 'faces_index', prefix, 'ffid', isSave)

    def create_contentfeat_index(self, prefix, isSave=True):
        """创建场景数据索引
        
        Arguments:
            prefix {string} -- [要创建的索引文件前缀]
        
        Keyword Arguments:
            isSave {bool} -- [是否保存到文件] (default: {True})
        """
        return self.__save_feat_index('content_feat', 'content_index', prefix, 'sfid', isSave)
    
    def load_index(self):
        """将索引载入内存，用于检索用户请求图片提取的特征
        """
        self.load_face_index()
        self.load_cont_index()
        self.load_person_index()
        

    def create_person_index(self, person_feats, person_ids):
        """创建人物特征索引并保存，返回已经载入数据的Index对象
        
        Arguments:
            person_feats {list} -- 人物特征列表
            person_ids {list} -- 人物特征对应的编号
        """
        index              = self.__create_index()
        index              = self.__add_dataToindex(index,person_feats)
    
        # save
        index_dir, id_dir = self.__get_index_id_path(self.index_prefix, 'person_index')
        index.saveIndex(index_dir)

        # 保存id文件
        np.save(id_dir, person_ids)

        return index


    def load_person_index(self):
        """将人物人脸特征索引载入内存
        """
        if self.ispersLoad:
            pass
        else:
            self.ispersLoad = True
            self.person_index = self.__create_index()
            index_dir, id_dir = self.__get_index_id_path('Person', 'person_index')            
            self.person_index.loadIndex(index_dir)
            self.person_id_list = np.load(id_dir)

    def load_face_index(self):
        """将人脸特征索引载入内存
        """
        if self.isfaceLoad:
            pass
        else:
            self.isfaceLoad = True
            # 读文件
            self.face_index = self.__create_index()
            index_dir, id_dir = self.__get_index_id_path(self.index_prefix, 'faces_index')            
            self.face_index.loadIndex(index_dir)
            self.face_id_list = np.load(id_dir)
        pass
    
    def load_cont_index(self):
        """将场景特征索引载入内存
        """
        if self.iscontLoad:
            pass
        else:
            self.iscontLoad = True
            # 读文件
            self.cont_index = self.__create_index()
            index_dir, id_dir = self.__get_index_id_path(self.index_prefix, 'content_index')            
            self.cont_index.loadIndex(index_dir)
            self.cont_id_list = np.load(id_dir)
        pass

    def __query_index(self, query_feat, 
        index_type, K=100, index_prefix=None, 
        index=None, id_list=None):
        """在Index中检索索引
        
        Arguments:
            query_feat {data} -- 要检索的特征数据
            index_type {string} -- 索引类型
        
        Keyword Arguments:
            K {int} --结果数 (default: {100})
            index_prefix {string} -- 索引文件前缀 (default: {None})
            index {Index对象} -- 索引对象 (default: {None})
            id_list {list} -- 编号列表 (default: {None})
        """
        if index_prefix is None and index is None:
            self.lg("index_prefix or index should not None.")
            return None
        
        if index != None:
            # 读内存中的index            
            if id_list is None:
                self.lg("id_list should not None.")
                return None
        else:
            # 读文件
            pass
        if index_type == 'faces_index':
            self.load_face_index()
            result, distance = self.__queryitem(self.face_id_list, self.face_index, query_feat, K)
        elif index_type == 'content_index':
            self.load_cont_index()
            result, distance = self.__queryitem(self.cont_id_list, self.cont_index, query_feat, K)
        else:
            self.load_person_index()
            result, distance = self.__queryitem(self.person_id_list, self.person_index, query_feat, K)
        # self.lg(str(result))
        return result,distance

    def queryFace(self, facefeat,  
        index=None, id_list=None):
        """检索人脸特征，返回结果编号列表
        
        Arguments:
            facefeat {data} -- 要检索的人脸特征
        
        Keyword Arguments:
            index {Index对象} -- Index对象 (default: {None})
            id_list {list} -- 编号列表 (default: {None})
        """
        return self.__query_index(facefeat, 'faces_index', 100, self.index_prefix,index, id_list)

    def queryPerson(self, facefeat,  
        index=None, id_list=None):
        """检索人物特征，返回结果编号列表
        
        Arguments:
            facefeat {data} -- 要检索的人脸特征
        
        Keyword Arguments:
            index {Index对象} -- Index对象 (default: {None})
            id_list {list} -- 编号列表 (default: {None})
        """
        # 只查询10个
        return self.__query_index(facefeat, 'person_index', 10, self.index_prefix,index, id_list)

    def queryContent(self, contentfeat, 
        index=None, id_list=None):
        """检索场景特征，返回结果编号列表
        
        Arguments:
            contentfeat {data} -- 要检索的场景特征
        
        Keyword Arguments:
            index {Index对象} -- Index对象 (default: {None})
            id_list {list} -- 编号列表 (default: {None})
        """
        return self.__query_index(contentfeat, 'content_index', 100, self.index_prefix,index, id_list)
        
if __name__ == "__main__":
    sf = SearchFeature(isShow=True)
    sf.create_facefeat_index('test', isSave=True)
    sf.create_contentfeat_index('test', isSave=True)
    
    # sf.queryFace()