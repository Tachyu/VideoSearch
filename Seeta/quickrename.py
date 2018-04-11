import os
dir = os.listdir('data')

for index, f in enumerate(dir):
    suffix = os.path.splitext(f)[1]
    os.rename('data/' + f, 'data/'+str(index) + suffix )
