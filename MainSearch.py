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
         
    
    def __get_db_info(self, id_type, id_list, distance):
        """根据id查询数据库
        id_type = 'face' or 'content'
        """
        results = []
        result_distance = []
        if id_type == 'face':
            for index, faceid in enumerate(id_list):
                v_s_info = self.dbhandler.search_scene_video_info_by_faceid(int(faceid))
                results += [SceneInfo(v_s_item) for v_s_item in v_s_info]
                for i in range(len(v_s_info)):
                    result_distance.append(distance[index])
        else:
            for index, picid in enumerate(id_list):
                v_s_info = self.dbhandler.search_scene_video_info_by_picid(int(picid))
                results += [SceneInfo(v_s_item) for v_s_item in v_s_info]
                for i in range(len(v_s_info)):
                    result_distance.append(distance[index])
        return results, result_distance
    
    def get_face_to_video_sceneinfo(self, faceidlist, distance):
        results,re_distance = self.__get_db_info('face', faceidlist, distance)
        return results,re_distance

    def get_content_to_video_sceneinfo(self, picidlist, distance):
        results,re_distance = self.__get_db_info('content', picidlist, distance)
        return results,re_distance
    
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

    def searchKeywords(self, text, keepObjFormat=False):
        """使用solr搜索关键词
        Returns:
            result_dic:
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
        json_video_list = make_video_thumb(self.thumb_info, v_list)
        if not keepObjFormat
            json_scene_list = make_scene_thumb(self.thumb_info, s_list,False)
        else:
            # 转换为SceneInfo
            json_scene_list = [SceneInfo(dic) for dic in s_list]

        result_dic = {}
        result_dic['keywords'] = text
        result_dic['video_num'] = len(json_video_list)  
        result_dic['video_list'] = json_video_list

        result_dic['scene_num'] = len(json_scene_list)  
        result_dic['scene_list'] = json_scene_list
        return result_dic

    def searchJoint(self, image, keywords):
        """图片文字联合搜索
        
        Arguments:
            image {string} -- 图片路径
            keywords {string} -- 关键词
        Returns:
            result_dic:
            {
                keywords{string}, 
                face_scene_num{int},
                face_scene_list{list[scene},
                face_dist_list{list[double]},

                content_scene_num{int},
                content_scene_list{list[scene]},
                content_dist_list{list[double]},

                smart_scene_num{int},
                smart_scene_list{list[scene]},

                keywords_scene_num{int},
                keywords_scene_list{list[scene]},

                both_video_num{int}
                both_scene_num{int}
                both_scene_list{list[scene]}

                personid,personname,personinfo
                object_num,object_list

            }
        """
        keywords_scenes = self.searchKeywords(keywords, keepObjFormat=True)
        self.set_image(image)
        image_scenes = self.searchImage(keepObjFormat=True)
        # 结果综合方法:
        # both&keyword, both|keyword, content, face
        Kset = set(keywords_scenes['scene_list'])
        Bset = set(image_scenes['both_scene_list'])
        Cset = set(image_scenes['content_scene_list'])
        Fset = set(image_scenes['face_scene_list'])

        smart_scene_list = list(Kset & Bset)
        smart_scene_list += list( (Kset | Bset) - (Kset & Bset) )
        smart_scene_list += list(set(smart_scene_list) - Cset)
        smart_scene_list += list(set(smart_scene_list) - Fset)
        
        result_dic = image_scenes
        result_dic['smart_scene_num'] = len(smart_scene_list)         
        result_dic['smart_scene_list'] = make_scene_thumb(smart_scene_list)

        result_dic['keywords_scene_num'] = len(keywords_scenes['scene_list'])         
        result_dic['keywords_scene_list'] = make_scene_thumb(keywords_scenes['scene_list'])
     
        result_dic['face_scene_list'] = make_scene_thumb(result_dic['face_scene_list'])
        result_dic['content_scene_list'] = make_scene_thumb(result_dic['content_scene_list'])
        
        result_dic['keywords'] = keywords_scenes['keywords']
        return result_dic
        
    def smartsort(self, klist, blist, clist, flist, cdistance, fdistance):
        """多来源结果智能排序
        
        Arguments:
            klist {list} -- 关键词搜索结果
            blist {list} -- content与face交集
            clist {list} -- content搜索结果
            flist {list} -- face搜索结果
            cdistance {list} -- content搜索距离
            fdistance {list} -- face搜索距离            
        Returns:
            list -- 智能排序结果
        """
        Kset = set(klist)
        Bset = set(blist)
        Cset = set(clist)
        Fset = set(flist)
        
        smart_list = list(Kset & Bset)
        smart_list += list(Kset | Bset)

        # 对于剩余的content和face,按照距离排序
        order_arg = np.argsort(cdistance+fdistance)
        order_CandF = np.array(clist + flist)[order_arg]

        smart_list += list(set(order_CandF) | set(smart_list))

        
        return smart_list

    def searchImage(self, keepObjFormat=False):
        """返回json格式的图片检索结果
        Returns:
            result_dic:
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
        # 由于relate加入,所以需要对返回结果进行处理
        face_idlist, face_distance = self.search_face()
        face_results, face_distance = self.get_face_to_video_sceneinfo(face_idlist,face_distance)

        cont_idlist, object_list, cont_distance = self.search_pic()
        cont_idlist = cont_idlist
        cont_results,cont_distance = self.get_content_to_video_sceneinfo(cont_idlist,cont_distance)

        result_dic = {}
        # face
        result_dic['face_scene_num'] = len(face_results)  
        if not keepObjFormat:
            result_dic['face_scene_list'] = make_scene_thumb(self.thumb_info, face_results)
        else:
            result_dic['face_scene_list'] = face_results
        result_dic['face_dist_list'] = list(face_distance) 
        
        # content      
        result_dic['content_scene_num'] = len(cont_results)  
        if not keepObjFormat:
            result_dic['content_scene_list'] = make_scene_thumb(self.thumb_info, cont_results)
        else:
            result_dic['content_scene_list'] = cont_results
        result_dic['content_dist_list'] = list(cont_distance)       
        
        # 交集
        fsids, fvids = extrace_ids(face_results)
        csids, cvids = extrace_ids(cont_results)
        both_scene_list = []
        both_scene_list = set(face_results) & set(cont_results)
        both_video_list = set(fvids) | set(cvids)
        result_dic['both_video_num']  = len(both_video_list)
        result_dic['both_scene_num']  = len(both_scene_list)
        if not keepObjFormat:
            result_dic['both_scene_list'] = make_scene_thumb(self.thumb_info, both_scene_list)
        else:
            result_dic['both_scene_list'] = both_scene_list

        # 组织智能排序结果,
        # both&keyword, both|keyword, content, face
        Bset = set(both_scene_list)
        Cset = set(image_scenes['content_scene_list'])
        Fset = set(image_scenes['face_scene_list'])

        smart_scene_list = list(Kset & Bset)
        smart_scene_list += list( (Kset | Bset) - (Kset & Bset) )
        smart_scene_list += list(set(smart_scene_list) - Cset)
        smart_scene_list += list(set(smart_scene_list) - Fset)
        
        result_dic = image_scenes
        result_dic['smart_scene_num'] = len(smart_scene_list)         
        result_dic['smart_scene_list'] = make_scene_thumb(smart_scene_list)

        # 识别人物
        pid, pname = self.personface.identify_pic_person(self.imagename)
        # 读取存储的人物简介
        pinfo = ''
        if pid != -1:
            pinfo = read_person_info(self.personinfo_dir, pid)
        result_dic['personid'] = pid
        result_dic['personname'] = pname
        result_dic['personinfo'] = pinfo
        
        # 物体集合
        result_dic['object_num']  = len(object_list)
        result_dic['object_list'] = object_list

        return result_dic


if __name__ == '__main__':  
    imagename="Data/Tmp/A/20170825.mp4.Scene-161-IN.jpg"
    ms = MainSearch(max_len = 100, isShow=False,logfile="tmp.log")
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
        
        
