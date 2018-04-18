import subprocess

from SearchFeature import SearchFeature
from BasicPart import BasicPart
from FaceRecog import FaceRecog
from ObjectDet import ObjectDet
from DBHandler import DBHandler

try:
    from PIL import Image, ImageDraw
    import numpy as np
except ImportError:
    raise ImportError('Pillow can not be found!')


class MainSearch(BasicPart):
    def __init__(self, prefix, imagename, logfile=None, isShow=False):
        BasicPart.__init__(self, logfile, isShow)
        self.imagename     = imagename
        self.facerecog     = FaceRecog(logfile, isShow)
        self.objectdetect  = ObjectDet(logfile, isShow, single_pic_process=True)
        self.dbhandler     = DBHandler()
        self.SearchFeature = SearchFeature(logfile, isShow)
        self.prefix = prefix
        
    
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
        query_result = self.searchfeature.queryFace(query_feat, index_prefix=self.prefix)

        # TODO: 按照sceneid 去重
        sceenid_unique = set(query_result)
        return query_result

    def search_pic(self):
        image_obj_dic = self.objectdetect.extract_image_feature(self.imagename)
        query_feat = image_obj_dic['feat']
        query_feat = np.array(query_feat)
        query_result = self.searchfeature.queryContent(query_feat, index_prefix=self.prefix)
        # TODO: 按照sceneid 去重
        query_result_unique = set(query_result)
        return query_result

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
            cmd = '''
            ffmpeg -ss %d -i %s -y -f image2 -vframes 1 -s 800x600 %s
            '''%(timestamp,full_videoname,image_name)
            a = subprocess.getoutput(cmd)
            Image.open(image_name).show()
            image_names.append(image_name)
        
        return image_names

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
    ms = MainSearch(prefix='test', imagename="Data/Tmp/tmp.png",isShow=True)
    # ms = MainSearch(prefix='test', imagename="Data/Tmp/tmp.png",isShow=True)
    
    # ms.create_indexs(True)
    idlist = ms.search_face()[:10]
    results = ms.get_face_to_video_sceneinfo(idlist)  
    ms.show_pics(results)

    # idlist = ms.search_pic()[:5]
    # results = ms.get_content_to_video_sceneinfo(idlist)  
    # ms.show_pics(results)
    for re in results:
        print(re)     
        
        