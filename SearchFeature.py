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

class SearchFeature(BasicPart):
    def __init__(self, 
        logfile=None, 
        isShow=False):
        BasicPart.__init__(self, logfile, isShow)
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
        
        self.M                    = self.config.getint('nms', 'M')
        self.efConstruction       = self.config.getint('nms', 'efConstruction')
        self.efSearch             = self.config.getint('nms', 'efSearch')
        self.space_name           = self.config.get('nms', 'space_name')
        self.num_threads          = self.config.getint('nms', 'num_threads')



    def __create_index(self):
        index = nmslib.init(method='hnsw', space=self.space_name, data_type=nmslib.DataType.DENSE_VECTOR)
        return index

    def __queryitem(self, id_list, index, item):
        # Setting query-time parameters
        query_time_params = {'efSearch': self.efSearch}
        index.setQueryTimeParams(query_time_params)

        # Querying
        nbrs = index.knnQueryBatch(item, 
        k = self.K, 
        num_threads = self.num_threads)
        result = [id_list[i] for i in nbrs]
        return result

    def __read_featfile(self, id_name, path):
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
        index_time_params = {'M': self.M, 
        'indexThreadQty': self.num_threads, 
        'efConstruction': self.efConstruction}
        index.addDataPointBatch(data)
        self.lg("Creating Face index...")
        index.createIndex(index_time_params)
        return index

    def __get_index_id_path(self, index_prefix, index_dir_name):
        index_file_name = index_prefix+"_%s.bin"%index_dir_name
        index_path= self.dir[index_dir_name]
        index_dir = os.path.join(index_path, index_file_name) 

        id_file_name = index_prefix+"_%s.npy"%index_dir_name
        id_dir = os.path.join(index_path, id_file_name)
        return index_dir, id_dir


    def __save_feat_index(self, feat_dir_name, index_dir_name, index_prefix, id_name, isSave):
        feat_dir           = self.dir[feat_dir_name]
        index_dir          = self.dir[index_dir_name]
        
        id_list, feat_list = self.__read_featfile(id_name, feat_dir)
        index              = self.__create_index()
        index              = self.__add_dataToindex(index,feat_list)

        # save
        if isSave:
            index_dir, id_dir = self.__get_index_id_path(index_prefix, index_dir_name)
            index.saveIndex(index_dir)
            # 保存id文件
            np.save(id_dir, id_list)

        return index, id_list

    def save_facefeat_index(self, prefix, isSave=True):
        return self.__save_feat_index('faces_feat', 'faces_index', prefix, 'ffid', isSave)

    def save_contentfeat_index(self, prefix, isSave=True):
        return self.__save_feat_index('content_feat', 'content_index', prefix, 'sfid', isSave)

    def __query_index(self, query_feat, 
        index_dir_name, index_prefix=None, 
        index=None, id_list=None):
        if index_prefix == None and index == None:
            self.lg("index_prefix or index should not None.")
            return None
        
        if index != None:
            # 读内存中的index            
            if id_list == None:
                self.lg("id_list should not None.")
                return None
        else:
            # 读文件
            index = self.__create_index()
            index_dir, id_dir = self.__get_index_id_path(index_prefix, index_dir_name)            
            index.loadIndex(index_dir)
            id_list = np.load(id_dir)
        result = self.__queryitem(id_list, index, query_feat)
        self.lg(str(result))
        return result

    def queryFace(self, facefeat, 
        index_prefix=None, 
        index=None, id_list=None):
        return self.__query_index(facefeat, 'faces_feat', index_prefix,index, id_list)

    def queryContent(self, facefeat, 
        index_prefix=None, 
        index=None, id_list=None):
        return self.__query_index(facefeat, 'content_feat', index_prefix,index, id_list)
        
if __name__ == "__main__":
    sf = SearchFeature(isShow=True)
    sf.save_facefeat_index('test')
    # sf.queryFace()