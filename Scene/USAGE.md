
PySceneDetect
==========================================================

Usage (Command Line)
----------------------------------------------------------

In order to effectively use PySceneDetect, you should become familiar with the basic command line options (especially the detection method `-d`/`--detector` and threshold value `-t` / `--threshold`).  Descriptions for all command-line arguments can be obtained by running PySceneDetect with the `-h` / `--help` flag.

There are two main detection methods PySceneDetect uses: threshold (comparing each frame to a set black level, useful for detecting cuts and fades to/from black), and content (compares each frame sequentially looking for changes in content, useful for detecting fast cuts between video scenes, although slower to process).  Each mode has slightly different parameters, and is described in detail below.

In general, use `threshold` mode if you want to detect scene boundaries using fades/cuts in/out to black.  If the video uses a lot of fast cuts between content, and has no well-defined scene boundaries, you should use the `content` mode.  Once you know what detection mode to use, you can try the parameters recommended below, or generate a statistics file (using the `-s` / `--statsfile` flag) in order to determine the correct paramters - specifically, the proper threshold value.


### Content-Aware Detection Mode

Unlike threshold mode, content-aware mode looks at the *difference* between each pair of adjacent frames, triggering a scene break when this difference exceeds the threshold value.  A good threshold value to try when using content-aware mode (`-d content`) is `30` (`-t 30`), for example:

```rst
scenedetect -i my_video.mp4 -d content -t 30
```

The optimal threshold can be determined by generating a statsfile (`-s`), opening it with a spreadsheet editor (e.g. Excel), and examining the `delta_hsv_avg` column.  This value should be very small between similar frames, and grow large when a big change in content is noticed (look at the values near frame numbers/times where you know a scene change occurs).  The threshold value should be set so that most scenes fall below the threshold value, and scenes where changes occur should *exceed* the threshold value (thus triggering a scene change).

Automatically splitting video based on detected scenes (will save starting from `output_scene-001.mkv`):

```rst
scenedetect -i my_video.mp4 -d content -t 30 -o output_scene.mkv
```


### Threshold-Based Detection Mode

Threshold-based mode is what most traditional scene detection programs use, which looks at the average intensity of the *current* frame, triggering a scene break when the intensity falls below the threshold (or crosses back upwards).  A good threshold value to try when using threshold mode (`-d threshold`) is `12` (`-t 12`), with a minimum percentage of at least 90% (`-m 0.9`).  Using values less than `8` may cause problems with some videos (especially those encoded at lower quality bitrates).

The optimal threshold can be determined by generating a statsfile (`-s`), opening it with a spreadsheet editor (e.g. Excel), and examining the `avg_rgb` column.  These values represent the average intensity of the pixels for that particular frame (taken by averaging the R, G, and B values over the whole frame).  The threshold value should be set so that the average intensity of most frames in content scenes lie above the threshold value, and scenes where scene changes/breaks occur should fall *under* the threshold value (thus triggering a scene change).


Usage (Python)
----------------------------------------------------------

PySceneDetect can also be used from within other Python programs.  This allows you to perform scene detection directly in Python code, yielding a list of scene cuts/breaks for an OpenCV `VideoCapture` object.  Note: currently PySceneDetect requires the passed video stream to terminate, but support for live video stream segmentation is planned for the following version.

The general usage workflow is to determine which detection method and threshold to use (this can even be done iteratively), using these values to create a `SceneDetector` object, the type of which depends on the detection method you want to use (e.g. `ThresholdDetector`, `ContentDetector`).  A list of `SceneDetector` objects is then passed with an open `VideoCapture` object and an empty list to the `scenedetect.detect_scenes()` function, which appends the frame numbers of any detected scene boundaries to the list (the function itself returns the number of frames read from the video file).

The below code sample is incomplete, but shows the general usage style:

```python
import scenedetect

scene_list = []        # Scenes will be added to this list in detect_scenes().
path = 'my_video.mp4'  # Path to video file.

# Usually use one detector, but multiple can be used.
detector_list = [
	scenedetect.detectors.ThresholdDetector(threshold = 16, min_percent = 0.9)
]

video_framerate, frames_read = scenedetect.detect_scenes_file(
    path, scene_list, detector_list)

# scene_list now contains the frame numbers of scene boundaries.
print scene_list

# create new list with scene boundaries in milliseconds instead of frame #.
scene_list_msec = [(1000.0 * x) / float(video_framerate) for x in scene_list]

# create new list with scene boundaries in timecode strings ("HH:MM:SS.nnn").
scene_list_tc = [scenedetect.timecodes.get_string(x) for x in scene_list_msec]
```

The frame numbers can be converted to timecodes or seconds by passing the video framerate (returned by the `detect_scenes_file()` function) and the scene list to the appropriate timecode conversion function, as shown above.


----------------------------------------------------------

Licensed under BSD 2-Clause (see the `LICENSE` file for details).

Copyright (C) 2012-2017 Brandon Castellano.
All rights reserved.
