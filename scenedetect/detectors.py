#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# This file contains all of the detection methods/algorithms that can be used
# in PySceneDetect.  This includes a base object (SceneDetector) upon which all
# other detection method objects are based, which can be used as templates for
# implementing custom/application-specific scene detection methods.
#
# Copyright (C) 2012-2017 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 2-Clause License; see the
# included LICENSE file or visit one of the following pages for details:
#  - http://www.bcastell.com/projects/pyscenedetect/
#  - https://github.com/Breakthrough/PySceneDetect/
#
# This software uses Numpy and OpenCV; see the LICENSE-NUMPY and
# LICENSE-OPENCV files or visit one of above URLs for details.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#

# Third-Party Library Imports
import cv2
import numpy as np
# import minpy.numpy as np

# Default value for -d / --detector CLI argument (see get_available_detectors()
# for a list of valid/enabled detection methods and their string equivalents).
DETECTOR_DEFAULT = 'threshold'


def get_available():
    """Returns a dictionary of the available/enabled scene detectors.

    Returns:
        A dictionary with the form {name (string): detector (SceneDetector)},
        where name is the common name used via the command-line, and detector
        is a reference to the object instantiator.
    """
    detector_dict = {
        'threshold': ThresholdDetector,
        'content': ContentDetector
    }
    return detector_dict


class SceneDetector(object):
    """Base SceneDetector class to implement a scene detection algorithm."""
    def __init__(self):
        pass

    def process_frame(self, frame_num, frame_img, frame_metrics, scene_list):
        """Computes/stores metrics and detects any scene changes.

        Prototype method, no actual detection.
        """
        return

    def post_process(self, scene_list, frame_num):
        pass


class ThresholdDetector(SceneDetector):
    """Detects fast cuts/slow fades in from and out to a given threshold level.

    Detects both fast cuts and slow fades so long as an appropriate threshold
    is chosen (especially taking into account the minimum grey/black level).

    Attributes:
        threshold:  8-bit intensity value that each pixel value (R, G, and B)
            must be <= to in order to trigger a fade in/out.
        min_percent:  Float between 0.0 and 1.0 which represents the minimum
            percent of pixels in a frame that must meet the threshold value in
            order to trigger a fade in/out.
        min_scene_len:  Unsigned integer greater than 0 representing the
            minimum length, in frames, of a scene (or subsequent scene cut).
        fade_bias:  Float between -1.0 and +1.0 representing the percentage of
            timecode skew for the start of a scene (-1.0 causing a cut at the
            fade-to-black, 0.0 in the middle, and +1.0 causing the cut to be
            right at the position where the threshold is passed).
        add_final_scene:  Boolean indicating if the video ends on a fade-out to
            generate an additional scene at this timecode.
        block_size:  Number of rows in the image to sum per iteration (can be
            tuned to increase performance in some cases; should be computed
            programmatically in the future).
    """
    def __init__(self, threshold = 12, min_percent = 0.95, min_scene_len = 15,
                 fade_bias = 0.0, add_final_scene = False, block_size = 8):
        """Initializes threshold-based scene detector object."""
        super(ThresholdDetector, self).__init__()
        self.threshold = int(threshold)
        self.fade_bias = fade_bias
        self.min_percent = min_percent
        self.min_scene_len = min_scene_len
        self.last_frame_avg = None
        self.last_scene_cut = None
        # Whether to add an additional scene or not when ending on a fade out
        # (as cuts are only added on fade ins; see post_process() for details).
        self.add_final_scene = add_final_scene
        # Where the last fade (threshold crossing) was detected.
        self.last_fade = { 
            'frame': 0,         # frame number where the last detected fade is
            'type': None        # type of fade, can be either 'in' or 'out'
          }
        self.block_size = block_size
        return

    def compute_frame_average(self, frame):
        """Computes the average pixel value/intensity over the whole frame.

        The value is computed by adding up the 8-bit R, G, and B values for
        each pixel, and dividing by the number of pixels multiplied by 3.

        Returns:
            Floating point value representing average pixel intensity.
        """
        num_pixel_values = float(
            frame.shape[0] * frame.shape[1] * frame.shape[2])
        avg_pixel_value = np.sum(frame[:,:,:]) / num_pixel_values
        return avg_pixel_value

    def frame_under_threshold(self, frame):
        """Check if the frame is below (true) or above (false) the threshold.

        Instead of using the average, we check all pixel values (R, G, and B)
        meet the given threshold (within the minimum percent).  This ensures
        that the threshold is not exceeded while maintaining some tolerance for
        compression and noise.

        This is the algorithm used for absolute mode of the threshold detector.

        Returns:
            Boolean, True if the number of pixels whose R, G, and B values are
            all <= the threshold is within min_percent pixels, or False if not.
        """
        # First we compute the minimum number of pixels that need to meet the
        # threshold. Internally, we check for values greater than the threshold
        # as it's more likely that a given frame contains actual content. This
        # is done in blocks of rows, so in many cases we only have to check a
        # small portion of the frame instead of inspecting every single pixel.
        num_pixel_values = float(frame.shape[0] * frame.shape[1] * frame.shape[2])
        min_pixels = int(num_pixel_values * (1.0 - self.min_percent))

        curr_frame_amt = 0
        curr_frame_row = 0

        while curr_frame_row < frame.shape[0]:
            # Add and total the number of individual pixel values (R, G, and B)
            # in the current row block that exceed the threshold. 
            curr_frame_amt += int(
                np.sum(frame[curr_frame_row : 
                    curr_frame_row + self.block_size,:,:] > self.threshold))
            # If we've already exceeded the most pixels allowed to be above the
            # threshold, we can skip processing the rest of the pixels. 
            if curr_frame_amt > min_pixels:
                return False
            curr_frame_row += self.block_size
        return True

    def process_frame(self, frame_num, frame_img, frame_metrics, scene_list):
        # Compare the # of pixels under threshold in current_frame & last_frame.
        # If absolute value of pixel intensity delta is above the threshold,
        # then we trigger a new scene cut/break.

        # Value to return indiciating if a scene cut was found or not.
        cut_detected = False

        # The metric used here to detect scene breaks is the percent of pixels
        # less than or equal to the threshold; however, since this differs on
        # user-supplied values, we supply the average pixel intensity as this
        # frame metric instead (to assist with manually selecting a threshold).
        frame_amt = 0.0
        frame_avg = 0.0
        if frame_num in frame_metrics and 'frame_avg_rgb' in frame_metrics[frame_num]:
            frame_avg = frame_metrics[frame_num]['frame_avg_rgb']
        else:
            frame_avg = self.compute_frame_average(frame_img)
            frame_metrics[frame_num]['frame_avg_rgb'] = frame_avg

        if self.last_frame_avg is not None:
            if self.last_fade['type'] == 'in' and self.frame_under_threshold(frame_img):
                # Just faded out of a scene, wait for next fade in.
                self.last_fade['type'] = 'out'
                self.last_fade['frame'] = frame_num
            elif self.last_fade['type'] == 'out' and not self.frame_under_threshold(frame_img):
                # Just faded into a new scene, compute timecode for the scene
                # split based on the fade bias.
                f_in = frame_num
                f_out = self.last_fade['frame']
                f_split = int((f_in + f_out + int(self.fade_bias * (f_in - f_out))) / 2)
                # Only add the scene if min_scene_len frames have passed. 
                if self.last_scene_cut is None or (
                    (frame_num - self.last_scene_cut) >= self.min_scene_len):
                    scene_list.append(f_split)
                    cut_detected = True
                    self.last_scene_cut = frame_num
                self.last_fade['type'] = 'in'
                self.last_fade['frame'] = frame_num
        else:
            self.last_fade['frame'] = 0
            if self.frame_under_threshold(frame_img):
                self.last_fade['type'] = 'out'
            else:
                self.last_fade['type'] = 'in'
        # Before returning, we keep track of the last frame average (can also
        # be used to compute fades independently of the last fade type).
        self.last_frame_avg = frame_avg
        return cut_detected

    def post_process(self, scene_list, frame_num):
        """Writes a final scene cut if the last detected fade was a fade-out.

        Only writes the scene cut if add_final_scene is true, and the last fade
        that was detected was a fade-out.  There is no bias applied to this cut
        (since there is no corresponding fade-in) so it will be located at the
        exact frame where the fade-out crossed the detection threshold.
        """

        # If the last fade detected was a fade out, we add a corresponding new
        # scene break to indicate the end of the scene.  This is only done for
        # fade-outs, as a scene cut is already added when a fade-in is found.
        cut_detected = False
        if self.last_fade['type'] == 'out' and self.add_final_scene and (
            self.last_scene_cut is None or
            (frame_num - self.last_scene_cut) >= self.min_scene_len):
            scene_list.append(self.last_fade['frame'])
            cut_detected = True
        return cut_detected

import matplotlib.pyplot as plt  

class ContentDetector(SceneDetector):
    """Detects fast cuts using changes in colour and intensity between frames.

    Since the difference between frames is used, unlike the ThresholdDetector,
    only fast cuts are detected with this method.  To detect slow fades between
    content scenes still using HSV information, use the DissolveDetector.
    """

    def __init__(self, threshold = 30.0, min_scene_len = 20):
        super(ContentDetector, self).__init__()
        self.threshold = threshold
        self.min_scene_len = min_scene_len  # minimum length of any given scene, in frames
        self.last_frame = None
        self.last_scene_cut = None
        self.begin_hsv = None
        self.last_hsv = None
        self.num_pixels = None
        # print(diff.shape)
        hmask = np.ones((1, diff.shape[1],diff.shape[2]))
        smask = np.ones((1, diff.shape[1],diff.shape[2]))
        vmask = np.ones((1, diff.shape[1],diff.shape[2]))
        
        # print(mask2.shape)        
        hmask = 1 * hmask
        smask = 1 * hmask        
        vmask = 1 * vmask
        mask = np.vstack((hmask, smask))
        self.mask = np.vstack((mask, vmask))
        # self.surf = cv2.xfeatures2d.SURF_create()
    
    def calculate_delta(self, hsv_a, hsv_b):
        # 减小亮度变化带来的影响,对HSV的V通道进行衰减,
        # 同时适当增强其他两个通道
        # 0.7, 1.1, 1.2
        diff = hsv_a.astype(np.int32) - hsv_b.astype(np.int32)
        diff = diff * self.mask
        # mask =         
        delta_hsv = np.sum(np.abs(diff), axis=(1,2)) / (float(self.num_pixels))
        delta_hsv = np.append(delta_hsv, np.sum(delta_hsv)/3.0)
        return delta_hsv

    def process_frame(self, frame_num, frame_img, frame_metrics, scene_list):
        # Similar to ThresholdDetector, but using the HSV colour space DIFFERENCE instead
        # of single-frame RGB/grayscale intensity (thus cannot detect slow fades with this method).

        # Value to return indiciating if a scene cut was found or not.
        cut_detected = False
        save_both    = False
        return_last_hsv = None    
        return_curr_hsv = None
        # 额外计算本scene中头尾两个画面的hsv,决定是否保存尾部图片


        if self.last_frame is not None:
            # Change in average of HSV (hsv), (h)ue only, (s)aturation only, (l)uminance only.
            delta_hsv_avg, delta_h, delta_s, delta_v = 0.0, 0.0, 0.0, 0.0

            if frame_num in frame_metrics and 'delta_hsv_avg' in frame_metrics[frame_num]:
                delta_hsv_avg = frame_metrics[frame_num]['delta_hsv_avg']
                delta_h = frame_metrics[frame_num]['delta_hue']
                delta_s = frame_metrics[frame_num]['delta_sat']
                delta_v = frame_metrics[frame_num]['delta_lum']

            else:
                num_pixels = frame_img.shape[0] * frame_img.shape[1]
                curr_hsv = cv2.split(cv2.cvtColor(frame_img, cv2.COLOR_BGR2HSV))
                curr_hsv = np.array(curr_hsv)

                last_hsv = self.last_hsv
                if last_hsv is None:
                    last_hsv = cv2.split(cv2.cvtColor(self.last_frame, cv2.COLOR_BGR2HSV))
                    last_hsv = np.array(last_hsv)

                if not self.num_pixels:
                    self.num_pixels = curr_hsv[0].shape[0] * curr_hsv[0].shape[1]

                delta_hsv = self.calculate_delta(curr_hsv, last_hsv)
                delta_h, delta_s, delta_v, delta_hsv_avg = delta_hsv

                frame_metrics[frame_num]['delta_hsv_avg'] = delta_hsv_avg
                frame_metrics[frame_num]['delta_hue'] = delta_h
                frame_metrics[frame_num]['delta_sat'] = delta_s
                frame_metrics[frame_num]['delta_lum'] = delta_v

            # 保存上一个场景的最后一帧hsv,并返回
            return_last_hsv = last_hsv    
            return_curr_hsv = curr_hsv

            if delta_hsv_avg >= self.threshold:
                if self.last_scene_cut is None or (
                  (frame_num - self.last_scene_cut) >= self.min_scene_len): 
                    if self.begin_hsv is None:
                        pass# First Scene
                    else:
                        # Compare begin and last
                        _,_,_,value = self.calculate_delta(self.begin_hsv, self.last_hsv)
                        if value > self.threshold/1.1 and value >= delta_hsv_avg:
                            # save both
                            # print("SAVE "+str(value)+ " : "+str(self.threshold) + " : " +str(delta_hsv_avg))
                            save_both = True
                        else:
                            pass
                            # print("NO-SAVE "+str(value)+ " : "+str(self.threshold) + " : " +str(delta_hsv_avg))
       
                    self.begin_hsv = curr_hsv
                    scene_list.append(frame_num)
                    self.last_scene_cut = frame_num
                    cut_detected = True
            self.last_hsv = curr_hsv
            #self.last_frame.release()
            del self.last_frame
                
        self.last_frame = frame_img.copy()
        return cut_detected, save_both, return_last_hsv, return_curr_hsv

    def post_process(self, scene_list, frame_num):
        """Not used for ContentDetector, as cuts are written as they are found."""
        return
