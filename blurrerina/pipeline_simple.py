import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GLib, Gst

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
    pipeline.make("fakesink", "sink")

    pipeline.link(["source", "decoder_bin"])

    def decodebin_on_pad_added(element, pad, data):
        caps = pad.get_current_caps() or pad.query_caps()
        structure = caps.get_structure(0)
        media_type = structure.get_name()
        
        if "video/x-raw" not in media_type:
            # stream type is not video
            return

        sink_pad = data.get_request_pad("sink_0")

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
    pipeline.link(["streammux", "nvinfer", "osd", "sink"])

    pipeline.first_start()

    try:
        loop.run()
    except:
        pass

    pipeline.set_state(Gst.State.NULL)


if __name__ == '__main__':
    main()