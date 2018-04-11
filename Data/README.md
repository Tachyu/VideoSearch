# Data说明
---
## Content:
Path： Data/Content
### 用于存储从场景图像中提取出的特征文件.
>以视频为单位存储，每一个视频对应一个pkl文件
>>**命名格式：**
>>videoid_sf.pkl 例如 12_sf.pkl
>>
>>**数据格式：**
>>```
>>[{
>>    'sfid' : 123,
>>    'feat' : [12312,21312,....]
>>}, ]```

## Faces:
Path： Data/Faces
### 用于存储人脸特征图像.
### Faces/Feats:
Path：Data/Faces/Feats
>用于存储视频中提取的人脸特征，以视频为单位存储，每一个视频对应一个pkl文件
>>**命名格式：**
>>videoid_ff.pkl 例如 12_ff.pkl
>>
>>**数据格式：**
>>```
>>[{
>>    'ffid'   : 123,
>>    'feat' : [12312,21312,....]
>>}, ]```

### Faces/Person:
Path: Data/Faces/Person
>用于存储特定人物的特征，以<b>人名id</b>为单位存储,后缀为pkl
>>**命名格式：**
>>personid_ff.pkl 例如 1_ff.pkl
>>
>>**数据格式：**
>>```
>>[{
>>    'ffid'    : 123,
>>    'feat' : [12312,21312,....]
>>}, ]```

## Objects:
Path： Data/Objects
### 用于存储从场景图像中识别出的物体.
>以视频为单位存储，每一个视频对应一个pkl文件
>>**命名格式：**
>>videoid_ob.pkl 例如 12_ob.pkl
>>
>>**数据格式：**
>>```
>>[{
>>    'picid' : 123,
>>    'objs' : ['人','汽车',....],
>>    'boxes':list
>>}, ]```

## Videos
Path: Data/Videos
>用于存储视频（暂时）
