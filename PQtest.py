
# coding: utf-8

# In[7]:


import pickle,os,faiss,math
import numpy as np

def read_featfile(id_name, path,features_files=[]):
    """读特征文件，返回特征数据以及特征编号列表

    Arguments:
        id_name {string} -- 特征文件编号字段名
        path {string} -- 特征文件文件夹路径
    """
    # 读目录下所有特征文件
    if len(features_files) == 0:
        dirs = os.listdir(path)
        for d in dirs:
            if os.path.splitext(d)[1] == '.pkl':
                features_files.append(d)
    print("Load %d files from %s"%(len(features_files), path))

    features_data_list = []
    for ff_name in features_files:
        ff_name = os.path.join(path, ff_name)
        with open(ff_name,"rb") as ff:
            features_data_list += pickle.load(ff, encoding="utf8")

    num_feats = len(features_data_list)
    print("Feature Count = %d"%(num_feats))
    id_list = [item[id_name] for item in features_data_list]
    feat_list = [item['feat'] for item in features_data_list]                   
    return id_list, feat_list


# In[8]:


# id_name = 'sfid'
# features_files = ['Data/Content/Feats/1_sf.pkl']
id_name = 'ffid'
features_files = ['Data/Faces/Feats/1_ff.pkl']
ids, feats = read_featfile(id_name, '',features_files)

feats = np.array(feats).astype('float32')
print(feats.shape)


# In[11]:
dimention = feats.shape[1]
nlist = 5
m = 8
k = 8
bit = 2
# d % m = 0
                           # 8 specifies that each sub-vector is encoded as 8 bits
# index.train(feats)
# index.add(feats)
def ivecs_read(fname):
    a = np.fromfile(fname, dtype='int32')
    d = a[0]
    return a.reshape(-1, d + 1)[:, 1:].copy()

tmpdir = "tmp/"

def ct(count, dimention):
    print("%d x %d"%(count, dimention))
    m = 2
    for i in range(2,dimention):
        if (dimention % i) == 0:
            m = i
            break
    if i == dimention - 1:
        m = dimention
        
    bit = int(math.log(count,2))
    return m, bit

m, bit = ct(feats.shape[0], feats.shape[1])
bit = 4
print("m=%d bit=%d"%(m, bit))

def func():
    quantizer = faiss.IndexFlatL2(dimention)  # this remains the same
    # # index = faiss.IndexIVFPQ(quantizer, dimention, nlist, m, 3)
    index = faiss.IndexIVFPQ(quantizer, dimention, nlist, m, bit)
    return index, quantizer

index, quantizer = func()
     
# # # index = faiss.index_factory(dimention, "IVFPQ")
# print("training index")
index.train(feats)
index.add(feats)
# print("write " + tmpdir + "trained.index")
# faiss.write_index(index, tmpdir + "trained.index")

# print("read " + tmpdir + "all_flatpq_faces_index.bin")
# def rd():
#     index = faiss.read_index(tmpdir + "all_flatpq_faces_index.bin")
#     return index
# index = rd()
# index.nprobe = 5

# In[ ]:


D, I = index.search(feats, 1) # sanity check
# D = D / math.pow(2, bit)
print(D.shape)
avg = np.sum(D)/D.shape[0]
print(avg.shape)
print(avg)
# print(D)
# print(D)


