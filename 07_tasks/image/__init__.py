"""Image signal extraction tasks.

Submodules (``classify``, ``color``, ``meta``, ``quality``, ``regions``,
``text_ocr``) are imported individually rather than re-exported here — most
depend on ``cv2`` from the optional ``[vision]`` extra, so eager loading
would break installations without OpenCV.
"""
