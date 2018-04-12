# coding: utf-8
import numpy 
import sys 
import nmslib 
import time 
import math 
from sklearn.neighbors import NearestNeighbors
import os
import numpy as np

# Just read the data
features_files = []
dirs = os.listdir(".")
# print(dirs)
for d in dirs:
    if os.path.splitext(d)[1] == '.npy':
        features_files.append(d)
print(features_files)

features_data_list = []
for ff in features_files:
    features_data_list.append(np.load(ff))
print(len(features_data_list))

features_data = np.stack(features_data_list[:len(features_data_list)-1], axis=0)
print(features_data.shape)

query_item = features_data_list[-1][np.newaxis,:]
print(query_item.shape)

M = 15
efC = 100
num_threads = 4

index_time_params = {'M': M, 
'indexThreadQty': num_threads, 
'efConstruction': efC, 
'post' : 0}
print('Index-time parameters', index_time_params)

# Number of neighbors 
K=100
space_name='l2'

# Intitialize the library, specify the space, the type of the vector and add data points 
index = nmslib.init(method='hnsw', 
space=space_name, 
data_type=nmslib.DataType.DENSE_VECTOR) 

index.addDataPointBatch(features_data) 

# Create an index
start = time.time()
index_time_params = {'M': M, 
'indexThreadQty': num_threads, 
'efConstruction': efC}
index.createIndex(index_time_params) 
end = time.time() 
print('Index-time parameters', index_time_params)
print('Indexing time = %f' % (end-start))

# Setting query-time parameters
efS = 100
query_time_params = {'efSearch': efS}
print('Setting query-time parameters', query_time_params)
index.setQueryTimeParams(query_time_params)

# Querying
query_qty = 1
# print(query_qty)
# print(query_matrix.shape)
start = time.time() 
nbrs = index.knnQueryBatch(query_item, 
k = K, 
num_threads = num_threads)
end = time.time() 
print('kNN time total=%f (sec), per query=%f (sec), per query adjusted for thread number=%f (sec)' % 
      (end-start, float(end-start)/query_qty, num_threads*float(end-start)/query_qty)) 
print(nbrs)

# Computing gold-standard data 
print('Computing gold-standard data')

start = time.time()
sindx = NearestNeighbors(n_neighbors=K, metric='l2', algorithm='brute').fit(data_matrix)
end = time.time()

print('Brute-force preparation time %f' % (end - start))

start = time.time() 
gs = sindx.kneighbors(query_matrix)
end = time.time()

print('brute-force kNN time total=%f (sec), per query=%f (sec)' % 
      (end-start, float(end-start)/query_qty) )

# Finally computing recall
recall=0.0
for i in range(0, query_qty):
  correct_set = set(gs[1][i])
  ret_set = set(nbrs[i][0])
  recall = recall + float(len(correct_set.intersection(ret_set))) / len(correct_set)
recall = recall / query_qty
print('kNN recall %f' % recall)

# Save a meta index
index.saveIndex('dense_index_optim.bin')

# Re-intitialize the library, specify the space, the type of the vector.
newIndex = nmslib.init(method='hnsw', space=space_name, data_type=nmslib.DataType.DENSE_VECTOR) 
# For an optimized L2 index, there's no need to re-load data points, but this would be required for
# non-optimized index or any other methods different from HNSW (other methods can save only meta indices)
#newIndex.addDataPointBatch(data_matrix) 


# Re-load the index and re-run queries
newIndex.loadIndex('dense_index_optim.bin')

# Setting query-time parameters and querying
print('Setting query-time parameters', query_time_params)
newIndex.setQueryTimeParams(query_time_params)

query_qty = query_matrix.shape[0]
start = time.time() 
new_nbrs = newIndex.knnQueryBatch(query_matrix, k = K, num_threads = num_threads)
end = time.time() 
print('kNN time total=%f (sec), per query=%f (sec), per query adjusted for thread number=%f (sec)' % 
      (end-start, float(end-start)/query_qty, num_threads*float(end-start)/query_qty)) 

# Finally computing recall for the new result set
recall=0.0
for i in range(0, query_qty):
  correct_set = set(gs[1][i])
  ret_set = set(new_nbrs[i][0])
  recall = recall + float(len(correct_set.intersection(ret_set))) / len(correct_set)
recall = recall / query_qty
print('kNN recall %f' % recall)

