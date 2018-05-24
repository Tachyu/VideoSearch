# coding:utf-8
import os
from gevent import monkey
monkey.patch_all()
from flask import Flask
from flask import request,make_response,jsonify
from flask_cors import *
from gevent import wsgi
import json
import os,uuid
from werkzeug import secure_filename
from MainSearch import MainSearch
import tensorflow as tf
import time
from PublicTool import *

face_thresh = 600
cont_thresh = 600
prefix = '/var/www/html/SiteVideo/upload/'
web_prefix = 'upload/'   

g = tf.Graph()
with g.as_default():
    ms = MainSearch(max_len = 120, isShow=True)
    ms.load_index(['0701&0825&1220'],['Person'])

    # 测试图片
    ms.lg("**********test**********")
    ms.setThreshold(0,0)    
    ms.set_image("x.jpg")
    result_dic = ms.searchImage()
    print('Ready Let`s GO!')

app = Flask(__name__)

def savepicture(picdata):
    pic_name = secure_filename(picdata.filename)
    img_path = os.path.join(prefix,pic_name)
    picdata.save(img_path)
    upload_path = web_prefix + pic_name
    return locale_path,upload_path

def response_to(message, iserror):
    resp_dic = {}
    resp_dic['error']   = iserror
    resp_dic['message'] = message
    resp = jsonify(resp_dic)
    # 跨域设置
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

def writetojson(dic_obj):
    # print(json_obj)
    json_str = json.dumps(dic_obj,cls=MyEncoder)
    ud = str(uuid.uuid4())
    js_name = 'Data/Videos/UUID/' + ud + ".json"
    message = {}
    message['jsname'] = ud
    with open('/var/www/html/SiteVideo/'+js_name,'w',encoding='utf8') as js:
        js.write(json_str)
    if 'face_dist_list' in dic_obj.keys():
        saveDisJson(dic_obj['face_dist_list'], ud, 'face')
    if 'content_dist_list' in dic_obj.keys():      
        saveDisJson(dic_obj['content_dist_list'], ud, 'content')
    generateRelationJson(ud, dic_obj)
    return ud, message


@app.route('/uploadpicture', methods=['POST'])
def uploadpic():
    time_start=time.time();
    picdata = request.files['file']
    locale_path, upload_path = savepicture(picdata)
    # time.sleep(1)
    # img_path = "Data/Tmp/A/20171220.mp4.Scene-024-IN.jpg"
    with g.as_default():
        ms.setThreshold(face_thresh, cont_thresh)
        ms.set_image(locale_path)
        result_dic = ms.searchImage()
        
    time_stop=time.time()
    
    result_dic['querytime'] = 1000* (time_stop-time_start)   
    result_dic['uploadpicture'] = upload_path

    ud, message = writetojson(result_dic)

    return response_to(message,False)

@app.route('/search', methods=['POST'])
def search():
    time_start=time.time();
    keywords = request.form['keywords']
    with g.as_default():
        result_dic = ms.searchKeywords(keywords)
    time_stop=time.time()
    result_dic['querytime'] = 1000 * (time_stop-time_start)   
    ud, message = writetojson(result_dic)
    return response_to(message,False)

@app.route('/jointsearch', methods=['POST'])
def jointsearch():
    time_start=time.time();
    keywords = request.form['keywords']    
    locale_path, upload_path = savepicture(picdata)

    with g.as_default():
        ms.setThreshold(face_thresh, cont_thresh)
        result_dic = ms.searchJoint(locale_path, keywords)

    time_stop=time.time()
    result_dic['querytime'] = 1000 * (time_stop-time_start)   
    result_dic['uploadpicture'] = upload_path

    ud, message = writetojson(result_dic)
    return response_to(message,False)

@app.route('/setthresh', methods=['POST'])
def setthresh():
    face_thresh = request.form['face_thresh']
    cont_thresh = request.form['content_thresh']
    message = {}
    message['jsname'] = 'OK'
    return response_to(message, False)


if __name__ == "__main__":
    server = wsgi.WSGIServer(('0.0.0.0', 5000), app)
    server.serve_forever()
