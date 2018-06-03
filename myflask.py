from gevent import monkey
monkey.patch_all()
from flask import Flask
from flask import request,make_response,jsonify
from flask_cors import *
from gevent import wsgi
import json
import os,uuid
from werkzeug import secure_filename
import os
import time



app = Flask(__name__)
face_thresh = 400
cont_thresh = 400
prefix = '/var/www/html/SiteVideo/upload/'
web_prefix = 'upload/' 

def savepicture(picdata):
    pic_name = secure_filename(picdata.filename)
    img_path = os.path.join(prefix,pic_name)
    picdata.save(img_path)
    upload_path = web_prefix + pic_name
    return locale_path,upload_path

@app.route('/')
def hello_world():
    return 'Hello World!'

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
    picdata = request.files['file']
    picdata.save(picdata.filename)
    print(picdata.filename)
    time.sleep(3)
    # print(request.form)
    ud = str(uuid.uuid4())
    js_name = 'Data/Videos/UUID/' + ud + ".json"
    message = {}
    message['jsname'] = ud
    s = 'H:/xampp/htdocs/SiteVideo/'
    with open('/var/www/html/SiteVideo/'+js_name,'w',encoding='utf8') as js:
        js.write(testjson)
    # basedir = os.path.abspath(os.path.dirname(__file__))

    # print(picdata.filename)
    # img_path = os.path.join(basedir,secure_filename(picdata.filename))
    # picdata.save(img_path)

    # excute_search()
    
    # message['imagename'] = img_path
    # print("RETURE RESPONSE")
    return response_to(message,False)

@app.route('/jointsearch', methods=['POST'])
def jointsearch():
    time_start=time.time();
    keywords = request.form['keywords']  
    print(keywords)
    # print(request.form.get('file',None))
    # print(request.files.get('file',None))
    picdata = request.files['file']
    # picdata  = request.form['picture']
    # print(picdata)

    time_stop=time.time()
    result_dic = {}


    # ud, message = writetojson(result_dic)
    return response_to(None,False)

@app.route('/setthresh', methods=['POST'])
def setthresh():
    face_thresh = request.form['face_thresh']
    cont_thresh = request.form['content_thresh']
    message = {}
    message['jsname'] = 'OK'
    return response_to(message, False)

@app.route('/searchkeywords', methods=['POST'])
def search():
    keywords = request.form['keywords']
    time.sleep(1)
    print(keywords)
    message = {}
    message['jsname'] = 'OK'
    return response_to(message, False)

if __name__ == '__main__':   
    server = wsgi.WSGIServer(('0.0.0.0', 5000), app)
    server.serve_forever()