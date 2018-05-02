import threading
import queue
import time
import os
import configparser
import numpy as np
from BasicPart import BasicPart


class SceneMerge(BasicPart):
    """
        场景合并类,依据:开始帧hsv
        1. 合并相邻(或相隔较近)的场景
        2. 选择是否保留一个场景首尾信息
        -以减少后期处理负担
    """
    
    def __init__(self,
        logfile          = None,
        isShow           = False): 
        """初始化
        """
        BasicPart.__init__(self, logfile=logfile, isShow=isShow)
        self.num_pixels  = -1
        # 记录hsv历史数据,保留:{id, relate_id, hsv}
        self.hsv_history  = []
        # 记录缩减的scene数目
        self.reduce_count = 0
        # 总item数
        self.sum_count = 0
        # 向前追溯最远距离
        self.maxdistance  = 10    
    def read_config(self):
        self.threshold        = self.config.getint('sample', 'threshold')  + 5
    
    def calculate_delta(self, hsv_a, hsv_b):
        diff = hsv_a.astype(np.int32) - hsv_b.astype(np.int32)       
        delta_hsv = np.sum(np.abs(diff), axis=(1,2)) / (float(self.num_pixels))
        delta_hsv = np.sum(delta_hsv) / 3.0
        return delta_hsv

    def compare(self, item_a, item_b):
        """比对两个item
            若相似则返回True
        """
        delta = self.calculate_delta(item_a['hsv'],item_b['hsv'])
        # print(delta)
        if delta < self.threshold:
            return True, delta
        else:
            return False, delta

    def MergeItem(self, item):
        # 提取该item的hsv
        curr_id        = item['id']
        curr_hsv       = item['hsv']
        curr_relate_id = curr_id
        hsv_his_Item        = {}
        hsv_his_Item['id']  = curr_id
        hsv_his_Item['hsv'] = curr_hsv
        
        # 第一个场景,无需比对
        if len(self.hsv_history) == 0:
            self.num_pixels = item['hsv'][0].shape[0] * item['hsv'][0].shape[1]
            # print('NUM_PIXELS: ' + str(self.num_pixels))  
            # time.sleep(10)
            pass
        else: 
            # 进行比对
            # 若出现多个匹配对象,则选择delta最小的那个
            # 比对对象:目标item的relate_hsv
            min_delta  = self.threshold * 100
            # 比对过的id
            compared_set = set([])
            for i in range(self.maxdistance):
                compareid = curr_id - i -1
                if compareid < 0:
                    # 比对结束
                    break
                else:
                    # 比对
                    target_id = self.hsv_history[compareid]['relate_id']
                    if target_id in compared_set:
                        continue
                    else:
                        compared_set.add(target_id)
                        isRelated,delta = self.compare(self.hsv_history[target_id],hsv_his_Item)
                        if isRelated:
                            if delta < min_delta:
                                min_delta  = delta
                                curr_relate_id = target_id
                                self.reduce_count += 1
                
        hsv_his_Item['relate_id'] = curr_relate_id
        self.hsv_history.append(hsv_his_Item)
        return curr_relate_id
            
        
    def process(self, item):
        # 重写处理方法 
        # 每进来一个item,去与距离>=1的场景进行匹配
        # 要求: 距离=1,2,所有?
        # TODO:考察对性能的影响
        if item != None:
            if item['id'] == 0 or item['isIN']:
                self.sum_count += 1
                # 为开始帧或场景0, 进行处理,否则
                # 加入处理结果队列
                # relate_id: 为相似scene所在位置,默认为本身
                item['relate_id'] = self.MergeItem(item)
                self.output_queue.put(item)
        else:
            logging.warn("SceneMerge.process: NONE!")
    
    def after_process(self):
        self.lg("REDUCE: %d / %d, percent: %f"%(self.reduce_count, self.sum_count, (self.reduce_count+0.0)/self.sum_count))

if __name__ == '__main__':
    from VideoSample import VideoSample
    vname         = "Data/Videos/20170701.mp4"
    vsample       = VideoSample(isShow = True,save_images=False)
    sceneQ, sceneLock = vsample.sample(vname)

    s_time = time.time()

    sm = SceneMerge(isShow=True)
    output_queue, out_over_lock = sm.getOutputQueueAndLock()
    sm.startThread(sceneQ, sceneLock)
    # time.sleep(3)
    isProcessOver = False
    # 跳出循环条件：处理结束且队列为空
    sum_count = 0
    while not output_queue.empty() or not isProcessOver:
        # 非阻塞
        try:
            sum_count += 1
            sceneitem = output_queue.get(False)
            id = sceneitem['id']
            rid=sceneitem['relate_id']
            if id != rid:
                print(str(id) + " " + str(rid))
        except queue.Empty:
            if isProcessOver:
                break
            else:
                time.sleep(0.1)
        # 处理结束
        if out_over_lock.acquire(False):
            isProcessOver = True
    e_time = time.time()
    print("REDUCE: %d / %d, percent: %f"%(sm.reduce_count, sum_count, (sm.reduce_count+0.0)/sum_count))
    print("Merge: time = "+str(e_time - s_time))