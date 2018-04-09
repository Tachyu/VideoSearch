# Data说明
---
## Content:
Path： Data/Content
### 用于存储从场景图像中提取出的特征文件.
>以视频为单位存储，每一个视频对应一个npy文件
>>**命名格式：**
>>videoid_sf.npy 例如 12_sf.npy
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
>用于存储视频中提取的人脸特征，以视频为单位存储，每一个视频对应一个npy文件
>>**命名格式：**
>>videoid_ff.npy 例如 12_ff.npy
>>
>>**数据格式：**
>>```
>>[{
>>    'ffid'   : 123,
>>    'sceneid': 123,
>>    'feat' : [12312,21312,....]
>>}, ]```

### Faces/Person:
Path: Data/Faces/Person
>用于存储特定人物的特征，以<b>人名id</b>为单位存储,后缀为npy
>>**命名格式：**
>>personid_ff.npy 例如 1_ff.npy
>>
>>**数据格式：**
>>```
>>[{
>>    'ffid'   : 123,
>>    'feat' : [12312,21312,....]
>>}, ]```


## Videos
Path: Data/Videos
>用于存储视频（暂时）
