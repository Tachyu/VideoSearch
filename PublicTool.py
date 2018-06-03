# coding:utf-8
"""一些公用的函数
"""
import os, requests, json, subprocess,threading
import numpy as np
from copy import deepcopy
# 深拷贝

class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(MyEncoder, self).default(obj)


def mkthumb(thumb_size, timestamp, full_videoname, image_name):
    timestamp = round(timestamp) + 1
    cmd = '''
        ffmpeg -ss %d -i %s -y -f image2 -vframes 1 -s %s %s
        '''%(timestamp,full_videoname,thumb_size,image_name)
    # threading.Thread(target=subprocess.getoutput, args=(cmd))
    a = subprocess.getoutput(cmd)


def make_video_thumb(thumb_info,result_list):
    """将视频结果列表转换为前端接收的json列表,并创建略缩图
    
    Arguments:
        thumb_info {()}:
            thumb_size {string} -- 略缩图大小
            thumb_prefix {string} -- 略缩图前缀
            thumb_web_prefix {string} -- 略缩图所在网站路径
    
    Returns:
        jsonlist -- 列表:{'videoname','videopath','thumb'}
    """
    thumb_size, thumb_prefix, thumb_web_prefix = thumb_info
    json_list = []
    # 1. 转换文件名到路径，2.同时生成略缩图：400*300
    for index, cpdic in enumerate(result_list):
        cpdic = deepcopy(cpdic)
        cpdic['videopath'] = cpdic['videoname']
        cpdic['videoname'] = cpdic['videopath'].split('/')[-1]

        # 截图
        thumb_name = cpdic['videoname'].split(".")[0] +"_v_" +".jpg"
        thumb_path = os.path.join(thumb_prefix,thumb_name)
        if os.path.exists(thumb_path):
            pass
        else:
            st = 16.0
            pt = cpdic['videopath']
            mkthumb(thumb_size, st, pt, thumb_path)
        cpdic['thumb'] = thumb_web_prefix + thumb_name
        json_list.append(cpdic)
    return json_list    

def make_scene_thumb(thumb_info, result_list, isObj=True):
    """将场景结果列表转换为前端接收的json列表,并创建略缩图
    
    Arguments:
        thumb_info {()}:
            thumb_size {string} -- 略缩图大小
            thumb_prefix {string} -- 略缩图前缀
            thumb_web_prefix {string} -- 略缩图所在网站路径
        result_list {list} -- 场景信息列表
    
    Keyword Arguments:
        isObj {bool} -- 是否为SceneInfo对象列表 (default: {True})
    
    Returns:
        jsonlist -- 列表:{'videoname','videopath','thumb',starttime,sceneid,length}
    """
    thumb_size, thumb_prefix, thumb_web_prefix = thumb_info    
    json_list = []
    # 1. 转换文件名到路径，2.同时生成略缩图：400*300
    # 同时查询到当前场景的人物,物体
    for index, re in enumerate(result_list):
        if isObj:
            cpdic = deepcopy(re.dic)
        else:
            cpdic = deepcopy(re)
        cpdic['videopath'] = cpdic['videoname']
        cpdic['videoname'] = cpdic['videopath'].split('/')[-1]

        # print(str(index) +" " +videopath)

        # 截图
        thumb_name = cpdic['videoname'].split(".")[0] +"_s_"+str(cpdic['sceneid']) +".jpg"
        thumb_path = os.path.join(thumb_prefix,thumb_name)
        if os.path.exists(thumb_path):
            pass
        else:
            st = cpdic['starttime']
            pt = cpdic['videopath']
            # thumb_size, timestamp, full_videoname, image_name
            st = float(st)
            mkthumb(thumb_size, st, pt, thumb_path)
        cpdic['thumb'] = thumb_web_prefix + thumb_name
        json_list.append(cpdic)
    return json_list

def extrace_ids(resultlist):
    sceneids = [item.dic['sceneid'] for item in resultlist]
    videoids = [item.dic['videoid'] for item in resultlist]
    return sceneids, videoids

def read_person_info(personinfo_dir, pid):
    """读人物信息文件
    
    Arguments:
        pid {int} -- 人物id
    """
    content = ''
    filename = personinfo_dir + '/' + str(pid) + '.txt'
    with open(filename, 'r',encoding='utf8') as f:
        content = f.read()
    return content

def saveDisJson(distance, ud, dis_type):
    """将距离数据存到json文件中
    """
    dis_withid = []
    # 将distance编号
    for index, dis in enumerate(distance):
        ndis = []
        ndis.append(index+1)
        ndis.append(dis)        
        dis_withid.append(ndis)

    f_name = 'Data/Videos/UUID/' + ud + "_"+dis_type + "_dist.json"
    with open('/var/www/html/SiteVideo/'+f_name,'w',encoding='utf8') as f:
        f.write(str(dis_withid))

def genPoint(name, size, category, color, fontsize, fixed=False, x=0, y=0,):
    point_dic = {}
    point_dic['name'] = name
    point_dic['symbolSize'] = size
    if category != '':
        point_dic['category'] = category
    
    if color != '':
        itemstyle = {}
        itemstyle['color'] = color
        point_dic['itemStyle'] = itemstyle
        
    label = {}
    label['fontSize'] = fontsize
    point_dic['label'] = label
    point_dic['draggable'] = not fixed
    if fixed:
        point_dic['fixed'] = True
        point_dic['x'] = x
        point_dic['y'] = y        
        
    return point_dic

def genEdge(source, target):
    edge_dic = {}
    edge_dic['source'] = source
    edge_dic['target'] = target
    return edge_dic

def generateRelationJson(ud, result_dic, haskeywords=False):
    point_list = []
    edge_list  = []  
    name_list = []
    colors = ['#FFAB40', '#4CAF50','#C0CA33', '#EF5350']
    if 'content_scene_list' in result_dic.keys():      
        point_list.append(genPoint('图像',40,'图像', '', 30, True, 300, 500))

    if 'face_scene_list' in result_dic.keys():
        point_list.append(genPoint('人脸',40,'人脸', '', 30, True, 760, 500)) 

    if 'keywords_scene_list' in result_dic.keys():
        point_list.append(genPoint('关键词',40,'关键词', '', 30, True, 530, 100))  

    if len(point_list) == 1:
       point_list[0]['x'] = 600
       point_list[0]['y'] = 300     
    elif len(point_list) == 2:
       point_list[0]['x'] = 400
       point_list[0]['y'] = 300 
       point_list[1]['x'] = 800
       point_list[1]['y'] = 300 

    name_set = set()
    for scene in result_dic['both_scene_list']:
        pname = str(scene['sceneid']) 
        if pname not in name_set:
            point_list.append(genPoint(pname, 5,'', colors[1], 10))             
            name_set.add(pname)        

    for scene in result_dic['face_scene_list']:
        # pname = str(hex(face_scene['sceneid']))[2:]
        pname = str(scene['sceneid'])  
        if pname not in name_set:    
            point_list.append(genPoint(pname, 5,'人脸', '' ,10))
            name_set.add(pname)
        edge_list.append(genEdge('人脸', pname))

    for scene in result_dic['content_scene_list']:
        pname = str(scene['sceneid'])    
        if pname not in name_set:    
            point_list.append(genPoint(pname, 5,'图像', '',10))
            name_set.add(pname) 
        edge_list.append(genEdge('图像', pname))
    
    if haskeywords: 
        for scene in result_dic['keywords_scene_list']:
            pname = str(scene['sceneid'])
            if pname not in name_set:    
                point_list.append(genPoint(pname, 5,'关键词', '',10))
                name_set.add(pname)               
            edge_list.append(genEdge('关键词', pname))
    
    relation_data = {}
    relation_data['data'] = point_list
    relation_data['edge'] = edge_list
    
    f_name = 'Data/Videos/UUID/' + ud + "_"+"_relation.json"
    with open('/var/www/html/SiteVideo/'+f_name,'w',encoding='utf8') as f:
        json_str = json.dumps(relation_data,cls=MyEncoder)
        f.write(json_str) 

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

if __name__ == "__main__":
    testlist = [123,23,45]
    saveDisJson(testlist,'xxx','test')