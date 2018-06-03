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
        # self.setThreshold(800, 1000) # nmslib
        self.setThreshold(800, 300000) # faiss
              

    def setThreshold(self, faceThreshhold, contentThreshold):
        """设置阈值,阈值越大搜索到的结果更多
        
        Arguments:
            faceThreshhold {int} -- 脸部搜索阈值
            contentThreshold {int} -- 内容搜索阈值
        """
        self.faceThreshhold = faceThreshhold
        self.contentThreshold = contentThreshold


    def load_index(self,prefixlist,person_prefix_list):
        self.searchfeature.load_index(self.face_index_method, self.content_index_method, prefixlist,person_prefix_list)
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
        self.content_distance_discount = self.config.getint("search","content_distance_discount")
        # 索引方法
        self.content_index_method = self.config.get("search","content_index_method")
        self.face_index_method = self.config.get("search","face_index_method")


    def __get_db_info(self, id_type, id_list, distance):
        """根据id查询数据库
        id_type = 'face' or 'content'
        """
        results = []
        result_distance = []
        if id_type == 'face':
            for index, faceid in enumerate(id_list):
                v_s_info = self.dbhandler.search_scene_video_info_by_faceid(int(faceid))
                
                # 字典中增加distance
                for i in range(len(v_s_info)):
                    v_s_info[i][id_type+'_distance'] = distance[index]

                results += [SceneInfo(v_s_item) for v_s_item in v_s_info]                    
                for i in range(len(v_s_info)):
                    result_distance.append(distance[index])
        else:
            for index, picid in enumerate(id_list):
                v_s_info = self.dbhandler.search_scene_video_info_by_picid(int(picid))

                # 字典中增加distance
                for i in range(len(v_s_info)):
                    v_s_info[i][id_type+'_distance'] = distance[index]

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
        
        self.searchfeature.create_facefeat_index(self.face_index_method, perfix,isSave,facefeatlist)
        self.searchfeature.create_contentfeat_index(self.content_index_method, perfix,isSave,contfeatlist)

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
        query_result,distance = self.searchfeature.queryFace(self.face_index_method, ['all'], query_feat)
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
        query_result,distance = self.searchfeature.queryContent(self.content_index_method, ['all'], query_feat)
        # print(len(distance))
        distance = [i / self.content_distance_discount for i in distance]
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
        ns_list = []
        for scene in s_list:
            scene['sceneid'] = int(scene['sceneid'])
            scene['videoid'] = int(scene['videoid'][0])            
            ns_list.append(scene)
        s_list = ns_list
        if not keepObjFormat:
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
        image_scenes = self.searchImage(image, keepObjFormat=True)
        # 结果综合 TODO
        smart_scene_list, both_scene_list = self.smartsort(
        keywords_scenes['scene_list'], 
        image_scenes['content_scene_list'],
        image_scenes['face_scene_list'], 
        image_scenes['content_dist_list'],
        image_scenes['face_dist_list'] )
        
        result_dic = image_scenes
        
        # 更新both
        result_dic['both_scene_num'] = len(both_scene_list)         
        result_dic['both_scene_list'] = make_scene_thumb(self.thumb_info, both_scene_list)

        result_dic['smart_scene_num'] = len(smart_scene_list)         
        result_dic['smart_scene_list'] = make_scene_thumb(self.thumb_info, smart_scene_list)

        result_dic['keywords_scene_num'] = len(keywords_scenes['scene_list'])         
        result_dic['keywords_scene_list'] = make_scene_thumb(self.thumb_info, keywords_scenes['scene_list'])
     
        result_dic['face_scene_list'] = make_scene_thumb(self.thumb_info, result_dic['face_scene_list'])
        result_dic['content_scene_list'] = make_scene_thumb(self.thumb_info, result_dic['content_scene_list'])
        
        result_dic['keywords'] = keywords_scenes['keywords']
        return result_dic

    def compute_score(self, list, keyname, decay):
         # 从前到后,按照100, 100-(100/size), 100-2*(100/size)...计算得分
         # 加权距离的指数 log(1/distance)
         # 总分 =
        list_size = len(list)
        if list_size > 0:
            delta = 100 / list_size
            delta = decay
            scores = [100 - i * delta for i in range(list_size)]
            for index, item in enumerate(list):
                item.dic[keyname] = scores[index]
        return list
            

    def smartsort(self, klist, clist, flist, cdistance, fdistance):
        """多来源结果智能排序
        
        Arguments:
            klist {list} -- 关键词搜索结果
            clist {list} -- content搜索结果
            flist {list} -- face搜索结果
            cdistance {list} -- content搜索距离
            fdistance {list} -- face搜索距离            
        Returns:
            list -- 智能排序结果
        """
        klist = self.compute_score(klist, 'keyword_scores', 0.44)
        clist = self.compute_score(clist, 'content_scores', 0.42)
        flist = self.compute_score(flist, 'face_scores', 0.4)

        Kset = set(klist)
        Cset = set(clist)
        Fset = set(flist)

        smart_list = []
        
        keyword_weight = 0.7
        content_weight = 0.78
        face_weight    = 0.8
        
        for content_item in clist:
            sum_score_item = deepcopy(content_item)
            sum_score_item.dic['sum_scores'] = content_weight * sum_score_item.dic['content_scores']
            if sum_score_item in Fset:
                face_score = flist[flist.index(sum_score_item)].dic['face_scores']
                sum_score_item.dic['sum_scores'] += face_weight * face_score
            if sum_score_item in Kset:
                key_score = klist[klist.index(sum_score_item)].dic['keyword_scores']
                sum_score_item.dic['sum_scores'] += keyword_weight * key_score
            smart_list.append(sum_score_item)

        Sset = set(smart_list)
        for face_item in flist:
            if face_item in Sset:
                continue

            sum_score_item = deepcopy(face_item)
            sum_score_item.dic['sum_scores'] = face_weight * sum_score_item.dic['face_scores']
            if sum_score_item in Cset:
                content_score = clist[clist.index(sum_score_item)].dic['content_scores']
                sum_score_item.dic['sum_scores'] += content_weight * content_score
            if sum_score_item in Kset:
                key_score = klist[klist.index(sum_score_item)].dic['keyword_scores']
                sum_score_item.dic['sum_scores'] += keyword_weight * key_score
            smart_list.append(sum_score_item)

        Sset = set(smart_list)
        for key_item in klist:
            if key_item in Sset:
                continue

            sum_score_item = deepcopy(key_item)
            sum_score_item.dic['sum_scores'] = keyword_weight * sum_score_item.dic['keyword_scores']
            if sum_score_item in Cset:
                content_score = clist[clist.index(sum_score_item)].dic['content_scores']
                sum_score_item.dic['sum_scores'] += content_weight * content_score
            if sum_score_item in Fset:
                face_score = flist[flist.index(sum_score_item)].dic['face_scores']
                sum_score_item.dic['sum_scores'] += face_weight * face_score
            smart_list.append(sum_score_item)
        # 对smart_list按照 sum_scores 排序
        smart_list = sorted(smart_list, key=lambda x:x.dic['sum_scores'], reverse=True)

        if len(klist) == 0:
            both_list = list(Cset & Fset)
        else:
            both_list = list(Kset & Cset & Fset)

        return smart_list, both_list

    def searchImage(self, imagename, keepObjFormat=False):
        """返回json格式的图片检索结果
        Returns:
            result_dic:
            {
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
        self.imagename = imagename
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
        _, fvids = extrace_ids(face_results)
        _, cvids = extrace_ids(cont_results)
        both_video_list = set(fvids) | set(cvids)
        result_dic['both_video_num']  = len(both_video_list)
        smart_scene_list, both_list = self.smartsort([], 
        cont_results, face_results, 
        cont_distance, face_distance)
        

        result_dic['both_scene_num'] = len(both_list)
        if not keepObjFormat:
            result_dic['both_scene_list'] = make_scene_thumb(self.thumb_info, both_list)
        else:
            result_dic['both_scene_list'] = both_list


        result_dic['smart_scene_num'] = len(smart_scene_list)                 
        if not keepObjFormat:
            result_dic['smart_scene_list'] = make_scene_thumb(self.thumb_info, smart_scene_list)
        else:
            result_dic['smart_scene_list'] = smart_scene_list

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
    # imagename="Data/Tmp/A/20170825.mp4.Scene-161-IN.jpg"
    ms = MainSearch(max_len = 100, isShow=True)
    # results = ms.searchImage(imagename)
    # print(results)
    # scene1 = {}
    # scene1['sceneid'] = 1
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
        
        
