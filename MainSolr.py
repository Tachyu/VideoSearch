import subprocess

from BasicPart import BasicPart
from DBHandler import DBHandler

try:
    from PIL import Image, ImageDraw
    import numpy as np
except ImportError:
    raise ImportError('Pillow can not be found!')
import json
import requests,os,pickle

class MainSolr(BasicPart):
    """向Solr服务器增加新数据
    格式：
    VideoSearch
        videoid
        videopath
        videoname
        length
        addtime
        description
    
    SceneSearch
        videoname
        videopath
        persons
        objects
        starttime
        length
    
    Arguments:
        BasicPart {父类} -- [description]
    
    Returns:
        [type] -- [description]
    """
    
    def __init__(self, logfile=None, isShow=False):
        BasicPart.__init__(self, logfile, isShow)
        self.handler = DBHandler()

    def read_config(self):
        self.address   = self.config.get('solr','address')
        self.port      = self.config.get('solr','port')
        self.v_collect = self.config.get('solr','collecttion_1')
        self.s_collect = self.config.get('solr','collecttion_2')   
        self.objdir = self.config.get('datadir','objects')  
        self.max_result = self.config.getint('solr','max_result')  
    
    def __generate_solrdata(self, dic_data):
        data      = {}
        doc_data  = {}
        doc_data['doc'] = dic_data
        data['add']     = doc_data
        return data   

    def __post_to_solr(self, collection, data):
        params  = {"boost":1.0,"overwrite": "true","commitWithin": 1000}
        url     = 'http://%s:%s/solr/%s/update?wt=json'%(self.address, self.port, collection)
        headers = {"Content-Type": "application/json"}
        # print(data)
        r = requests.post(url, json = data, params = params, headers = headers)
        return r

    def __read_objs(self, videoid):
        """读物体文件，返回物体数据列表
        """
        obj_files = []
        obj_files.append('%d_ob.pkl'%videoid)
        self.lg("Load %d files from %s"%(len(obj_files), self.objdir))
        
        obj_data_list = []
        for ob_name in obj_files:
            ob_name = os.path.join(self.objdir, ob_name)
            with open(ob_name,"rb") as objf:
                obj_data_list += pickle.load(objf, encoding="utf8")

        return obj_data_list

    def addVideo(self,videoid):
        # 增加视频信息到Solr
        # videoid
        # videopath
        # videoname
        # length
        # addtime
        # description

        videoinfo_dic = self.handler.search_videoinfo_by_videoid(videoid)
        data = self.__generate_solrdata(videoinfo_dic)
        # 提交
        r = self.__post_to_solr(self.v_collect, data)
        # print(r.text)

    def addScene(self, videoid):
        # 查询数据库，并读取本地obj文件
        # 1. 首先获取所有物体信息

        obj_data_list = self.__read_objs(videoid)

        # 根据picid从数据库获取场景信息
        # 增加场景中识别到的人物信息
        sceneinfos =[]    
        for pic_item in obj_data_list:
            pic_id = pic_item['picid']
            # print(pic_id)
            sceneinfo_list = self.handler.search_scene_video_info_by_picid(pic_id)
            for sceneinfo in sceneinfo_list:
                sceneinfo['objects'] = pic_item['objs']
                
                # 提交
                data = self.__generate_solrdata(sceneinfo)
                r = self.__post_to_solr(self.s_collect, data)
            # print(r.text)
        #

    def __query(self, collection, keywords):
        args = (self.address, self.port, collection,keywords, self.max_result)
        url_video = '''http://%s:%s/solr/%s/select?q=%s&wt=json&indent=true&rows=%d'''%args
        # print(url_video)
        r = requests.get(url_video, verify = False)
        r = r.json()
        # print(r)
        return r['response']['numFound'], r['response']['docs']

    def queryKeywords(self, keywords):
        """在solr中检索关键词
        
        Arguments:
            keywords {string} -- 关键词
        
        Returns:
            v_num -- 视频数
            v_list -- 视频列表
            s_num -- 场景数
            s_list -- 场景列表
        """
        v_num, v_list = self.__query(self.v_collect,keywords)
        s_num, s_list = self.__query(self.s_collect,keywords)
        return v_num, v_list, s_num, s_list
    
    def addManySceneAndVideo(self, idlist):
        for id in idlist:
            self.addVideo(id)
            self.addScene(id)
            

        
if __name__ == '__main__':  
    ms = MainSolr(isShow=True)
    # idlist = [i for i in range(1,13,1)]
    # print(idlist)
    # ms.addManySceneAndVideo(idlist)
    # ms.addVideo(130)    
    # ms.addScene(130)
    # ms.addVideo(131)    
    # ms.addScene(131)
    # ms.addVideo(132)    
    # ms.addScene(132)
    print(ms.queryKeywords("习近平"))
        