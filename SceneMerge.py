import threading
import queue
import time
import os
import configparser
from BasicPart import BasicPart


class SceneMerge(BasicPart):
    """
        场景合并类,
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
    
    def read_config(self):
        self.threshold        = self.config.getint('sample', 'threshold')
    
    def process(self, item):
        # 重写处理方法 
        if item != None:
            if 'name' not in item.keys():
                if item['isIN']:
                    name = str(item['id']) + "_IN_"
                else:
                    name = str(item['id']) + "_OUT"
                item['name'] = name
            result = self.__Recognation(item['name'], item['data'])
        
            # 加入处理结果队列
            item['face_result'] = result
            self.output_queue.put(item)
        else:
            logging.warn("SceneMerge.process: NONE!")