# coding: utf-8
# 04.30 重大更新,支持多索引文件读取
# 05.28 新增faiss
import sys 

import time 
import math 
import os
import numpy as np
import logging
from BasicPart import BasicPart
import nmslib 
from sklearn.neighbors import NearestNeighbors
import pickle,math
import faiss

class FeatureIndex(BasicPart):
    """索引建立，读取，检索类
    
    Arguments:
        BasicPart {BasicPart} -- 父类
    """
    def __init__(self,                     
        logfile=None, 
        isShowIndex=False,
        isShow=False):
        BasicPart.__init__(self, logfile, isShow)
        self.isfaceLoad    = False
        self.iscontLoad    = False
        self.ispersLoad    = False        
        self.isShowIndex = isShowIndex
        # 索引对象列表
        self.face_index_list     = []
        self.face_id_list_list   = []
        self.cont_index_list     = []
        self.cont_id_list_list   = []
        self.person_index_list   = []
        self.person_id_list_list = []
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

        # faiss
        self.M                    = self.config.getint('faiss', 'M')
        self.nlist                = self.config.getint('faiss', 'nlist')
        self.bit                  = self.config.getint('faiss', 'bit')        
        

    def __create_index_hnsw(self):
        """初始化HNSW索引对象
        """
        index = nmslib.init(method='hnsw', space=self.space_name, data_type=nmslib.DataType.DENSE_VECTOR) 
        return index

    def __compute_cluster_args(self, count, dimention):
        """计算flatpq的各项参数
        
        Arguments:
            count {int} -- 数据量
        """
        # 要求: count % D == 0
        print("%d x %d"%(count, dimention))
        m = 2
        for i in range(2,dimention):
            if (dimention % i) == 0:
                m = i
                break
        if i == dimention - 1:
            m = dimention
        # 暂时按照维度算
        if dimention > 2048:
            bit = 6
        else:
            bit = 3

        return m, bit 

    def __create_index_flatpq(self, count, dimention):
        """创建一个flatpq索引
        
        Arguments:
            dimention {int} -- 数据维度
        
        Returns:
            index -- 未训练的索引对象
        """
        quantizer = faiss.IndexFlatL2(dimention)  # this remains the same
        M, bit = self.__compute_cluster_args(count, dimention) 
        print("M=%d bit=%d"%(M, bit))
        index = faiss.IndexIVFPQ(quantizer, dimention, self.nlist, M, bit)
        return index, quantizer
    
    def __queryitem(self, index_method, id_list, index, item, K):
        """索引中查询一个对象，返回查到的结果对应的编号
        
        Arguments:
            index_method {string} -- 索引方法 
            id_list {list} -- 索引对应的编号列表
            index {Index对象} -- Index
            item {data} -- 要查询的特征数据
            K {int} -- K值，即返回最大结果数
        """
        size = len(item)
        item = np.array(item)
        item = item.reshape((1,size))
        
        if index_method == 'hnsw':
            # Setting query-time parameters            
            query_time_params = {'efSearch': self.efSearch}
            index.setQueryTimeParams(query_time_params)
            nbrs = index.knnQueryBatch(item, 
             k = K, 
             num_threads = self.num_threads)
            targets = nbrs[0][0]
            distance= nbrs[0][1]

        elif index_method == 'flatpq':
            distance, targets = index.search(item, K)
            targets = targets[0]
            distance= distance[0]
    
        else:
            return None, None


        result = [id_list[int(i)] for i in targets]
        return result, distance


    def __read_featfile(self, id_name, path,features_files=[]):
        """读特征文件，返回特征数据以及特征编号列表
        
        Arguments:
            id_name {string} -- 特征文件编号字段名
            path {string} -- 特征文件文件夹路径
        """
        # 读目录下所有特征文件
        if len(features_files) == 0:
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
        id_list = [item[id_name] for item in features_data_list]
        feat_list = [item['feat'] for item in features_data_list]                 
        return id_list, feat_list

    def __add_dataToindex(self, index_method, index, data):
        """添加数据到索引类，返回添加好数据的index类
        
        Arguments:
            index_method {string} -- 索引方法 hnsw, flatpq 
            index {[Index索引类]} -- [索引对象]
            data {[data]} -- [特征列表]
        """
        if index_method == 'hnsw':
            index_time_params = {'M': self.M, 
            'indexThreadQty': self.num_threads, 
            'efConstruction': self.efConstruction}
            index.addDataPointBatch(data)
            self.lg("Add Data to HNSW index...")
            index.createIndex(index_time_params)

        elif index_method == 'flatpq':
            data = np.array(data).astype('float32')
            self.lg("Add Data to FlatPQ index...")           
            index.train(data)
            index.add(data)
            
        else:
            return None
        
        return index

    def __get_index_id_path(self, index_method, index_prefix, index_type):
        """获得对应prefix和索引类型的索引文件名及编号名
        
        Arguments:
            index_method {string} -- 索引方法 hnsw, flatpq 
            index_prefix {string} -- 要导入的索引文件前缀
            index_type {string} -- 要导入的索引文件类型，face_index, content_index
        """
        index_file_name = index_prefix+"_%s_%s.bin"%(index_method,index_type)
        index_path= self.dir[index_type]
        index_dir = os.path.join(index_path, index_file_name) 

        id_file_name = index_prefix+"_%s.npy"%index_type
        id_dir = os.path.join(index_path, id_file_name)
        return index_dir, id_dir


    def __create_feat_index(self, index_method, feat_type, index_type, index_prefix, id_name, isSave, features_files):
        """创建并保存索引到文件，返回载入索引的Index类及编号
        
        Arguments:
            index_method {string} -- 索引方法 hnsw, flatpq                       
            feat_type {string} -- 特征文件类型-face_feat, content_feat
            index_type {string} -- 索引文件类型-face_index, content_index
            index_prefix {string} -- 索引文件前缀名
            id_name {string} -- 特征文件对应的编号字段名
            isSave {bool} -- 是否保存到文件
        Returns:
            index {Index类} -- 索引类
            id_list {list} -- 编号列表
        """
        feat_dir           = self.dir[feat_type]
        index_dir          = self.dir[index_type]
        
        id_list, feat_list = self.__read_featfile(id_name, feat_dir, features_files)
        
        if index_method == 'hnsw':
            index       = self.__create_index_hnsw()
            index       = self.__add_dataToindex('hnsw', index, feat_list)

        elif index_method == 'flatpq':
            index,quantizer = self.__create_index_flatpq(len(feat_list), len(feat_list[0]))
            index       = self.__add_dataToindex('flatpq', index, feat_list)            
        else:
            self.lg("Invaild index_method:%s in function __create_feat_index"%(index_method))
            return None, []

        # save
        if isSave:
            index_dir, id_dir = self.__get_index_id_path(index_method, index_prefix, index_type)
            self.__saveIndex(index_method, index, id_list, index_dir, id_dir)
        return index, id_list

    def __saveIndex(self, index_method, index, id_list, index_dir, id_dir):
        """保存index到文件
        
        Arguments:
            index_method {string} -- 索引方法 hnsw, flatpq      
            index {index} -- 索引对象
            id_list{list} -- 编号列表
            index_dir {string} -- 索引保存路径      
            id_dir {string} -- 编号保存路径                 
        """
        if index_method == 'hnsw':
            index.saveIndex(index_dir)
        elif index_method == 'flatpq':
            faiss.write_index(index, index_dir)          
        else:
            self.lg("Invaild index_method:%s in function __saveIndex"%(index_method))
            pass
        # 保存id文件
        np.save(id_dir, id_list)

    def create_facefeat_index(self, index_method, prefix, isSave=True, features_files=[]):
        """创建人脸数据索引
        
        Arguments:
            index_method {string} -- 索引方法 hnsw, flatpq
            prefix {string} -- 要创建的索引文件前缀
        Keyword Arguments:
            isSave {bool} -- 是否保存到文件 (default: {True})
            features_files {list} -- 特征文件列表 (default: [])
        """
        return self.__create_feat_index(index_method, 'faces_feat', 'faces_index', prefix, 'ffid', isSave, features_files)

    def create_contentfeat_index(self, index_method, prefix, isSave=True,  features_files=[]):
        """创建场景数据索引
        
        Arguments:
            index_method {string} -- 索引方法 hnsw, flatpq
            prefix {string} -- 要创建的索引文件前缀
        Keyword Arguments:
            isSave {bool} -- 是否保存到文件 (default: {True})
            features_files {list} -- 特征文件列表 (default: [])
        """
        return self.__create_feat_index(index_method, 'content_feat', 'content_index', prefix, 'sfid', isSave,  features_files)
    
    def load_index(self, face_index_method, content_index_method, index_prefixs=['test'], person_index_prefixs=['Person']):
        """将索引载入内存，用于检索用户请求图片提取的特征
            index_method {string} -- 索引方法 hnsw, flatpq
        """
        self.index_prefixs=index_prefixs
        self.person_index_prefixs=person_index_prefixs    
        self.load_face_index(face_index_method, index_prefixs)
        self.load_cont_index(content_index_method, index_prefixs)
        self.load_person_index(person_index_prefixs)
        

    def create_person_index(self, person_feats, person_ids, index_prefix):
        """创建HNSW人物特征索引并保存，返回已经载入数据的Index对象
        
        Arguments:
            person_feats {list} -- 人物特征列表
            person_ids {list} -- 人物特征对应的编号
        """
        index              = self.__create_index_hnsw()
        index              = self.__add_dataToindex('hnsw', index,person_feats)
    
        # save
        index_dir, id_dir = self.__get_index_id_path('hnsw', index_prefix, 'person_index')
        self.__saveIndex('hnsw', index, person_ids, index_dir, id_dir)
        return index


    def load_person_index(self, person_index_prefixs=["Person"]):
        """将人物人脸特征索引载入内存
           增加载入多个索引的功能
        """
        if self.ispersLoad:
            pass
        else:
            self.ispersLoad = True
            for index_prefix in person_index_prefixs:
                index_dir, id_dir = self.__get_index_id_path('hnsw', index_prefix, 'person_index')
                person_index = self.__create_index_hnsw()          
                person_index.loadIndex(index_dir)
                person_id_list = np.load(id_dir)
                self.person_index_list.append(person_index)
                self.person_id_list_list.append(person_id_list)
                

    def load_face_index(self, index_method, index_prefixs):
        """将人脸特征索引载入内存
        增加载入多个索引的功能
            index_method {string} -- 索引方法 hnsw, flatpq
        """
        if self.isfaceLoad:
            pass
        else:
            self.isfaceLoad = True
            # 读文件
            for index_prefix in index_prefixs:
                self.lg("index_prefix = %s"%index_prefix)
                index_dir, id_dir = self.__get_index_id_path(index_method, index_prefix, 'faces_index')
                if index_method == 'hnsw':
                    self.lg("load hnsw face index: %s"%(index_dir)) 
                    face_index = self.__create_index_hnsw()          
                    face_index.loadIndex(index_dir)

                elif index_method == 'flatpq':
                    self.lg("load flatpq face index: %s"%(index_dir))                    
                    face_index  =  faiss.read_index(index_dir) 

                else:
                    self.lg("Invaild index_method:%s in function load_face_index"%(index_method))
                    return
                
                face_id_list = np.load(id_dir)
                self.face_index_list.append(face_index)
                self.face_id_list_list.append(face_id_list)
    
    def load_cont_index(self, index_method, index_prefixs):
        """将场景特征索引载入内存
        index_method {string} -- 索引方法 hnsw, flatpq
        """
        if self.iscontLoad:
            pass
        else:
            self.iscontLoad = True

            # 读文件
            for index_prefix in index_prefixs:
                index_dir, id_dir = self.__get_index_id_path(index_method, index_prefix, 'content_index')  
                if index_method == 'hnsw':
                    self.lg("load hnsw content index: %s"%(index_dir))
                    cont_index = self.__create_index_hnsw()
                    cont_index.loadIndex(index_dir)

                elif index_method == 'flatpq':
                    self.lg("load flatpq content index: %s"%(index_dir))
                    cont_index  =  faiss.read_index(index_dir) 

                else:
                    self.lg("Invaild index_method:%s in function load_cont_index"%(index_method))
                    return

                cont_id_list = np.load(id_dir)
                self.cont_index_list.append(cont_index)
                self.cont_id_list_list.append(cont_id_list)
        pass

    def __query_index(self, index_method, index_prefixs, query_feat, 
        index_type, K=100):
        """在Index中检索索引
        
        Arguments:
            index_method {string} -- 索引方法 hnsw, flatpq
            index_prefixs {string} -- 索引文件前缀
            query_feat {data} -- 要检索的特征数据
            index_type {string} -- 索引类型
        
        Keyword Arguments:
            K {int} --结果数 (default: {100})
        """
        query_feat = np.array(query_feat).astype("float32")
        if index_type == 'faces_index':
            self.load_face_index(index_method, index_prefixs)
            id_list_list = self.face_id_list_list
            index_list   = self.face_index_list

        elif index_type == 'content_index':
            self.load_cont_index(index_method, index_prefixs)
            id_list_list = self.cont_id_list_list
            index_list   = self.cont_index_list
        
        else:
            self.load_person_index()
            id_list_list = self.person_id_list_list
            index_list   = self.person_index_list
        # 多个索引中查询
        result = []
        distance = []
        for index_id, queryIndex in enumerate(index_list):
            id_list   = id_list_list[index_id]
            res, dis  = self.__queryitem(index_method, id_list, queryIndex, query_feat, K)
            result    = result + list(res)
            distance  = distance + list(dis)
        # 按照距离从小到大排序
        res_np   = np.array(result)        
        dis_np   = np.array(distance)
        dis_arg  = np.argsort(dis_np)
        distance = list(dis_np[dis_arg])
        result   = list(res_np[dis_arg])

        # 废弃---将result变为字典 
        # for i, rid in enumerate(result):
        #     re = {}
        #     re['sceneid'] = rid
        #     re[index_type+'_distance'] = distance[i]
            
        return result,distance

    def queryFace(self, index_method, index_prefixs, facefeat, max_count=1000):
        """检索人脸特征，返回结果编号列表
        
        Arguments:
            index_method {string} -- 索引方法 hnsw, flatpq
            index_prefixs {string} -- 索引文件前缀
            facefeat {data} -- 要检索的人脸特征
            max_count {int} -- 最多结果数
        """
        return self.__query_index(index_method, index_prefixs, facefeat, 'faces_index', max_count)

    def queryPerson(self, facefeat):
        """检索人物特征，返回结果编号列表
        
        Arguments:
            facefeat {data} -- 要检索的人脸特征
        
        Keyword Arguments:
            max_count {int} -- 最多结果数
        """
        # 只查询10个
        results, distance = self.__query_index('hnsw', [], facefeat, 'person_index', 10)
        results = results[:10]
        distance = distance[:10] 
        return results, distance

    def queryContent(self, index_method, index_prefixs, contentfeat, max_count=1000):
        """检索场景特征，返回结果编号列表
        
        Arguments:
            index_method {string} -- 索引方法 hnsw, flatpq
            index_prefixs {string} -- 索引文件前缀
            contentfeat {data} -- 要检索的场景特征
        
        Keyword Arguments:
            max_count {int} -- 最多结果数
        """
        return self.__query_index(index_method, index_prefixs, contentfeat, 'content_index', max_count)
        
if __name__ == "__main__":
    sf = FeatureIndex(isShow=True)
    # sf.create_facefeat_index('flatpq',    'all', isSave=True)
    sf.create_facefeat_index('hnsw',    'all', isSave=True)

    # sf.create_contentfeat_index('flatpq', 'all', isSave=True)
    
    # sf.queryFace()