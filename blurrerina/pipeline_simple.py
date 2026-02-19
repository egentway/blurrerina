import sys
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstPbutils', '1.0')
from gi.repository import GLib, Gst, GstPbutils

import datetime
from pathlib import Path
import pyds

from blurrerina.pipeline import Pipeline
import blurrerina.paths as paths

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def main():
    Gst.init(None)
    loop = GLib.MainLoop()
    pipeline = Pipeline(loop, "blurrerina-simple")

    input_path = str(paths.input_file.resolve())
    logger.info(f"{input_path=}")

    pipeline.make("filesrc", "source", properties={ "location": str(paths.input_file.resolve()) })
    pipeline.make("decodebin", "decoder_bin")
    pipeline.make("nvstreammux", "streammux", {
        "width": 1920,                 # output width
        "height": 1080,                # output height
        "batch-size": 1,               # has to match size in config_infer.txt
        "batched-push-timeout": 40000, # 40ms (standard)
        "live-source": 0               # 0 for files, 1 for cameras
    })
    pipeline.make("nvinfer", "nvinfer", properties={"config-file-path": str(paths.config_file.resolve())})
    pipeline.make("nvdsosd", "osd")
    # copy-hw: 2 is necessary to avoid memory errors with software encoding
    # see https://forums.developer.nvidia.com/t/deepstream-sdk-faq/80236/61
    pipeline.make("nvvideoconvert", "post_conv", properties={ "copy-hw": 2 })
    pipeline.make("encodebin", "encoder_bin", properties={"profile": make_h264_mp4_profile()})
    pipeline.make("filesink", "sink", properties={"location": str(paths.output_file.resolve()), "sync": False})

    pipeline.link(["source", "decoder_bin"])

    def decodebin_on_pad_added(element, pad, data):
        caps = pad.get_current_caps() or pad.query_caps()
        structure = caps.get_structure(0)
        media_type = structure.get_name()
        
        if "video/x-raw" not in media_type:
            # stream type is not video
            return

        sink_pad = data.request_pad_simple("sink_0")

        if not sink_pad:
            logger.error('[decodebin] Could not obtain sink pad "sink_0" from nvstreammux')
            return

        if sink_pad.is_linked():
            logger.info('[decodebin] pad already linked')

        res = pad.link(sink_pad)
        if res == Gst.PadLinkReturn.OK:
            logger.info("[decodebin] Linked video pad to nvstreammux sink pad")
        else:
            logger.error(f"[decodebin] Video pad link failed with code {res}")


    pipeline["decoder_bin"].connect("pad-added", decodebin_on_pad_added, pipeline["streammux"])
    pipeline.link(["streammux", "nvinfer", "osd", "post_conv", "encoder_bin", "sink"])

    pipeline.first_start()

    try:
        loop.run()
    except:
        pass

    pipeline.set_state(Gst.State.NULL)


def make_h264_mp4_profile():
    container_profile = GstPbutils.EncodingContainerProfile.new(
        "mp4_profile", 
        "Blurrerina Output", 
        Gst.Caps.from_string("video/quicktime")
        None
    )
    video_profile = GstPbutils.EncodingVideoProfile.new(
        Gst.Caps.from_string("video/x-h264"),
        None,
        None,
        0
    )
    container_profile.add_profile(video_profile)

    return container_profile

if __name__ == '__main__':
    main()