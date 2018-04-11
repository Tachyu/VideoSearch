#-*- coding:utf-8 -*-
from googletrans import Translator
import sys
from queue import Queue
import threading
import time

translator = Translator()
content = ''
with open('model_data/coco_classes.txt','r') as ori_file:
    content = ori_file.read()
# print(content)

#translate
lines = content.split('\n')
# A_part = lines[:len(lines)/2]
# B_part = lines[len(lines)/2:]
# print(len(A_part))
# print(len(B_part))
# # time.sleep(5)
# lines = A_part
# lines = B_part

lineQ = Queue()
tranQ = Queue()

for index, line in enumerate(lines):
    dic = {}
    dic['index'] = index
    dic['content'] = line
    lineQ.put(dic)

tran_thread_num = 5

finish_lock = threading.Lock()
finish_num = 1

def translate_thread():
    print(threading.current_thread().getName()+ " is start")
    global finish_num,finish_lock
    while not lineQ.empty():
        orignal = lineQ.get()
        oritext = orignal['content']
        orignal['content'] = translator.translate(oritext, dest='zh-cn').text
        time.sleep(0.1)
        tranQ.put(orignal)
        print(str(orignal['index']) + '\t' +oritext + " -> " +orignal['content'])
    finish_lock.acquire()
    print("\t[" + str(finish_num) + " / "+ str(tran_thread_num) + "] is Done!")
    finish_num += 1
    finish_lock.release()

tran_thread_pool = []
for i in range(tran_thread_num):
    new_thread= threading.Thread(target=translate_thread)
    tran_thread_pool.append(new_thread)

# start threads
for thread in tran_thread_pool:
    thread.start()

while finish_num <= tran_thread_num:
    time.sleep(1)

dic_list = []
while not tranQ.empty():
    dic_list.append(tranQ.get())

# sort
dic_list = sorted(dic_list,key = lambda x:x['index'],reverse = False)    
print(len(dic_list))

with open('model_data/coco_chinese_classes.txt','w') as tra_file:
    for c in dic_list:
        tra_file.write(c['content'] + '\n')        
        # tra_file.write(str(c['index']) + '\t' + c['content'] + '\n')

# print translator.translate('今天天气不错').text
# print translator.translate('今天天气不错', dest='ja').text
# print translator.translate('今天天气不错', dest='ko').text