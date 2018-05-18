import cv2  
import numpy as np 
from PIL import Image 
from matplotlib import pyplot as plt 
import math
import time

class ComputeSim():
    def readimage(self,name):
        image = cv2.imread(name) 
        return image

    def computehist(self,image):
        pixels = image.shape[0] * image.shape[1]
        image_hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h = cv2.calcHist([image_hsv], [0], None, [180], [0,180])
        s = cv2.calcHist([image_hsv], [1], None, [256], [0,256])
        v = cv2.calcHist([image_hsv], [2], None, [256], [0,256])
        hist = np.vstack(h,s)
        hist = np.vstack(hist,v)        
        return hist

    def showimage(self,image):
        # image = Image.fromarray(cv2.cvtColor(image,cv2.COLOR_HSV2RGB)) 
        image = Image.fromarray(cv2.cvtColor(image,cv2.COLOR_BGR2RGB))  
        image.show() 

    def crop_image(self,image,pointx=0.224,pointy=0.224):
        imagex = image.shape[0]
        imagey = image.shape[1]
        px = int(imagex * pointx)
        py = int(imagey * pointy)
        qx = imagex - px
        qy = imagey - py  
        # t = image[600:1200,750:1500]  
        center = image[px:qx,py:qy]
        '''
        6 | 3 | 0
        7 | 4 | 1
        8 | 5 | 2

        '''
        r1 = image[0:px, qy:imagey]
        r2 = image[px:qx, qy:imagey]
        r3 = image[qx:imagex, qy:imagey]
        r4 = image[0:px, py:qy]
        r5 = image[px:qx,py:qy]
        r6 = image[qx:imagex, py:qy]    
        r7 = image[0:px, 0:py]
        r8 = image[px:qx, 0:py]
        r9 = image[qx:imagex, 0:py]
        regions = []
        regions.append(r1)
        regions.append(r2)
        regions.append(r3)
        regions.append(r4)
        regions.append(r5)
        regions.append(r6)
        regions.append(r7)
        regions.append(r8)
        regions.append(r9)    
        return regions
        
        
    def pshape(self,item):
        print(item.shape)


    def calculate(self,image1,image2):
        weight = [0.7,0.2,0.1]
        p1 = image1.shape[0] * image1.shape[1]
        p2 = image2.shape[0] * image2.shape[1]      
        max_values = [180, 256, 256]
        degrees = []
        for index, max_value in enumerate(max_values):  
            hist1 = cv2.calcHist([image1],[index],None,[max_value],[0.0,max_value]) / p1
            hist2 = cv2.calcHist([image2],[index],None,[max_value],[0.0,max_value]) /p2
            degree = self.calsinglechannel(hist1, hist2)
            # degree = calsinglechannel_trad(hist1, hist2)        
            degrees.append(degree * weight[index])
        return np.sum(degrees) 
    
    def calsinglechannel_trad(self,hist1, hist2):
        #计算直方图的重合度 
        degree = 0 
        for i in range(len(hist1)): 
            if hist1[i] != hist2[i]: 
                degree = degree + (1 - abs(hist1[i]-hist2[i])/max(hist1[i],hist2[i])) 
            else: 
                degree = degree + 1 
        degree = (degree/len(hist1))[0] 
        return degree 

    def calsinglechannel(self,c1, c2):
        base = np.ones_like(c1)
        maxmat = np.maximum(c1, c2)
        nozero = np.nonzero(maxmat) 
        base[nozero] = 1 - np.abs(c1 - c2)[nozero] / maxmat[nozero] 
        degree = np.sum(base) / len(c1)
        return degree
    
    def calculate_delta(self, image1,image2):
        # hsv1 = self.computehist(image1)
        diff = image1.astype(np.int32) - image2.astype(np.int32)
        delta_hsv = np.sum(np.abs(diff), axis=(1,2)) / (float(100))
        delta_hsv = np.append(delta_hsv, np.sum(delta_hsv)/3.0)
        return delta_hsv


    def caldegree(self,image1, image2):
        regions1 = self.crop_image(image1)
        regions2 = self.crop_image(image2) 
        degrees  = [self.calculate(region1,region2) for region1, region2 in zip(regions1,regions2)]
        # 中心区域0.4 周围0.6/8
        center_weight = 0.4
        surrond_weight = (1-center_weight)/8
        degrees = np.array(degrees)
        degrees =  surrond_weight * degrees
        degrees[4] += (int(center_weight / surrond_weight) - 1 ) * degrees[4]
        result = np.sum(degrees)
        return result


if __name__ == '__main__':
    cs = ComputeSim()
    image1 = cs.readimage('t1.JPG')
    image2 = cs.readimage('t2.JPG')
    
    np.random.seed(1234)

    # hist1 = np.random.randint(0,10,(3,10,10))
    # hist2 = np.random.randint(0,10,(3,10,10))
    # print(hist1.shape)
    st = time.time()
    # cs.calculate_np(image1, image2)
    delta = cs.calculate_delta(image1, image2)[3]
    degree = cs.caldegree(image1, image2)
    et = time.time()
    # print(et-st)
    print(delta)
    print(degree)
    
    # caldiff(hists1[4],hists1[4])
    # hsv_mask = [0.9,0.3,0.1]
    # print(hists[0].shape)  
    # # showimage(regions[0])
    # showimage(regions[1])
    # showimage(regions[5])
    
    
    