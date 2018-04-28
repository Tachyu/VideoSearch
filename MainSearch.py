import subprocess

from FeatureIndex import FeatureIndex
from BasicPart import BasicPart
from FaceRecog import FaceRecog
from ObjectDet import ObjectDet
from DBHandler import DBHandler
from PersonFace import PersonFace
import os,json

try:
    from PIL import Image, ImageDraw
    import numpy as np
except ImportError:
    raise ImportError('Pillow can not be found!')

class MainSearch(BasicPart):
    def __init__(self, prefix, imagename,max_len=20, logfile=None, isShow=False):
        BasicPart.__init__(self, logfile, isShow)
        self.imagename     = imagename
        self.facerecog     = FaceRecog(logfile, isShow)
        self.objectdetect  = ObjectDet(logfile, isShow, single_pic_process=True)
        self.dbhandler     = DBHandler()
        self.searchfeature = FeatureIndex(prefix, logfile, isShow)
        self.personface    = PersonFace(logfile, isShow=isShow)
        self.max_len = max_len
        self.prefix = prefix

    def load_index(self):
        self.searchfeature.load_index()
        self.personface.setFeatureIndex(self.searchfeature)

    def set_image(self,imagename):
        self.imagename     = imagename

    def read_config(self):
        # TODO:配置文件
        self.thumb_prefix = '/var/www/html/SiteVideo/Data/thumbs/'  
        self.thumb_web_prefix = 'Data/thumbs/'  
        self.thumb_size = '400x300'   
         
    
    def __get_db_info(self, id_type, id_list):
        """根据id查询数据库
        id_type = 'face' or 'content'
        """
        results = []
        if id_type == 'face':
            for faceid in id_list:
                v_s_info = self.dbhandler.search_scene_video_info_by_faceid(int(faceid))
                results.append(SceneInfo(v_s_info))
        else:
            for picid in id_list:
                v_s_info = self.dbhandler.search_scene_video_info_by_picid(int(picid))
                results.append(SceneInfo(v_s_info))
        return set(results)
    
    def get_face_to_video_sceneinfo(self, faceidlist):
        results = self.__get_db_info('face', faceidlist)
        return results

    def get_content_to_video_sceneinfo(self, picidlist):
        results = self.__get_db_info('content', picidlist)
        return results
    
    def create_indexs(self, isSave=False):
        """创建特征的索引文件
        """
        self.searchfeature.save_facefeat_index(self.prefix, isSave=isSave)
        self.searchfeature.save_contentfeat_index(self.prefix, isSave=isSave)

    def search_face(self):
        pic_face_dic = self.facerecog.extract_image_face_feature(self.imagename)
        num_faces = len(pic_face_dic['feats'])
        print(pic_face_dic['landmarks'])
        if num_faces == 0:
            self.lg("Face not found")
            return None
        
        # 只搜索第一个脸
        query_feat = pic_face_dic['feats'][0]
        # print(self.prefix)
        query_result,_ = self.searchfeature.queryFace(query_feat)

        # TODO: 按照sceneid 去重
        sceenid_unique = set(query_result)
        return query_result

    def search_pic(self):
        image_obj_dic = self.objectdetect.extract_image_feature(self.imagename)
        query_feat = image_obj_dic['feat']
        tag_name   = image_obj_dic['tag_name']        
        query_feat = np.array(query_feat)
        query_result,_ = self.searchfeature.queryContent(query_feat)
        # TODO: 按照sceneid 去重
        query_result_unique = set(query_result)
        return query_result,tag_name

        # print(result)
    def show_pics(self, results):
        image_names = []
        for list_index,re in enumerate(results):
            re = re.dic
            timestamp  = re['starttime']
            sceneid    = re['sceneid']    
            full_videoname  = re['videoname']       
            videoname  = full_videoname.split("/")[-1]
            image_name = 'Data/Tmp/%s_s%d.jpg'%(videoname,sceneid)
            timestamp = round(timestamp,1) + 0.3
            cmd = '''
            ffmpeg -ss %d -i %s -y -f image2 -vframes 1 -s 800x600 %s
            '''%(timestamp,full_videoname,image_name)
            a = subprocess.getoutput(cmd)
            Image.open(image_name).show()
            image_names.append(image_name)
        
        return image_names
    
    def mkthumb(self, timestamp, full_videoname, image_name):
        timestamp = round(timestamp) + 1
        cmd = '''
            ffmpeg -ss %d -i %s -y -f image2 -vframes 1 -s %s %s
            '''%(timestamp,full_videoname,self.thumb_size,image_name)
        a = subprocess.getoutput(cmd)

    def searchKeywords(self, text):
        """使用solr搜索关键词
        """
        pass
        
    def to_json(self, result_list):
        json_list = []
        # 1. 转换文件名到路径，2.同时生成略缩图：400*300
        for index, re in enumerate(result_list):
            cpdic = re.dic
            videopath = cpdic['videoname']
            video_name = videopath.split('/')[-1]
            cpdic['videoname'] = video_name
            cpdic['videopath'] = videopath

            # 截图
            thumb_name = cpdic['videoname'].split(".")[0] +"_s_"+str(cpdic['sceneid']) +".jpg"
            thumb_path = os.path.join(self.thumb_prefix,thumb_name)
            if os.path.exists(thumb_path):
                pass
            else:
                st = cpdic['starttime']
                pt = cpdic['videopath']
                self.mkthumb(st, pt, thumb_path)
            cpdic['thumb'] = self.thumb_web_prefix + thumb_name
            json_list.append(cpdic)
        return json_list

    def extrace_ids(self, resultlist):
        sceneids = [item.dic['sceneid'] for item in resultlist]
        videoids = [item.dic['videoid'] for item in resultlist]
        return sceneids, videoids

    def get_search_result_JSON(self):
        """返回json格式的检索
        TODO: 完成物体搜索结果
        """
        face_idlist = self.search_face()[:self.max_len]
        face_results = self.get_face_to_video_sceneinfo(face_idlist)
        self.lg('FACE:' + str(len(face_idlist)))
        
        cont_idlist, object_list = self.search_pic()
        cont_idlist = cont_idlist[:self.max_len]
        cont_results = self.get_content_to_video_sceneinfo(cont_idlist)
        self.lg('CONT:' + str(len(cont_idlist)))

        result_json = {}
        result_json['face_scene_num'] = len(face_idlist)  
        result_json['face_scene_list'] = self.to_json(face_results)

        result_json['content_scene_num'] = len(cont_idlist)  
        result_json['content_scene_list'] = self.to_json(cont_results)
        
        # 交集
        fsids, fvids = self.extrace_ids(face_results)
        csids, cvids = self.extrace_ids(cont_results)
        both_scene_list = []
        # both_scene_list = set(face_results) & set(cont_results)
        both_video_list = set(fvids) | set(cvids)

        result_json['both_scene_num']  = len(both_scene_list)
        result_json['both_scene_list'] = self.to_json(both_scene_list)

        # 物体集合
        result_json['object_num']  = len(object_list)
        result_json['object_list'] = object_list

        return result_json



class SceneInfo:
    def __init__(self, dic):
        self.dic = dic
    
    def __eq__(self, other):
        if isinstance(other, SceneInfo):
            return self.dic['sceneid'] == other.dic['sceneid']
        else:
            return False
    def __ne__(self, other):
        return (not self.__eq__(other))
    
    def __str__(self):
        return(str(self.dic))

    def __hash__(self):
        return hash(self.dic['sceneid'])

if __name__ == '__main__':  
    ms = MainSearch(prefix='0825-1031-1030', max_len = 10, imagename="Data/Tmp/1.jpg",isShow=True)
    # ms.create_indexs(True)
    # ms = MainSearch(prefix='test', imagename="Data/Tmp/tmp.png",isShow=True)
    ms.load_index()
    print(ms.get_search_result_JSON())
    
    # idlist = ms.search_face()[:10]
    # results = ms.get_face_to_video_sceneinfo(idlist)  
    # ms.show_pics(results)

    # # idlist = ms.search_pic()[:5]
    # # results = ms.get_content_to_video_sceneinfo(idlist)  
    # # ms.show_pics(results)
    # for re in results:
    #     print(re)     
        
        