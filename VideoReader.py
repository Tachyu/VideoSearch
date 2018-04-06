import datetime
import time
import subprocess
import os
import psycopg2
import configparser

class VideoReader:
    """读取视频,并将信息存入数据库
    """
    def __init__(self):
        self.videoinfos = [] 
        conf = configparser.ConfigParser()
        try:
            conf.read("Config/config.ini")
            self.connection = psycopg2.connect(
                database = conf.get('database', 'database'), 
                user     = conf.get('database', 'user'), 
                password = conf.get('database', 'password'), 
                host     = conf.get('database', 'host'), 
                port     = conf.get('database', 'port')) 
        except FileNotFoundError:
            print("Config/config.ini Not Found.")
        except Exception as e:
            print(e)
            print("Failed to connect to database.")
        
        print("Successfully connect to database.")
    
    def addVideoInfo(self, videoname, descrip):
        """增加视频信息
        
        Arguments:
            videoname {string} -- 视频名
            descrip {string} -- 视频描述
        """
        if os.path.exists(videoname): 
            duration           = self.__getSeconds(videoname)
            v_info             = {}
            v_info['name']     = videoname
            v_info['descrip']  = descrip
            v_info['duration'] = duration
            self.videoinfos.append(v_info)
        else:
            print('filename: %s not found.'%videoname)
    
    def commit(self):
        """将视频信息提交数据库， 并将添加后的视频信息返回
        """
        cursor = self.connection.cursor()
        for info in self.videoinfos:
            # "videoname" varchar, 
            # "videolength" float8, 
            # "addtime" timestamptz, 
            # "description" text
            cursor.callproc(
                '"public"."AddVideo"',
            [
                str(info['name']), 
                float(info['duration']),
                None,
                str(info['descrip'])
            ])
            for re in cursor:
                video_id = re[0]
            info['video_id'] = video_id
        self.connection.commit()
        return self.videoinfos

    def __getSeconds(self, videoname):
        """返回视频长度（秒）
        """
        a          = subprocess.getoutput('ffmpeg -i '+videoname)
        infos      = a.split('Duration:')[1].split(', start:')[0]
        vlength    = infos.strip()
        fl_seconds = float(vlength.split('.')[1]) / 100
        vlength    = vlength.split('.')[0]
        times      = vlength.split(":")
        duration   = datetime.timedelta(
        seconds    = int(times[2]),
        minutes    = int(times[1]), 
        hours      = int(times[0]))
        sc         = duration.total_seconds() + fl_seconds
        return sc
    
    def __del__(self):
        self.connection.close() 

if __name__ == "__main__":
    reader = VideoReader()
    reader.addVideoInfo("Data/Videos/demo.mp4", "Python Test")    
    infos  = reader.commit()
    print(infos)