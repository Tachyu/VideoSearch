# coding:utf-8
###### Sat Mar 31 09:38:34 CST 2018
from __future__ import print_function

import scenedetect as scenedetect
import scenedetect.detectors as detectors
import scenedetect.manager as manager

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
        save_images      = True):
        """初始化
        
        Keyword Arguments:
            useconfig {bool} -- 是否读配置文件
            threshold {int} -- 阈值 (default: {30})
            frame_skip {int} -- 跳帧 (default: {0})
            downscale_factor {int} -- 压缩率 (default: {50})
            save_images {bool} -- 是否存储采样图片 (default: {True})
        """
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

    def sample(self, videoname):
        """对视频进行取样并返回场景信息
        
        Arguments:
            videoname {string} -- 视频文件名
        """
        smgr = manager.SceneManager(
        detector          = self.content_detector, 
        frame_skip        = self.frame_skip, 
        downscale_factor  = self.downscale_factor, 
        save_images       = self.save_images, 
        save_csv_filename = "tmp.csv", 
        save_image_prefix = 'tmp', 
        perf_update_rate  = 1)
        scenedetect.detect_scenes_file(videoname, smgr)
        return smgr.scene_list


if __name__ == "__main__":
    vname     = "Data/Videos/demo.mp4"
    vsample   = VideoSample(useconfig = True)
    scenelist = vsample.sample(vname)
    print("Detected %d scenes in video" % (len(scenelist)))
    print(scenelist)