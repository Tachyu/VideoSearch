#! /usr/bin/env python
"""Run a YOLO_v2 style detection model on test images."""
import argparse
import colorsys
import imghdr
import os
import random

import numpy as np
from keras import backend as K
from keras.models import load_model
from PIL import Image, ImageDraw, ImageFont

from yad2k.models.keras_yolo import yolo_eval, yolo_head
import logging
import pickle
import zlib
# from keras.utils import plot_model


parser = argparse.ArgumentParser(
    description='Run a YOLO_v2 style detection model on test images..')
parser.add_argument(
    'model_path',
    help='path to h5 model file containing body'
    'of a YOLO_v2 model')
parser.add_argument(
    '-a',
    '--anchors_path',
    help='path to anchors file, defaults to yolo_anchors.txt',
    default='model_data/yolo_anchors.txt')
parser.add_argument(
    '-c',
    '--classes_path',
    help='path to classes file, defaults to coco_classes.txt',
    default='model_data/coco_chinese_classes.txt')
parser.add_argument(
    '-t',
    '--test_path',
    help='path to directory of test images, defaults to images/',
    default='images')
parser.add_argument(
    '-o',
    '--output_path',
    help='path to output test images, defaults to images/out',
    default='images/out')
parser.add_argument(
    '-s',
    '--score_threshold',
    type=float,
    help='threshold for bounding box scores, default .3',
    default=.3)
parser.add_argument(
    '-iou',
    '--iou_threshold',
    type=float,
    help='threshold for non max suppression IOU, default .5',
    default=.5)

logging.basicConfig(level = logging.INFO,format = '%(levelname)s-%(asctime)s %(message)s')

def write_feature(feature, feature_output_path, image_name, isCompress=False):
    image_name =  os.path.splitext(image_name)[0]
    if not os.path.exists(feature_output_path):
        print('Creating feature output path {}'.format(feature_output_path))
        os.mkdir(feature_output_path)
    # # 压缩
    # if isCompress:
    #     logging.info("Start  compress feature file: "+image_name)
    #     feature = zlib.compress(feature, zlib.Z_BEST_COMPRESSION)
    #     logging.info("Finish compress feature file: "+image_name)
    # c = np.load("a.npy")
    # str2 = zlib.decompress(str1)
    ff_path = os.path.join(feature_output_path, image_name) 
    ff_path = ff_path + '.npy'     
    # 使用numpy读写文件功能
    np.save(ff_path, feature)  
    # with open(ff_path,'wb') as ff:
    #     pickle.dump(feature, ff)
    #     # ff.write(feature)

def save_tag(image_names, tag_output_path, image_classes, all_classes):
    image_names =[os.path.splitext(i)[0] for i in image_names]
    if not os.path.exists(tag_output_path):
        print('Creating tag output path {}'.format(tag_output_path))
        os.mkdir(tag_output_path)
    images_dic_list = []
    image_classes = np.array(image_classes)
    all_classes = np.array(all_classes)
    print(image_classes.shape)
    print(all_classes.shape)
    
    for index, image in enumerate(image_names): 
        image_dic = {}
        tags = ''
        image_tag_name = np.choose(image_classes[index], all_classes)
        for t in image_tag_name:
            tags += t + '&'
        image_dic['index'] = index            
        image_dic['name'] = image
        image_dic['tags'] = tags
        images_dic_list.append(image_dic)
    tag_csv_path = os.path.join(tag_output_path, '1') + '.csv' 

    with open(tag_csv_path, "wb") as csvFile:
        csvWriter.writerow(['id', 'name', 'tag'])        
        csvWriter = csv.writer(csvFile)
        csvWriter.writerows(data)
    logging.info("Successfully write csv file:"+tag_csv_path)



def _main(args):
    model_path = os.path.expanduser(args.model_path)
    assert model_path.endswith('.h5'), 'Keras model must be a .h5 file.'
    anchors_path = os.path.expanduser(args.anchors_path)
    classes_path = os.path.expanduser(args.classes_path)
    test_path = os.path.expanduser(args.test_path)
    output_path = os.path.expanduser(args.output_path)

    if not os.path.exists(output_path):
        print('Creating output path {}'.format(output_path))
        os.mkdir(output_path)

    sess = K.get_session()  # TODO: Remove dependence on Tensorflow session.

    with open(classes_path) as f:
        class_names = f.readlines()
    class_names = [c.strip() for c in class_names]

    with open(anchors_path) as f:
        anchors = f.readline()
        anchors = [float(x) for x in anchors.split(',')]
        anchors = np.array(anchors).reshape(-1, 2)

    yolo_model = load_model(model_path)
    # plot_model(yolo_model, to_file='model.png')
    # Verify model, anchors, and classes are compatible
    num_classes = len(class_names)
    num_anchors = len(anchors)
    # TODO: Assumes dim ordering is channel last
    model_output_channels = yolo_model.layers[-1].output_shape[-1]
    assert model_output_channels == num_anchors * (num_classes + 5), \
        'Mismatch between model and given anchor and class sizes. ' \
        'Specify matching anchors and classes with --anchors_path and ' \
        '--classes_path flags.'
    print('{} model, anchors, and classes loaded.'.format(model_path))

    # Check if model is fully convolutional, assuming channel last order.
    model_image_size = yolo_model.layers[0].input_shape[1:3]
    is_fixed_size = model_image_size != (None, None)

    # Generate colors for drawing bounding boxes.
    hsv_tuples = [(x / len(class_names), 1., 1.)
                  for x in range(len(class_names))]
    colors = list(map(lambda x: colorsys.hsv_to_rgb(*x), hsv_tuples))
    colors = list(
        map(lambda x: (int(x[0] * 255), int(x[1] * 255), int(x[2] * 255)),
            colors))
    random.seed(10101)  # Fixed seed for consistent colors across runs.
    random.shuffle(colors)  # Shuffle colors to decorrelate adjacent classes.
    random.seed(None)  # Reset seed to default.

    # Generate output tensor targets for filtered bounding boxes.
    # TODO: Wrap these backend operations with Keras layers.
    yolo_outputs = yolo_head(yolo_model.output, anchors, len(class_names))
    input_image_shape = K.placeholder(shape=(2, ))
    boxes, scores, classes = yolo_eval(
        yolo_outputs,
        input_image_shape,
        score_threshold=args.score_threshold,
        iou_threshold=args.iou_threshold)

    image_files = os.listdir(test_path)
    true_images = []
    true_images_classes = []
    
    for image_file in image_files:
        try:
            if not os.path.isdir(image_file):
                image_type = imghdr.what(os.path.join(test_path, image_file))
                if not image_type:
                    continue
                else:
                    true_images.append(image_file)
            else:
                continue
        except IsADirectoryError:
            continue

        image = Image.open(os.path.join(test_path, image_file))
        if is_fixed_size:  # TODO: When resizing we can use minibatch input.
            resized_image = image.resize(
                tuple(reversed(model_image_size)), Image.BICUBIC)
            image_data = np.array(resized_image, dtype='float32')
        else:
            # Due to skip connection + max pooling in YOLO_v2, inputs must have
            # width and height as multiples of 32.
            new_image_size = (image.width - (image.width % 32),
                              image.height - (image.height % 32))
            resized_image = image.resize(new_image_size, Image.BICUBIC)
            image_data = np.array(resized_image, dtype='float32')
            print(image_data.shape)

        image_data /= 255.
        image_data = np.expand_dims(image_data, 0)  # Add batch dimension.
        logging.info(image_data.shape)

        out_boxes, out_scores, out_classes, yolo_model_output = sess.run(
            [boxes, scores, classes, yolo_model.output],
            feed_dict={
                yolo_model.input: image_data,
                input_image_shape: [image.size[1], image.size[0]],
                K.learning_phase(): 0
            })
        logging.info(yolo_model_output.reshape(-1).shape)
        print('Found {} boxes for {}'.format(len(out_boxes), image_file))

        font = ImageFont.truetype(
            font='font/SourceHanSans-Regular.otf',
            size=np.floor(3e-2 * image.size[1] + 0.5).astype('int32'))
        thickness = (image.size[0] + image.size[1]) // 300
        
        true_images_classes.append(out_classes)

        for i, c in reversed(list(enumerate(out_classes))):
            predicted_class = class_names[c]
            box = out_boxes[i]
            score = out_scores[i]

            label = '{} {:.2f}'.format(predicted_class, score)

            draw = ImageDraw.Draw(image)
            label_size = draw.textsize(label, font)

            top, left, bottom, right = box
            top = max(0, np.floor(top + 0.5).astype('int32'))
            left = max(0, np.floor(left + 0.5).astype('int32'))
            bottom = min(image.size[1], np.floor(bottom + 0.5).astype('int32'))
            right = min(image.size[0], np.floor(right + 0.5).astype('int32'))
            print(label, (left, top), (right, bottom))

            if top - label_size[1] >= 0:
                text_origin = np.array([left, top - label_size[1]])
            else:
                text_origin = np.array([left, top + 1])

            # My kingdom for a good redistributable image drawing library.
            for i in range(thickness):
                draw.rectangle(
                    [left + i, top + i, right - i, bottom - i],
                    outline=colors[c])
            draw.rectangle(
                [tuple(text_origin), tuple(text_origin + label_size)],
                fill=colors[c])
            draw.text(text_origin, label, fill=(0, 0, 0), font=font)
            del draw
        # write_feature(yolo_model_output.reshape(-1), 'feature', image_file)
        # image.save(os.path.join(output_path, image_file), quality=90)
    save_tag(true_images, 'tags', true_images_classes, class_names)
    sess.close()


if __name__ == '__main__':
    _main(parser.parse_args())
