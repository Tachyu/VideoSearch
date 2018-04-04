# coding:utf-8
###### Sat Mar 31 09:38:34 CST 2018
import Scene.scenedetect
import Scene.scenedetect.detectors
import Scene.scenedetect.manager

class VideoSample():
    """
        视频采样类
        V1.0###### Sat Mar 31 09:46:39 CST 2018
    """
    
    def __init__(self, threshold = 30, 
        frame_skip = 0, 
        downscale_factor = 50, 
        save_images = True):
        """初始化
        
        Keyword Arguments:
            threshold {int} -- 阈值 (default: {30})
            frame_skip {int} -- 跳帧 (default: {0})
            downscale_factor {int} -- 压缩率 (default: {50})
            save_images {bool} -- 是否存储采样图片 (default: {True})
        """
        content_detector = scenedetect.detectors.ContentDetector(threshold = threshold)
        self.smgr = scenedetect.manager.SceneManager(detector = content_detector, 
        frame_skip = frame_skip, 
        downscale_factor = downscale_factor, 
        save_images = save_images)

    def sample(self, videoname):
        content_detector = scenedetect.detectors.ContentDetector(threshold = 30)
        smgr = scenedetect.manager.SceneManager(detector =content_detector, 
        frame_skip = 2, downscale_factor = 30, 
        save_images = False, save_csv_filename="2017.csv", save_image_prefix='jj', perf_update_rate=1)
        scenedetect.detect_scenes_file("Videos/20170701_c.mp4", smgr)
        # time_end = time.time()
        # print('SUM time = ' + str(time_end - time_start))
        print("Detected %d scenes in video" % (len(smgr.scene_list)))
        scenedetect.detect_scenes_file(videoname, self.smgr)
        print("Detected %d scenes in video (algorithm = content, threshold = 20)." % (len(smgr.scene_list)))
