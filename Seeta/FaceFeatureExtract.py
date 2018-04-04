from pyseeta import Detector
from pyseeta import Aligner
from pyseeta import Identifier
import os
import logging
import uuid

try:
    from PIL import Image, ImageDraw
    import numpy as np
except ImportError:
    raise ImportError('Pillow can not be found!')

class FaceFeatureExtract():
    '''
        提取图片中人脸特征并存储
        2018/3/30 V1.0
    '''
    images_name = []

    isShow = None
    detector = None
    aligner = None
    identifier = None

    def __init__(self, treshhold=20, single=False, logfile=None, pics_dir='data', isShow=True):
        '''
            single:  是否为处理单个图片的模式
            logfile: 日志文件路径
            pics_dir:若single为False则图片文件夹路径
                     若single为True则图片路径
            isShow:  显示图片处理过程
            
        '''
        self.detector = Detector()
        self.aligner = Aligner()
        self.identifier = Identifier()

        self.detector.set_min_face_size(treshhold)
        if not single:
            all_files = os.listdir(pics_dir)

            for f in all_files:
                if not os.path.isdir(f):
                    self.images_name.append(os.path.join(pics_dir,f))
        else:
            self.images_name.append(pics_dir)
        
        self.images_name.sort()

        if logfile == None:
            logging.basicConfig(level=logging.INFO, 
            format='%(levelname)s-%(lineno)d-%(asctime)s  %(message)s',
            filename=logfile)
        else:#print to screen
            logging.basicConfig(level=logging.INFO, 
            format='%(levelname)s-%(lineno)d-%(asctime)s  [FaceFeatureExtract]: %(message)s')
        self.isShow = isShow

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
    
    def release(self):
        '''
            释放资源
        '''
        self.detector.release()
        self.aligner.release()
        self.identifier.release()
    
if __name__ == '__main__':
    extractor = FaceFeatureExtract(treshhold=60, isShow=False)
    dic_list = extractor.detect()
    extractor.release()



