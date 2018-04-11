#!/usr/bin/python
# -*- coding: UTF-8 -*-
import threading
class Parent:        
    "父类"
    def __init__(self):
        pass

    def parentMethod(self):
        threading.Thread(target=self.info).start()
    
    def haha(self):
        pass

    def info(self):
        print("fatherprint")        
        pass


class Child(Parent): 
    "定义子类"
    def __init__(self):
        pass

    def info(self):
        with open('ObjectDetect/yad2k/model_data/coco_chinese_classes.txt','r',encoding='utf8') as f:
            print(f.readlines())
        print("sonprint")


c = Child()          # 实例化子类
c.parentMethod()      # 调用子类的方法