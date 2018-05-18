#!/bin/sh
find Indexs/Content -name "*.bin"  | xargs rm -f
find Indexs/Content -name "*.npy"  | xargs rm -f
find Indexs/Faces -name "*.bin"  | xargs rm -f
find Indexs/Faces -name "*.npy"  | xargs rm -f

