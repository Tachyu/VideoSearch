import cv2
from matplotlib import pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D


img1_url = '/home/zhang/AI/VideoSearch/tmp/3.jpg'
img2_url = '/home/zhang/AI/VideoSearch/tmp/4.jpg'
num_pixels = 0
def getHsv(url):
    global num_pixels
    img = cv2.imread(url,1)
    img = img[::50,::50,:]
    # img = img[::1,::1,:]    
    num_pixels = img.shape[0] * img.shape[1]
    curr_hsv = cv2.split(cv2.cvtColor(img, cv2.COLOR_RGB2HSV))
    curr_hsv = np.array(curr_hsv) 
    return curr_hsv

def cal_diff(hsv_a, hsv_b, var):
    global num_pixels
    # print(num_pixels)
    # 减小亮度变化带来的影响,对HSV的V通道进行衰减,
    # 同时适当增强其他两个通道
    diff = hsv_a.astype(np.int32) - hsv_b.astype(np.int32)
    # print(diff.shape)
    hmask = np.ones((1, diff.shape[1],diff.shape[2]))
    smask = np.ones((1, diff.shape[1],diff.shape[2]))
    vmask = np.ones((1, diff.shape[1],diff.shape[2]))
    
    # print(mask2.shape)        
    hmask = var[0] * hmask
    smask = var[0] * hmask        
    vmask = var[0] * vmask
            
    mask = np.vstack((hmask, smask))
    mask = np.vstack((mask, vmask))

    diff = diff * mask
    # mask =         
    delta_hsv = np.sum(np.abs(diff), axis=(1,2)) / (float(num_pixels))
    delta_hsv = np.append(delta_hsv, np.sum(delta_hsv)/3.0)
    return delta_hsv
hsv_a, hsv_b = getHsv(img1_url), getHsv(img2_url)
values = np.arange(0.1,3,0.1)
deltas = []
minh, minv, mins, mind = 0,0,0,200
for h in values:
    for s in values:
        v = 3-h-s
        delta = cal_diff(hsv_a, hsv_b, (h,s,v))[3]
        deltas.append(delta)
        if delta < mind:
            minh,mins,minv = h,s,v
            mind = delta
        if 30 - delta < 10 and 30 - delta > 0 and v > 0.5:
            print(str((h,s,v)) + " " + str(delta))

print((minh, minv, mins, mind))        
fig = plt.figure()
ax = Axes3D(fig)
X = values
Y = values
X, Y = np.meshgrid(X, Y)
Z = np.array(deltas).reshape(29,29)
# R = np.sqrt(X**2 + Y**2)
# Z = np.sin(R)
# print(Z)

# 具体函数方法可用 help(function) 查看，如：help(ax.plot_surface)
ax.plot_surface(X, Y, Z, rstride=1, cstride=1, cmap='rainbow')

plt.show()    
# cal_diff(getHsv(img1_url), getHsv(img2_url))