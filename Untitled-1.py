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
        

    def info(self):
        print("fatherprint")        
        pass


class Child(Parent): 
    "定义子类"
    def __init__(self):
        pass

    def info(self):
        print("sonprint")


c = Child()          # 实例化子类
c.parentMethod()      # 调用子类的方法