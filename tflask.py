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

face_thresh = 400
cont_thresh = 400

g = tf.Graph()
with g.as_default():
    ms = MainSearch(max_len = 120, isShow=True)
    ms.setThreshold(800,800)
    ms.load_index(['0701&0825&1220'],['Person'])
    print('Ready Let`s GO!')

app = Flask(__name__)


def response_to(message, iserror):
    resp_dic = {}
    resp_dic['error']   = iserror
    resp_dic['message'] = message
    resp = jsonify(resp_dic)
    # 跨域设置
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

def writetojson(json_obj):
    # print(json_obj)
    json_str = json.dumps(json_obj,cls=MyEncoder)
    ud = str(uuid.uuid4())
    js_name = 'Data/Videos/UUID/' + ud + ".json"
    message = {}
    message['jsname'] = ud
    with open('/var/www/html/SiteVideo/'+js_name,'w',encoding='utf8') as js:
        js.write(json_str)
    return ud, message


@app.route('/uploadpicture', methods=['POST'])
def uploadpic():
    time_start=time.time();
    prefix = '/var/www/html/SiteVideo/upload/'
    web_prefix = 'upload/'    
    picdata = request.files['file']
    
    pic_name = secure_filename(picdata.filename)
    img_path = os.path.join(prefix,pic_name)
    picdata.save(img_path)
    # time.sleep(1)
    with g.as_default():
        ms.setThreshold(face_thresh, cont_thresh)
        ms.set_image(img_path)
        testjson = ms.searchImage()
    time_stop=time.time();
    
    testjson['querytime'] = 1000* (time_stop-time_start)   
    testjson['uploadpicture'] = web_prefix + pic_name

    ud, message = writetojson(testjson)

    return response_to(message,False)

@app.route('/search', methods=['POST'])
def search():
    time_start=time.time();
    keywords = request.form['keywords']
    with g.as_default():
        testjson = ms.searchKeywords(keywords)
    time_stop=time.time();
    testjson['querytime'] = 1000* (time_stop-time_start)   

    ud, message = writetojson(testjson)

    return response_to(message,False)

@app.route('/jointsearch', methods=['POST'])
def jointsearch():
    pass
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
