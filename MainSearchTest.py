import subprocess

from FeatureIndex import FeatureIndex
from BasicPart import BasicPart
from FaceRecog import FaceRecog
from ObjectDet import ObjectDet
from DBHandler import DBHandler
from PersonFace import PersonFace
from MainSolr import MainSolr
from PublicTool import *
import os,json,time

try:
    from PIL import Image, ImageDraw
    import numpy as np
except ImportError:
    raise ImportError('Pillow can not be found!')

class MainSearch(BasicPart):
    def __init__(self, 
        max_len=1000, logfile=None, isShow=False):
        BasicPart.__init__(self, logfile, isShow)
        self.imagename     = ''
        self.facerecog     = FaceRecog(logfile=logfile, isShow=isShow)
        self.objectdetect  = ObjectDet(logfile, single_pic_process=True,isShow=isShow, picShow=False)
        self.dbhandler     = DBHandler()
        self.searchfeature = FeatureIndex(logfile=logfile, isShow=isShow)
        self.personface    = PersonFace(logfile=logfile, isShow=isShow)
        self.solrobj       = MainSolr(logfile=logfile, isShow=isShow)

        self.max_len = max_len
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


    def load_index(self,prefixlist,person_prefix_list):
        self.searchfeature.load_index(prefixlist,person_prefix_list)
        self.personface.setFeatureIndex(self.searchfeature)

    def set_image(self,imagename):
        """设置要搜索的图片路径
        
        Arguments:
            imagename {string} -- 图片路径
        """
        self.imagename     = imagename

    def read_config(self):
        # TODO:配置文件
        self.thumb_prefix = self.config.get("search","thumb_prefix")
        self.thumb_web_prefix = self.config.get("search","thumb_web_prefix")
        self.thumb_size = self.config.get("search","thumb_size")  
        self.personinfo_dir  = self.config.get("datadir","person_info")
        self.thumb_info = (self.thumb_size, self.thumb_prefix, self.thumb_web_prefix)
         
    
    def __get_db_info(self, id_type, id_list):
        """根据id查询数据库
        id_type = 'face' or 'content'
        """
        results = []
        if id_type == 'face':
            for faceid in id_list:
                v_s_info = self.dbhandler.search_scene_video_info_by_faceid(int(faceid))
                results += [SceneInfo(v_s_item) for v_s_item in v_s_info]
        else:
            for picid in id_list:
                v_s_info = self.dbhandler.search_scene_video_info_by_picid(int(picid))
                results += [SceneInfo(v_s_item) for v_s_item in v_s_info]
        return set(results)
    
    def get_face_to_video_sceneinfo(self, faceidlist):
        results = self.__get_db_info('face', faceidlist)
        return results

    def get_content_to_video_sceneinfo(self, picidlist):
        results = self.__get_db_info('content', picidlist)
        return results
    
    def create_indexs(self, perfix, featidlist=[], isSave=True):
        """创建特征的索引文件
        """
        # 创建文件名:
        facefeatlist = [id + "_ff.pkl" for id in featidlist]
        contfeatlist = [id + "_sf.pkl" for id in featidlist]
        
        self.searchfeature.create_facefeat_index(perfix,isSave,facefeatlist)
        self.searchfeature.create_contentfeat_index(perfix,isSave,contfeatlist)

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
        if num_faces == 0:
            self.lg("Face not found")
            return [],[]
        
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
        obj_ts = time.time()
        image_obj_dic = self.objectdetect.extract_image_feature(self.imagename)
        query_feat = image_obj_dic['feat']
        tag_name   = image_obj_dic['tag_name']        
        query_feat = np.array(query_feat)
        obj_te = time.time()
        
        feat_ts = time.time()        
        query_result,distance = self.searchfeature.queryContent(query_feat)
        feat_te = time.time()        
        
        # 选取
        max_index = self.selectByDistance(distance, self.contentThreshold)
        query_result = query_result[:max_index]
        distance = distance[:max_index]

        # TODO: 按照sceneid 去重
        query_result_unique = set(query_result)
        return query_result,tag_name,distance,feat_te-feat_ts,obj_te-obj_ts

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

    def searchKeywords(self, text):
        """使用solr搜索关键词
        Returns:
            result_json:
            {
                keywords{string}, 
                video_num{int}, 
                video_list{list[{'videoname','videopath','thumb'}]}
                scene_num{int}
                scene_list{list[{'videoname','videopath','thumb',starttime,sceneid,length}]}
            }
        """
        v_num, v_list, s_num, s_list = self.solrobj.queryKeywords(text)
        # 创建略缩图
        json_video_list = to_json_video(self.thumb_info, v_list)
        json_scene_list = to_json_scene(self.thumb_info, s_list,False)

        result_json = {}
        result_json['keywords'] = text
        result_json['video_num'] = len(json_video_list)  
        result_json['video_list'] = json_video_list

        result_json['scene_num'] = len(json_scene_list)  
        result_json['scene_list'] = json_scene_list
        return result_json

    def joinsearch(self, image, keywords):
        """图片文字联合搜索
        
        Arguments:
            image {string} -- 图片路径
            keywords {string} -- 关键词
        """
        keywords_json = self.searchKeywords(keywords)
        self.set_image(image)
        image_json = self.searchImage()
        

    def searchImage(self):
        """返回json格式的图片检索结果
        Returns:
            result_json:
            {
                keywords{string}, 
                video_num{int}, 
                video_list{list[{'videoname','videopath','thumb'}]},
                face_scene_num{int},
                face_scene_list{list[scene},
                face_dist_list{list[double]},

                content_scene_num{int},
                content_scene_list{list[scene]},
                content_dist_list{list[double]},

                both_video_num{int}
                both_scene_num{int}
                both_scene_list{list[scene]}

                personid,personname,personinfo
                object_num,object_list

            }
        TODO: 完成物体搜索结果
        """
        fs = time.time()
        face_idlist, face_distance = self.search_face()[:self.max_len]
        face_results = self.get_face_to_video_sceneinfo(face_idlist)
        self.lg('searchImage FACE:' + str(len(face_idlist)))
        fe = time.time()
        

        cont_idlist, object_list, cont_distance,ft,ot = self.search_pic()
        cont_idlist = cont_idlist[:self.max_len]
        cont_results = self.get_content_to_video_sceneinfo(cont_idlist)
        self.lg('searchImage CONT:' + str(len(cont_idlist)))


        ts = time.time()
        result_json = {}
        result_json['face_scene_num'] = len(face_idlist)  
        result_json['face_scene_list'] = to_json_scene(self.thumb_info, face_results)
        result_json['face_dist_list'] = list(face_distance)       

        result_json['content_scene_num'] = len(cont_idlist)  
        result_json['content_scene_list'] = to_json_scene(self.thumb_info, cont_results)
        result_json['content_dist_list'] = list(cont_distance)       
        
        # 交集
        fsids, fvids = extrace_ids(face_results)
        csids, cvids = extrace_ids(cont_results)
        both_scene_list = []
        # both_scene_list = set(face_results) & set(cont_results)
        both_video_list = set(fvids) | set(cvids)
        result_json['both_video_num']  = len(both_video_list)
        result_json['both_scene_num']  = len(both_scene_list)
        result_json['both_scene_list'] = to_json_scene(self.thumb_info, both_scene_list)

        te = time.time()     

        ps = time.time()   
        # 识别人物
        pid, pname = self.personface.identify_pic_person(self.imagename)
        # 读取存储的人物简介
        pinfo = ''
        if pid != -1:
            pinfo = read_person_info(self.personinfo_dir, pid)
        result_json['personid'] = pid
        result_json['personname'] = pname
        result_json['personinfo'] = pinfo
        # 物体集合
        result_json['object_num']  = len(object_list)
        result_json['object_list'] = object_list
        pe = time.time()
        print("%.4f, %.4f, %.4f, %.4f,%.4f"%(fe-fs, ot, ft, pe-ts, pe-fs))
        return result_json


if __name__ == '__main__':  
    imagename="Data/Tmp/A/20170825.mp4.Scene-161-IN.jpg"
    ms = MainSearch(max_len = 100, isShow=False,logfile="tmp.log")
    ms.set_image(imagename)
    ms.searchImage()
    print()
    # ms.create_indexs('0701&0825&1220',['130','131','132'],True)
    ms.setThreshold(800,800)
    ms.load_index(['0701&0825&1220'],['Person'])
    pic_list = ['Data/Tmp/A/','Data/Tmp/B/','Data/Tmp/C/']
    for i, picdir in enumerate(pic_list):
        pics = os.listdir(picdir)
        for pic in pics:
            # st = time.time()
            ms.set_image(picdir+pic)
            ms.searchImage()
    # print()
    #print(ms.searchKeywords("张德江"))
    
    # idlist = ms.search_face()[:10]
    # results = ms.get_face_to_video_sceneinfo(idlist)  
    # ms.show_pics(results)

    # # idlist = ms.search_pic()[:5]
    # # results = ms.get_content_to_video_sceneinfo(idlist)  
    # # ms.show_pics(results)
    # for re in results:
    #     print(re)     
        
        
