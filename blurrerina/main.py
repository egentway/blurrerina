from pathlib import Path
import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import os
import pyds

import time
import shutil

# Classes to blur (check your labels.txt)
# Usually 0 is person. If you see boxes but no blurring, check your class IDs.
TARGET_CLASSES = [0, 2] 

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

            # Modifica gli oggetti delle classi target per oscurarli
            if obj_meta.class_id in TARGET_CLASSES:
                # Modifichiamo direttamente rect_params dell'oggetto per renderlo un rettangolo nero
                obj_meta.rect_params.border_width = 0
                obj_meta.rect_params.has_bg_color = 1
                obj_meta.rect_params.bg_color.set(0.0, 0.0, 0.0, 1.0)  # Nero opaco
                
                # Rimuoviamo il testo dell'etichetta
                obj_meta.text_params.display_text = ""
                obj_meta.text_params.set_bg_clr = 0

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

    pipeline_str = f"""
        filesrc location={input_file} !
        qtdemux ! h264parse ! decodebin !
        nvvideoconvert !
        video/x-raw(memory:NVMM), format=NV12 !
        mux.sink_0 nvstreammux name=mux batch-size=1 width=1920 height=1080 !
        nvinfer name=pgie config-file-path={config_file} !
        nvvideoconvert !
        nvdsosd !
        nvvideoconvert !
        video/x-raw,format=I420 !
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
    end_time = time.perf_counter()
    print(f"Total processing time: {end_time - start_time:.2f} seconds")
    
    for model_file in Path().glob("*.engine"):
        shutil.copy(model_file, models_path / model_file.name)

if __name__ == '__main__':
    main()
