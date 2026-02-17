from pathlib import Path
import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import os
import pyds
import numpy as np
import cv2
import ctypes

import time

# Classes to blur (check your labels.txt)
# Usually 0 is person. If you see boxes but no blurring, check your class IDs.
TARGET_CLASSES = [0, 2] 

# Blur kernel size - higher = more blur
BLUR_KERNEL_SIZE = 51

def apply_blur_to_frame(frame_meta, gst_buffer):
    """Apply blur to detected objects in the frame"""
    # Get the buffer surface
    n_frame = pyds.get_nvds_buf_surface(hash(gst_buffer), frame_meta.batch_id)
    
    # Get frame dimensions
    frame_height = frame_meta.source_frame_height
    frame_width = frame_meta.source_frame_width
    
    # Collect bounding boxes to blur
    l_obj = frame_meta.obj_meta_list
    boxes_to_blur = []
    
    while l_obj is not None:
        try:
            obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
        except StopIteration:
            break
        
        if obj_meta.class_id in TARGET_CLASSES:
            left = int(obj_meta.rect_params.left)
            top = int(obj_meta.rect_params.top)
            width = int(obj_meta.rect_params.width)
            height = int(obj_meta.rect_params.height)
            boxes_to_blur.append((left, top, width, height))
        
        try:
            l_obj = l_obj.next
        except StopIteration:
            break
    
    # If no boxes to blur, return early
    if not boxes_to_blur:
        return
    
    # Convert buffer to numpy array (RGBA format)
    frame_copy = np.array(n_frame, copy=True, order='C')
    frame_copy = cv2.cvtColor(frame_copy, cv2.COLOR_RGBA2BGRA)
    
    # Apply blur to each box
    for left, top, width, height in boxes_to_blur:
        # Ensure coordinates are within frame bounds
        left = max(0, left)
        top = max(0, top)
        right = min(frame_width, left + width)
        bottom = min(frame_height, top + height)
        
        if right > left and bottom > top:
            # Extract region
            roi = frame_copy[top:bottom, left:right]
            if roi.size > 0:
                # Apply Gaussian blur
                blurred_roi = cv2.GaussianBlur(roi, (BLUR_KERNEL_SIZE, BLUR_KERNEL_SIZE), 0)
                # Replace region
                frame_copy[top:bottom, left:right] = blurred_roi
    
    # Convert back and copy to buffer
    frame_copy = cv2.cvtColor(frame_copy, cv2.COLOR_BGRA2RGBA)
    np.copyto(n_frame, frame_copy)

def pgie_src_pad_buffer_probe(pad, info, u_data):
    gst_buffer = info.get_buffer()
    if not gst_buffer:
        return Gst.PadProbeReturn.OK

    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    l_frame = batch_meta.frame_meta_list
    
    while l_frame is not None:
        try:
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break
        
        # Apply blur to frame
        apply_blur_to_frame(frame_meta, gst_buffer)
        
        try:
            l_frame = l_frame.next
        except StopIteration:
            break
    
    return Gst.PadProbeReturn.OK

def main():
    start_time = time.perf_counter()
    Gst.init(None)

    base_path = Path("/app/volume")
    input_file = base_path / "data/input.mp4"
    output_file = base_path / "output/output.mp4"
    config_file = base_path / "config/config_infer_primary.txt"
    models_path = base_path / "models"
    
    if not os.path.exists(input_file):
        print(f"Input file {input_file} not found!")
        return

    # Pipeline with blur support
    # - nvv4l2decoder: Hardware decoding
    # - nvinfer: Object detection
    # - nvvideoconvert: Convert to CPU-accessible format for blur probe
    # - Probe attached after nvinfer to access detections and modify frame
    pipeline_str = f"""
        filesrc location={input_file} !
        qtdemux ! h264parse ! nvv4l2decoder ! 
        mux.sink_0 nvstreammux name=mux batch-size=1 width=1920 height=1080 !
        nvinfer name=pgie config-file-path={config_file} !
        nvvideoconvert name=converter !
        video/x-raw,format=RGBA !
        nvvideoconvert ! video/x-raw,format=I420 !
        avenc_mpeg4 bitrate=4000000 ! qtmux !
        filesink location={output_file}
    """

    print(f"Constructing pipeline...")
    pipeline = Gst.parse_launch(pipeline_str)

    # Attach probe to converter where buffer is in CPU-accessible RGBA format
    converter = pipeline.get_by_name("converter")
    converter_src_pad = converter.get_static_pad("src")
    converter_src_pad.add_probe(Gst.PadProbeType.BUFFER, pgie_src_pad_buffer_probe, 0)

    loop = GLib.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    
    def on_message(bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            print("Processing complete.")
            loop.quit()
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"Error: {err}")
            loop.quit()
        return True
    bus.connect("message", on_message)

    print(f"Starting processing: {input_file}")
    pipeline.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    except KeyboardInterrupt:
        pass
    
    print("Closing...")
    pipeline.set_state(Gst.State.NULL)
    end_time = time.perf_counter()
    print(f"Total processing time: {end_time - start_time:.2f} seconds")
    
    # If not present, DeepStream creates the model in the TensorRT .engine format 
    # in the current folder. To avoid needing regenerating it each time, we move it
    # to a persistent location.

    for model_file in Path().glob("*.engine"):
        shutil.copy(model_file, models_path / model_file.name)

if __name__ == '__main__':
    main()
