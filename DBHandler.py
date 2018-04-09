import datetime
import time
import subprocess
import os
import psycopg2
import configparser

class DBHandler:
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
        video_id = None
        if not os.path.exists(videoname): 
            print('filename: %s not found.'%videoname)
        else:
            duration = self.__getSeconds(videoname)
            video_id = self.calldbproc([
            '"public"."AddVideo"',
             str(videoname), 
             float(duration), 
             None,            
             str(descrip)])
        return video_id
    
    def calldbproc(self, args):
        cursor = self.connection.cursor()                    
        cursor.callproc(args[0],args[1:])
        newid  = None            
        for re in cursor:
            newid = re[0]
        return newid

    def excutesql(self, sql, args, isFetch=True):
        cursor = self.connection.cursor()                    
        cursor.execute(sql, args)
        newid  = None       
        if isFetch:     
            for re in cursor:
                newid = re[0]
        return newid

    def addSceneInfo(self, videoid, starttime, length):
         """增加场景信息
         
         Arguments:
             videoid {视频id} -- int
             starttime {开始时间} -- float秒
             length {持续时间} -- float秒
         """
         scene_id = self.calldbproc([
        '"public"."AddScene"',
         int(videoid),
         float(starttime),
         float(length)])
         return scene_id
    
    def __addmany(self, tablename, arglist):

    def addmanySceneInfo(self, videoids, starttimes, lengths):
        """批量快速添加场景信息
            返回添加的场景信息id列表
        Arguments:
            videoids {数组} -- 视频id数组
            starttimes {开始时间数组} -- list
            lengths {持续时间数组} -- list
        """
        s1_sql  = 'SELECT nextval(%s::regclass)'
        s1_args = ['"SceneInfo_SceneId_seq"']
        nextval = self.excutesql(s1_sql, s1_args)

        s2_args = []
        s2_sql = 'INSERT INTO "SceneInfo" VALUES'         
        for i, st in enumerate(starttimes):
            # s2_args.append(None)
            s2_args.append(videoids[i])
            s2_args.append(st)
            s2_args.append(lengths[i])
            s2_sql += ('(DEFAULT, %s, %s, %s),')
        s2_sql = s2_sql[0:len(s2_sql) - 1]
        
        self.excutesql(s2_sql, s2_args, False)
        s3_sql  = 'SELECT currval(%s::regclass)'
        s3_args = ['"SceneInfo_SceneId_seq"']
        currval = self.excutesql(s3_sql, s3_args)

        return list(range(nextval+1, currval+1, 1))


    def addmanyFaceFeats(self, sceneids, personids):
        """批量快速添加人脸特征信息
            返回添加的人脸特征信息id列表
        Arguments:
            sceneids  {int} --  场景id列表
            personids {int} --人物id列表
        """
        s1_sql  = 'SELECT nextval(%s::regclass)'
        s1_args = ['"FaceInfo_FaceFeatId_seq"']
        nextval = self.excutesql(s1_sql, s1_args)

        s2_args = []
        s2_sql = 'INSERT INTO "FaceInfo" VALUES'         
        for i, sd in enumerate(sceneids):
            s2_args.append(sd)
            s2_args.append(personids[i])
            s2_sql += ('(DEFAULT, %s, %s),')
        s2_sql = s2_sql[0:len(s2_sql) - 1]
        self.excutesql(s2_sql, s2_args, False)

        s3_sql  = 'SELECT currval(%s::regclass)'
        s3_args = ['"FaceInfo_FaceFeatId_seq"']
        currval = self.excutesql(s3_sql, s3_args)
        return list(range(nextval+1, currval+1, 1))

    def commit(self):
        """将视频信息提交数据库
        """
        self.connection.commit()

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
    handler = DBHandler()
    # handler.addVideoInfo("Data/Videos/demo.mp4", "Python Test")    
    # handler.addSceneInfo(47, 0.0, 1.0)   
    # result = handler.addmanySceneInfo(47, [1,2,3],[4,5,6])  
    result = handler.addmanyFaceFeats([37,37,37],[1,1,1])        
    print(result)
    infos  = handler.commit()