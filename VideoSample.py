# coding:utf-8
###### Sat Mar 31 09:38:34 CST 2018
from __future__ import print_function

import scenedetect as scenedetect
import scenedetect.detectors as detectors
import scenedetect.manager as manager
import threading
import queue
import time
import os
import configparser

class VideoSample:
    """
        视频采样类
    """
    
    def __init__(self,
        useconfig        = False, 
        threshold        = 30, 
        frame_skip       = 0, 
        downscale_factor = 50, 
        save_images      = True,
        isShow           = False): 
        """初始化
        
        Keyword Arguments:
            useconfig {bool} -- 是否读配置文件
            threshold {int} -- 阈值 (default: {30})
            frame_skip {int} -- 跳帧 (default: {0})
            downscale_factor {int} -- 压缩率 (default: {50})
            save_images {bool} -- 是否存储采样图片 (default: {True})
        """
        self.isShow = isShow
        self.content_detector = detectors.ContentDetector(threshold = threshold)        
        if useconfig:
            conf                  = configparser.ConfigParser()
            conf.read("Config/config.ini")
            self.threshold        = conf.getint('sample', 'threshold')
            self.frame_skip       = conf.getint('sample', 'frame_skip')
            self.downscale_factor = conf.getint('sample', 'downscale_factor')
            self.save_images      = conf.getboolean('sample', 'save_images')
        else:
            self.threshold        = threshold
            self.frame_skip       = frame_skip
            self.downscale_factor = downscale_factor
            self.save_images      = save_images
    
    def __detect_thread(self):
        scenedetect.detect_scenes_file(self.videoname, self.smgr)

    def sample(self, videoname):
        """对视频进行取样并返回场景信息
            对返回值进行修改
        
        Arguments:
            videoname {string} -- 视频文件名
        """
        self.videoname = videoname
        if self.isShow:
            perf_update_rate = 1
        else:
            perf_update_rate = -1
        self.smgr = manager.SceneManager(
        detector          = self.content_detector, 
        frame_skip        = self.frame_skip, 
        downscale_factor  = self.downscale_factor, 
        save_images       = self.save_images, 
        save_csv_filename = "tmp.csv", 
        save_image_prefix = 'tmp',
        quiet_mode = not self.isShow, 
        perf_update_rate  = perf_update_rate)

        # 新线程进行检测，直接返回产生场景数据的队列和锁
        threading.Thread(target   = self.__detect_thread).start()
        pic_queue, pic_queue_lock = self.smgr.getQueueAndLock()
        return pic_queue, pic_queue_lock


if __name__ == "__main__":
    vname         = "Data/Videos/20170701_tiny.mp4"
    vsample       = VideoSample(useconfig = True, isShow = True)
    sceneQ, QLock = vsample.sample(vname)
    isSceneProcessOver = False
    # 跳出循环条件：处理结束且队列为空
    while not sceneQ.empty() or not isSceneProcessOver:
        # 非阻塞
        try:
            sceneitem = sceneQ.get(False)
            # print(sceneitem)
        except queue.Empty:
            if isSceneProcessOver:
                break
            else:
                time.sleep(0.1)
                
        
        # 处理结束
        if QLock.acquire(False):
            isSceneProcessOver = True

        # # 阻塞, 会死锁，已弃用
        # if not isSceneProcessOver:
        #     sceneitem = sceneQ.get()['id']
        #     print(sceneitem)
        # # 处理结束
        # if QLock.acquire(False):
        #     isSceneProcessOver = True

    # print("Detected %d scenes in video" % (len(scenelist)))
    # print(scenelist)