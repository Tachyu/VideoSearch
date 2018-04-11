import os
import logging
import configparser
import queue
import threading
import time
import copy



class BasicPart:

    def __init__(self, logfile = None, isShow=False):
        self.isShow = isShow
        self.config = configparser.ConfigParser()
        self.config.read('Config/config.ini')
        self.read_config()

        if logfile != None:
            logging.basicConfig(
                level=logging.INFO, 
                format='[%(levelname)s] %(asctime)s %(message)s',
                filename=logfile)
        else:#print to screen
            logging.basicConfig(
                level=logging.INFO, 
                format='[%(levelname)s] %(asctime)s %(message)s')
        logging.info(self.__class__.__name__+ "\tINITING...")        
        self.output_queue  = queue.Queue()
        self.out_over_lock = threading.Lock()
        self.out_over_lock.acquire()  
    
    def getOutputQueueAndLock(self):
        return self.output_queue, self.out_over_lock
    
    def startThread(self, input_queue, input_lock):
        logging.info(self.__class__.__name__+": StartThread")
        self.input_Queue = input_queue
        self.input_over_lock = input_lock
        threading.Thread(target=self.process_thread).start()
    
    def process(self, item):
        pass

    def read_config(self):
        pass

    def after_process(self):
        pass

    def lg(self, infomation):
        if self.isShow:
            logging.info(self.__class__.__name__+ ": "+infomation)

    def process_thread(self):
        logging.info(self.__class__.__name__+ ": process_thread START")                
        isProcessOver = False
        # 跳出循环条件：处理结束且队列为空
        while not self.input_Queue.empty() or not isProcessOver:
            # 非阻塞
            item = None
            try:
                item = self.input_Queue.get(False)
            except queue.Empty:
                if isProcessOver:
                    break
                else:
                    time.sleep(0.1)
            # 处理   
            if item != None:
                self.process(item)

            # 处理结束
            if self.input_over_lock.acquire(False):
                isProcessOver = True
        # 完毕
        self.out_over_lock.release()
        logging.info(self.__class__.__name__+ ": process_thread OVER")   
        self.after_process()
