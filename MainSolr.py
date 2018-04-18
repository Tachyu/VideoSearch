import subprocess

from BasicPart import BasicPart
from DBHandler import DBHandler

try:
    from PIL import Image, ImageDraw
    import numpy as np
except ImportError:
    raise ImportError('Pillow can not be found!')
import json
import requests

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
    
    def __init__(self, videoid, logfile=None, isShow=False):
        BasicPart.__init__(self, logfile, isShow)
        self.handler = DBHandler()
        self.videoid = videoid

    def read_config(self):
        self.address   = self.config.get('solr','address')
        self.port      = self.config.get('solr','port')
        self.v_collect = self.config.get('solr','collecttion_1')
        self.s_collect = self.config.get('solr','collecttion_2')    
    
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
        print(data)
        r = requests.post(url, json = data, params = params, headers = headers)
        return r

    def addVideo(self):
        # 增加视频信息到Solr
        # videoid
        # videopath
        # videoname
        # length
        # addtime
        # description

        videoinfo_dic = self.handler.search_videoinfo_by_videoid(self.videoid)
        data = self.__generate_solrdata(videoinfo_dic)
        # 提交
        r = self.__post_to_solr(self.v_collect, data)
        print(r.text)

    def addScene(self):
        # 查询数据库，并读取本地obj文件
        
        # 1. 首先获取当前视频的所有
        pass

if __name__ == '__main__':  
    ms = MainSolr(videoid=94,isShow=True)
    ms.addVideo()
        