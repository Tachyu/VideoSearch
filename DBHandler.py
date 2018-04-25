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
            video_id = self.__calldbproc([
            '"public"."AddVideo"',
             str(videoname), 
             float(duration), 
             None,            
             str(descrip)])
        return video_id
    
    def __calldbproc(self, args):
        cursor = self.connection.cursor()                    
        cursor.callproc(args[0],args[1:])
        newid  = None            
        for re in cursor:
            newid = re[0]
        return newid

    def __excutesql(self, sql, args, isFetch=True):
        cursor = self.connection.cursor()                    
        cursor.execute(sql, args)
        newid  = None       
        if isFetch:     
            for re in cursor:
                newid = re[0]
        return newid
    
    def __calldbproc_table(self, args):
        cursor = self.connection.cursor()                    
        cursor.callproc(args[0],args[1:])
        results = []
        for re in cursor:
            results.append(re)
        return results

    def __excutesql_table(self, sql, args):
        cursor = self.connection.cursor()                    
        cursor.execute(sql, args)
        results = []
        for re in cursor:
            results.append(re)
        return results

    def addSceneInfo(self, videoid, starttime, length):
         """增加场景信息
         
         Arguments:
             videoid {视频id} -- int
             starttime {开始时间} -- float秒
             length {持续时间} -- float秒
         """
         scene_id = self.__calldbproc([
        '"public"."AddScene"',
         int(videoid),
         float(starttime),
         float(length)])
         return scene_id
    
    def __addmany(self, tablename, idname, arglists):
        s1_sql  = 'SELECT nextval(%s::regclass)'
        s1_args = ['"%s_%s_seq"'%(tablename, idname)]
        nextval = self.__excutesql(s1_sql, s1_args)
        # print(nextval)
        s2_args = []
        size    = len(arglists[0])
        s2_sql = 'INSERT INTO "%s" VALUES'%tablename         
        for i in range(size):
            s2_sql += '(DEFAULT,'
            # s2_args.append(nextval + i)
            for lis in arglists:
                s2_args.append(lis[i])
                s2_sql += ('%s,')
            # s2_sql += ('(DEFAULT, %s, %s, %s),')
            s2_sql = s2_sql[0:len(s2_sql) - 1]
            s2_sql += '),'
        s2_sql = s2_sql[0:len(s2_sql) - 1]
        self.__excutesql(s2_sql, s2_args, False)

        s3_sql  = 'SELECT currval(%s::regclass)'
        s3_args = ['"%s_%s_seq"'%(tablename, idname)]
        currval = self.__excutesql(s3_sql, s3_args)

        return list(range(nextval+1, currval+1, 1))

    def addmanySceneInfo(self, videoids, starttimes, lengths):
        """批量快速添加场景信息
            返回添加的场景信息id列表
        Arguments:
            videoids {数组} -- 视频id数组
            starttimes {开始时间数组} -- list
            lengths {持续时间数组} -- list
        """
        return self.__addmany('SceneInfo','SceneId',[videoids,starttimes,lengths])


    def addmanyFaceFeats(self, sceneids, personids):
        """批量快速添加人脸特征信息
            返回添加的人脸特征信息id列表
        Arguments:
            sceneids  {int} --  场景id列表
            personids {int} --人物id列表
        """
        return self.__addmany('FaceInfo','FaceFeatId',[sceneids, personids])

    def addmanyPicFeats(self, sceneids):
        """批量快速添加图像特征信息
            返回添加的图像特征信息id列表
        Arguments:
            sceneids  {int} --  场景id列表
        """
        return self.__addmany('PicInfo','PicFeatId',[sceneids])
    def test(self, picid):
        results = self.__calldbproc_table([
            '"public"."querypic"',
             int(picid)])
        print(results)

    def search_scene_video_info_by_picid(self, picid):
        """根据picid来查询对应的图片，场景以及视频信息
        result_dic['sceneid']   = results[0][0]
        result_dic['videoid']   = results[0][1]
        result_dic['videoname'] = results[0][2]
        result_dic['starttime'] = results[0][3]
        result_dic['length']    = results[0][4]
        """

        results = self.__calldbproc_table([
            '"public"."querypic"',
             int(picid)])

        result_dic              = {}
        result_dic['sceneid']   = results[0][0]
        result_dic['videoid']   = results[0][1]
        result_dic['videoname'] = results[0][2]
        result_dic['starttime'] = results[0][3]
        result_dic['length']    = results[0][4]
        return result_dic

    def search_scene_video_info_by_faceid(self, faceid):
        '''
        result_dic['sceneid']   = results[0][0]
        result_dic['videoid']   = results[0][1]
        result_dic['videoname'] = results[0][2]
        result_dic['starttime'] = results[0][3]
        result_dic['length']    = results[0][4]
        '''
        sql = '''
        SELECT
            "public"."SceneInfo"."SceneId",
            "public"."VideoId"."VideoId",
            "public"."VideoId"."VideoName",
            "public"."SceneInfo"."StartTime",
            "public"."SceneInfo"."Length"
        FROM
            "public"."SceneInfo",
            "public"."VideoId" 
        WHERE
            "public"."SceneInfo"."SceneId" = (
        SELECT
            "public"."PicInfo"."SceenId"
        FROM
            "public"."PicInfo" 
            WHERE 
            "public"."PicInfo"."PicFeatId"= ( 
            SELECT 
            "public"."FaceInfo"."PicId" 
            FROM 
            "public"."FaceInfo" 
            WHERE 
            "public"."FaceInfo"."FaceFeatId" = %s ))
            AND "public"."SceneInfo"."VideoId"="public"."VideoId"."VideoId" ;
        '''
        results                 = self.__excutesql_table(sql, [faceid])
        result_dic              = {}
        result_dic['sceneid']   = results[0][0]
        result_dic['videoid']   = results[0][1]
        result_dic['videoname'] = results[0][2]
        result_dic['starttime'] = results[0][3]
        result_dic['length']    = results[0][4]
        return result_dic

    def search_videoinfo_by_videoid(self, videoid):
        """根据faceid来查询对应的图片，场景以及视频信息
        """
        sql = '''
        SELECT
            "public"."VideoId"."VideoId",
            "public"."VideoId"."VideoName",
            "public"."VideoInfo"."Length",
            "public"."VideoInfo"."AddTime",
            "public"."VideoInfo"."Descrption" 
        FROM
            "public"."VideoInfo",
            "public"."VideoId" 
        WHERE
            "public"."VideoId"."VideoId" = %s 
            AND "public"."VideoInfo"."VideoId" = "public"."VideoId"."VideoId";
        '''
        results                  = self.__excutesql_table(sql, [videoid])
        result_dic               = {}
        result_dic['videoid']    = results[0][0]        
        result_dic['videoname']   = results[0][1]
        result_dic['length']     = results[0][2]
        result_dic['addtime']    = results[0][3].strftime('%Y-%m-%d %H:%M:%S')        
        result_dic['description'] = results[0][4]
        return result_dic   
        
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
        self.connection.commit()
        self.connection.close() 

if __name__ == "__main__":
    handler = DBHandler()
    # handler.addVideoInfo("Data/Videos/demo.mp4", "Python Test")    
    # handler.addSceneInfo(47, 0.0, 1.0)   
    # result = handler.addmanySceneInfo([47,47,47], [1,2,3],[4,5,6])  
    # result = handler.addmanyFaceFeats([37,37,37],[1,1,1])  
    # result = handler.addmanyPicFeats([37,39,41])      
    # print(result)
    info = handler.search_scene_video_info_by_faceid(339)
    print(info)

    info = handler.search_scene_video_info_by_picid(101)
    print(info)

    info = handler.search_videoinfo_by_videoid(88)
    print(info)
    # infos  = handler.commit()