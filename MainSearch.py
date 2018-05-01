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
    def __init__(self, prefix, imagename,max_len=1000, logfile=None, isShow=False):
        BasicPart.__init__(self, logfile, isShow)
        self.imagename     = imagename
        self.facerecog     = FaceRecog(logfile, isShow)
        self.objectdetect  = ObjectDet(logfile, isShow, single_pic_process=True)
        self.dbhandler     = DBHandler()
        self.searchfeature = FeatureIndex(prefix, logfile, isShow)
        self.personface    = PersonFace(logfile, isShow=isShow)
        self.max_len = max_len
        self.prefix = prefix
        # 默认阈值
        self.setThreshold(800, 1000)      

    def setThreshold(self, faceThreshhold, contentThreshold):
        """设置阈值,阈值越大搜索到的结果更多
        
        Arguments:
            faceThreshhold {int} -- 脸部搜索阈值
            contentThreshold {int} -- 内容搜索阈值
        """
        self.faceThreshhold = faceThreshhold
        self.contentThreshold = contentThreshold


    def load_index(self):
        self.searchfeature.load_index()
        self.personface.setFeatureIndex(self.searchfeature)

    def set_image(self,imagename):
        self.imagename     = imagename

    def read_config(self):
        # TODO:配置文件
        self.thumb_prefix = self.config.get("search","thumb_prefix")
        self.thumb_web_prefix = self.config.get("search","thumb_web_prefix")
        self.thumb_size = self.config.get("search","thumb_size")  
        self.personinfo_dir  = self.config.get("datadir","person_info")
         
    
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

    def selectByDistance(self, distance, thresh):
        """按照阈值选择符合条件的结果
        
        Arguments:
            distance {list} -- 距离列表
            thresh {int} -- 距离阈值            
        """
        max_item = 0
        for index, dist in enumerate(distance):
            if dist >= thresh:
                max_item = index
                break
            else:
                max_item = index 
        # 截取
        return max_item

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
        query_result,distance = self.searchfeature.queryFace(query_feat)
        # 选取
        max_index = self.selectByDistance(distance, self.faceThreshhold)
        query_result = query_result[:max_index]
        distance = distance[:max_index]
        sceenid_unique = set(query_result)
        return query_result, distance

    def search_pic(self):
        image_obj_dic = self.objectdetect.extract_image_feature(self.imagename)
        query_feat = image_obj_dic['feat']
        tag_name   = image_obj_dic['tag_name']        
        query_feat = np.array(query_feat)
        query_result,distance = self.searchfeature.queryContent(query_feat)
        # 选取
        max_index = self.selectByDistance(distance, self.contentThreshold)
        query_result = query_result[:max_index]
        distance = distance[:max_index]

        # TODO: 按照sceneid 去重
        query_result_unique = set(query_result)
        return query_result,tag_name,distance

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
        url = 'http://*IP*:8985/solr/*集合名*/select?q=*字段名*:"\%s"&wt=json&indent=true'%item
        r = requests.get(url, verify = False)
        r = r.json()['response']['numFound']
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

    def read_person_info(self, pid):
        """读人物信息文件
        
        Arguments:
            pid {int} -- 人物id
        """
        content = ''
        filename = self.personinfo_dir + '/' + str(pid) + '.txt'
        with open(filename, 'r') as f:
            content = f.read()
        return content


    def get_search_result_JSON(self):
        """返回json格式的检索
        TODO: 完成物体搜索结果
        """
        face_idlist, face_distance = self.search_face()[:self.max_len]
        face_results = self.get_face_to_video_sceneinfo(face_idlist)
        self.lg('FACE:' + str(len(face_idlist)))
        
        cont_idlist, object_list, cont_distance = self.search_pic()
        cont_idlist = cont_idlist[:self.max_len]
        cont_results = self.get_content_to_video_sceneinfo(cont_idlist)
        self.lg('CONT:' + str(len(cont_idlist)))

        result_json = {}
        result_json['face_scene_num'] = len(face_idlist)  
        result_json['face_scene_list'] = self.to_json(face_results)
        result_json['face_dist_list'] = face_distance       

        result_json['content_scene_num'] = len(cont_idlist)  
        result_json['content_scene_list'] = self.to_json(cont_results)
        result_json['content_dist_list'] = cont_distance       
        
        # 交集
        fsids, fvids = self.extrace_ids(face_results)
        csids, cvids = self.extrace_ids(cont_results)
        both_scene_list = []
        # both_scene_list = set(face_results) & set(cont_results)
        both_video_list = set(fvids) | set(cvids)
        result_json['both_video_num']  = len(both_video_list)
        result_json['both_scene_num']  = len(both_scene_list)
        result_json['both_scene_list'] = self.to_json(both_scene_list)

        # 识别人物
        print(self.imagename)
        pid, pname = self.personface.identify_pic_person(self.imagename)
        # 读取存储的人物简介
        pinfo = ''
        if pid != -1:
            pinfo = self.read_person_info(pid)
        result_json['personid'] = pid
        result_json['personname'] = pname
        result_json['personinfo'] = pinfo
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
    ms.setThreshold(800,800)
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
        
        