import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import os
import pyds

# Classes to blur (check your labels.txt)
# Usually 0 is person, but adjust according to your fine-tuned model
TARGET_CLASSES = [0] 

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

        l_obj = frame_meta.obj_meta_list
        while l_obj is not None:
            try:
                obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
            except StopIteration:
                break
            
            # Here we can filter which objects should be blurred.
            # By default, nvdsblur blurs objects depending on its configuration.
            # Some versions use the obj_meta.mask_params to decide.
            
            try: 
                l_obj = l_obj.next
            except StopIteration:
                break
        try:
            l_frame = l_frame.next
        except StopIteration:
            break
    return Gst.PadProbeReturn.OK

def main():
    Gst.init(None)

    input_file = "/app/volume/data/input.mp4"
    output_file = "/app/volume/output/output.mp4"
    config_file = "/app/config_infer_primary_yolo.txt"
    
    if not os.path.exists(input_file):
        print(f"Input file {input_file} not found!")
        return

    # Pipeline definition using Gst.parse_launch for simplicity
    # nvdsblur: blurs objects detected by nvinfer
    # nvv4l2h264enc: hardware H264 encoder on Jetson
    pipeline_str = (
        f"filesrc location={input_file} ! "
        f"qtdemux ! h264parse ! nvv4l2decoder ! "
        f"nvstreammux name=mux width=1920 height=1080 batch-size=1 ! "
        f"nvinfer name=pgie config-file-path={config_file} ! "
        f"nvdsblur blur-objects=1 ! "
        f"nvvideoconvert ! nvdsosd ! "
        f"nvvideoconvert ! 'video/x-raw(memory:NVMM), format=I420' ! "
        f"nvv4l2h264enc bitrate=4000000 ! h264parse ! qtmux ! "
        f"filesink location={output_file}"
    )

    print(f"Constructing pipeline...")
    pipeline = Gst.parse_launch(pipeline_str)

    # Optional: Attach probe to PGIE for metadata manipulation
    pgie = pipeline.get_by_name("pgie")
    pgie_src_pad = pgie.get_static_pad("src")
    pgie_src_pad.add_probe(Gst.PadProbeType.BUFFER, pgie_src_pad_buffer_probe, 0)

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

if __name__ == '__main__':
    main()
