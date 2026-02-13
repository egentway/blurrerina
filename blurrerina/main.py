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

            # Oscura (blackout) le regioni degli oggetti rilevati delle classi target
            if obj_meta.class_id in TARGET_CLASSES:
                display_meta = pyds.nvds_acquire_display_meta_from_pool(batch_meta)
                rect_params = display_meta.rect_params[display_meta.num_rects]
                rect_params.left = int(obj_meta.rect_params.left)
                rect_params.top = int(obj_meta.rect_params.top)
                rect_params.width = int(obj_meta.rect_params.width)
                rect_params.height = int(obj_meta.rect_params.height)
                rect_params.border_width = 0
                rect_params.has_bg_color = 1
                rect_params.bg_color.set(0.0, 0.0, 0.0, 1.0)  # Nero opaco
                rect_params.has_border_color = 0
                rect_params.filled = 1
                display_meta.num_rects += 1
                pyds.nvds_add_display_meta_to_frame(frame_meta, display_meta)

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
    config_file = "/app/volume/config/config_infer_primary.txt"
    
    if not os.path.exists(input_file):
        print(f"Input file {input_file} not found!")
        return

    # Definizione pipeline senza nvdsblur, usando nvdsosd per blackout
    pipeline_str = f"""
        filesrc location={input_file} !
        qtdemux ! h264parse ! decodebin !
        videoconvert ! nvvideoconvert !
        video/x-raw(memory:NVMM), format=NV12 !
        nvinfer name=pgie config-file-path={config_file} !
        nvvideoconvert ! nvdsosd !
        nvvideoconvert ! video/x-raw,format=I420 !
        x264enc bitrate=4000 ! h264parse ! qtmux !
        filesink location={output_file}
    """

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
