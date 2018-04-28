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

    def __read_objs(self, videoid=-1):
        """读物体文件，返回物体数据列表
        """
        obj_files = []
        dirs = os.listdir(self.objdir)
        for d in dirs:
            if os.path.splitext(d)[1] == '.pkl':
                if videoid == -1:
                    obj_files.append(d)
                else:
                    if d.find(str(videoid)) == -1:
                        obj_files.append(d)
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
        print(r.text)

    def addScene(self, videoid = -1):
        # 查询数据库，并读取本地obj文件
        # 1. 首先获取所有物体信息

        obj_data_list = self.__read_objs(videoid)

        # 根据picid从数据库获取场景信息
        sceneinfos =[]    
        for pic_item in obj_data_list[:10]:
            pic_id = pic_item['picid']
            sceneinfo = self.handler.search_scene_video_info_by_picid(pic_id)
            sceneinfo['objects'] = pic_item['objs']
             # 提交
            data = self.__generate_solrdata(sceneinfo)
            r = self.__post_to_solr(self.s_collect, data)
            print(r.text)
            


if __name__ == '__main__':  
    ms = MainSolr(isShow=True)
    ms.addScene()
        