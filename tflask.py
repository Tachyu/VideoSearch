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

g = tf.Graph()
with g.as_default():
    ms = MainSearch(prefix='0825-1031-1030', max_len = 20, imagename="Data/Tmp/tmp.png",isShow=True)
    ms.load_index()
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

@app.route('/uploadpicture', methods=['POST'])
def uploadpic():
    testjson    = '''
    {
    "response_id":"12",
    "face_scene_num":"12",
    "face_scene_list":[
{
    "videoid":1,
    "videoname":"20170701.mp4",
    "addtime":"2017/07/01 11:00:00",  
    "sceneid":1,  
    "starttime":10,
    "length":5,
    "objects":"人，桌子，椅子",
    "videopath":"Data/Video/20170701_tiny.mp4",
    "thumb":"Data/thumbs/20170701_1.jpg"
}],
    "content_scene_num":"12",
    "content_scene_list":[
{
    "videoid":1,
    "videoname":"20170701.mp4",
    "addtime":"2017/07/01 11:00:00",  
    "sceneid":1,  
    "starttime":10,
    "length":5,
    "objects":"人，桌子，椅子",
    "videopath":"Data/Video/20170701_tiny.mp4",
    "thumb":"Data/thumbs/20170701_2.jpg"
}]

}
    '''
    # picid = request.form['id']
    # picdata = request.files['image']
    # print(request)
    # print(request.files['file'])
    prefix = 'Data/Tmp/'
    picdata = request.files['file']
    
    pic_name = picdata.filename
    img_path = os.path.join(prefix,secure_filename(pic_name))
    picdata.save(img_path)
    time.sleep(1)
    with g.as_default():
        ms.chaneg_image(img_path)
        testjson = ms.get_search_result_JSON()

    ud = str(uuid.uuid4())
    js_name = 'Data/Videos/UUID/' + ud + ".json"
    message = {}
    message['jsname'] = ud
    s = 'H:/xampp/htdocs/SiteVideo/'
    with open('/var/www/html/SiteVideo/'+js_name,'w',encoding='utf8') as js:
        js.write(testjson)
    # basedir = os.path.abspath(os.path.dirname(__file__))

    # print(picdata.filename)
    
    # picdata.save(img_path)

    # excute_search()
    
    # message['imagename'] = img_path
    # print("RETURE RESPONSE")
    return response_to(message,False)

@app.route('/search', methods=['POST'])
def search():
    keywords = request.form['keywords']
    print(keywords)
    return 'POST '+keydwords


if __name__ == "__main__":
    server = wsgi.WSGIServer(('0.0.0.0', 5000), app)
    server.serve_forever()
