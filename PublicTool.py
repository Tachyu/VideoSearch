# coding:utf-8
"""一些公用的函数
"""
import os, requests, json, subprocess
import numpy as np

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
    a = subprocess.getoutput(cmd)


def to_json_video(thumb_info,result_list):
    """将视频结果列表转换为前端接收的json列表,并创建略缩图
    
    Arguments:
        thumb_info {()}:
            thumb_size {string} -- 略缩图大小
            thumb_prefix {string} -- 略缩图前缀
            thumb_web_prefix {string} -- 略缩图所在网站路径
    
    Returns:
        jsonlist -- 列表
    """
    thumb_size, thumb_prefix, thumb_web_prefix = thumb_info
    json_list = []
    # 1. 转换文件名到路径，2.同时生成略缩图：400*300
    for index, cpdic in enumerate(result_list):
        videopath = cpdic['videoname']
        video_name = videopath.split('/')[-1]
        cpdic['videoname'] = video_name
        cpdic['videopath'] = videopath

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

def to_json_scene(thumb_info, result_list, isObj=True):
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
        jsonlist -- 列表
    """
    thumb_size, thumb_prefix, thumb_web_prefix = thumb_info    
    json_list = []
    # 1. 转换文件名到路径，2.同时生成略缩图：400*300
    # 同时查询到当前场景的人物,物体
    for index, re in enumerate(result_list):
        if isObj:
            cpdic = re.dic
        else:
            cpdic = re
        videopath = cpdic['videoname']
        video_name = videopath.split('/')[-1]
        cpdic['videoname'] = video_name
        cpdic['videopath'] = videopath
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