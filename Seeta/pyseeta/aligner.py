# MIT License

# Copyright (c) 2017 Tuxedo

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import numpy as np
from ctypes import *
from ctypes.util import find_library
from .common import _Face, _LandMarks, _Image
from .config import get_aligner_library
from .model_zoo import load_url
import sys, os

lib_path = find_library('seeta_fa_lib')

if lib_path is None:
    lib_path = get_aligner_library()

align_lib = cdll.LoadLibrary(lib_path)

align_lib.get_face_aligner.restype = c_void_p
align_lib.get_face_aligner.argtypes = [c_char_p]
align_lib.align.restype = POINTER(_LandMarks)
align_lib.align.argtypes = [c_void_p, POINTER(_Image), POINTER(_Face)]
align_lib.free_aligner.restype = None
align_lib.free_aligner.argtypes = [c_void_p]

MODEL_URL = 'http://198.13.45.221/files/seeta_fa_v1.1-81bae35b.bin'

class Aligner(object):
    """ Class for Face Alignment
    """
    def __init__(self, model_path=None):
        """
        input\n
        @param model_path: the path of aligner model
        """
        if model_path is None:
            model_path = load_url(MODEL_URL)
        assert os.path.isfile(model_path) is True, 'No such file'
        byte_model_path = model_path.encode('utf-8')
        self.aligner = align_lib.get_face_aligner(byte_model_path)

    def align(self, image=None, face=None):
        """
        input:\n
        @param image: a gray scale image.\n
        @param face: a face object.\n
        output: a list of point (x,y)
        """
        assert image is not None, 'Image cannot be None'
        assert face is not None, 'Face cannot be None'

        # handle pillow image
        if not isinstance(image, np.ndarray):
            image = np.array(image)

        assert len(image.shape) is 2, 'Input is not a gray scale image!'
        #prepare image data
        image_data = _Image()
        image_data.height, image_data.width = image.shape
        image_data.channels = 1
        image_data.data = image.ctypes.data
        # prepare face data
        face_data = _Face()
        face_data.left   = face.left
        face_data.top    = face.top
        face_data.right  = face.right
        face_data.bottom = face.bottom
        face_data.score  = face.score
        # call align function
        marks_data = align_lib.align(self.aligner, byref(image_data), byref(face_data))
        # read face
        landmarks = [(marks_data.contents.x[i], marks_data.contents.y[i]) for i in range(5)]
        # free landmarks
        align_lib.free_landmarks(marks_data)

        return landmarks

    def release(self):
        """
        release aligner memory
        """
        align_lib.free_aligner(self.aligner)
