from pyseeta import Detector
from pyseeta import Aligner
from pyseeta import Identifier
import os
import logging
import uuid
import configparser
import queue
import threading

try:
    from PIL import Image, ImageDraw
    import numpy as np
except ImportError:
    raise ImportError('Pillow can not be found!')

class FaceRecog():
    """
        人脸识别类
            StartRecongThread(queue, queue_lock)
            人脸识别队列

            __Recognation(img)
            识别图片中的人脸，记录人脸位置，记录特征,给每一张脸一个uuid

            getProcessedQueueAndLock()
            返回处理完毕图片存放的队列和锁

            RecordFaceToDB(faceid, person_name)
            数据库中建立部分脸id与人名的映射
    """
    images_name = []

    def __init__(self, 
        useconfig = True, 
        threshold = 30, 
        logfile   = None, 
        isShow    = False): 
        '''
            useconfig：读取配置文件
            logfile:   日志文件路径
            pics_dir:  若single为False则图片文件夹路径
                       若single为True则图片路径
            isShow:    显示图片处理过程
            
        '''
        self.detector = Detector()
        self.aligner = Aligner()
        self.identifier = Identifier()
        thresh = threshold
        if useconfig:
            config = configparser.ConfigParser()
            config.read('Conf/config.ini')
            thresh = config.getint('face','threshold')
        
        self.detector.set_min_face_size(thresh)

        if logfile == None:
            logging.basicConfig(level=logging.INFO, 
            format='%(levelname)s-%(lineno)d-%(asctime)s  %(message)s',
            filename=logfile)
        else:#print to screen
            logging.basicConfig(level=logging.INFO, 
            format='%(levelname)s-%(lineno)d-%(asctime)s  [FaceFeatureExtract]: %(message)s')
        self.isShow = isShow

        self.output_queue = queue.Queue()
        self.out_over_lock = threading.Lock()
        self.out_over_lock.acquire()

    def getOutputQueueAndLock(self):
        return self.output_queue, self.out_over_lock


    def StartRecongThread(self, img_queue, over_lock):
        """启动识别线程
        
        Arguments:
            img_queue {传入的图片队列} -- queue.Queue
            over_lock {队列生成线程完毕锁}
        """
        self.input_Queue = img_queue
        self.input_over_lock = over_lock
        threading.Thread(target=self.__Recog_Thread).start()
        pass


    def __Recog_Thread(self):
        isSceneProcessOver = False
        # 跳出循环条件：处理结束且队列为空
        while not self.input_Queue.empty() or not isSceneProcessOver:
            # 非阻塞
            try:
                '''
                    pic_out_dict['isIN'] = False
                    pic_out_dict['id'] = num_scenes   
                    pic_out_dict['data'] = last_frame
                '''
                sceneitem = sceneQ.get(False)
            except queue.Empty:
                if isSceneProcessOver:
                    break
                else:
                    time.sleep(0.1)
            # 处理   
            if sceneitem['isIN']:
                name = str(sceneitem['id']) + "_IN_"
            else:
                name = str(sceneitem['id']) + "_OUT"
            sceneitem['name'] = name
            result = self.__Recognation(name, sceneitem['data'])
           
            # 加入处理结果队列
            sceneitem['face_result'] = result
            self.output_queue.put(sceneitem)

            # 处理结束
            if self.input_over_lock.acquire(False):
                isSceneProcessOver = True
        # 完毕
        self.out_over_lock.release()

    def __Recognation(self, name, img):
        # 处理图片(cv格式), 返回feature和landmark信息
        image = img.convert('RGB')
        lands, faces, feats = self.__extract_features(image) 
        logging.info("detecting %s: find %d faces"%(name, len(lands))) 
        if self.isShow:
            image = Image.fromarray(cv2.cvtColor(img,cv2.COLOR_BGR2RGB))  
            draw = ImageDraw.Draw(image)
            for i, face in enumerate(faces):
                draw.rectangle([face.left, face.top, face.right, face.bottom], outline='red') 
            image.show()
        pic_face_dic = {}
        pic_face_dic['landmarks'] = lands
        pic_face_dic['feats']     = feats
        return pic_face_dic

    def detect(self):
        '''
         返回一个字典数组：长度等于图片数。例如：
         [
             {
                 'name':'1.jpg'，
                 'features':[[1,23,...],[2,3,....]],
                 'landmarks':[[1,2,3,4],[5,6,7,8]]                 
              },...
         ]
        '''
        pic_dic_list = []
        for pic in self.images_name:
            image = Image.open(pic).convert('RGB')
            lands, faces, feats = self.__extract_features(image) 
            logging.info("detecting %s: find %d faces"%(pic, len(lands))) 
            if self.isShow:
                draw = ImageDraw.Draw(image)
                for i, face in enumerate(faces):
                    draw.rectangle([face.left, face.top, face.right, face.bottom], outline='red') 
                image.show()
            pic_dic = {}
            pic_dic['name']      = pic
            pic_dic['landmarks'] = lands
            pic_dic['feats']     = feats
            pic_dic_list.append(pic_dic)
        return pic_dic_list


    def __extract_features(self, img):
        # detect face in image
        image_gray = img.convert('L')
        faces = self.detector.detect(image_gray)
                
        feats = []
        landmarks = []
        
        for detect_face in faces:
            landmark = self.aligner.align(image_gray, detect_face)
            landmarks.append(landmark)
            feat = self.identifier.extract_feature_with_crop(img, landmark)
            feats.append(feat)
        return landmarks, faces, feats 
    
    def __del__(self):
        '''
            释放资源
        '''
        self.detector.release()
        self.aligner.release()
        self.identifier.release()
    
if __name__ == '__main__':
    recog = FaceRecog(isShow=True)
    recog.StartRecongThread(img_queue, over_lock):
    
    dic_list = extractor.detect()
    extractor.release()



