import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstPbutils', '1.0')
from gi.repository import GLib, Gst, GstPbutils

from blurrerina.pipeline_wrapper import PipelineWrapper
import blurrerina.paths as paths

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def main():
    Gst.init(None)
    loop = GLib.MainLoop()
    pipeline = PipelineWrapper(Gst.Pipeline(name="blurrerina"), loop)

    input_path = str(paths.input_file.resolve())
    output_path = str(paths.output_file.resolve())
    logger.info(f"{input_path=} {output_path=}")

    pipeline.make("uridecodebin", "decoder_bin", properties={ "uri": f"file://{input_path}" })
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

    # on the Jetson Orin Nano, encodebin will try to use the hardware encoder and fail,
    # since this model doesn't have one. To make this use the software encoder, you need
    # to export the env var GST_PLUGIN_FEATURE_RANK=nvv4l2h264enc:NONE,nvv4l2h265enc:NONE
    pipeline.make("encodebin", "encoder_bin", properties={"profile": make_h264_mp4_profile()})

    pipeline.make("filesink", "sink", properties={"location": output_path, "sync": False})

    pipeline["decoder_bin"].connect("pad-added", decodebin_on_pad_added, pipeline["streammux"])
    pipeline.link(["streammux", "nvinfer", "osd", "post_conv", "encoder_bin", "sink"])

    pipeline.set_state(Gst.State.PLAYING)

    try:
        loop.run()
    finally:
        pipeline.set_state(Gst.State.NULL)

def decodebin_on_pad_added(element, pad, data):
    """
    Callback for decodebin/uridecodebin.

    GStreamer uses pads. They are points at which different elements can connect.
    Pads can be sources or sinks, based on whether they send or receive data. 
    You usually connect source pads to sink pads.

    Most elements have static "src" and "sink" pads, which represent respectively their input
    and output. In that case, you can use the `element.link(other_element)` API to implicitly
    connect `element`'s `sink` pad to `other_element`'s source pad.

    Other elements have dynamic sources and sinks, that get added while the application is in
    execution. In that case, you use callbacks to plug directly the various source pads and sink pads
    as they are added in elements.

    This function takes care of requesting a new sink pad to `nvstreammux` each time a source pad
    for `decodebin` is added, and plugging them together.
    """
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


def make_h264_mp4_profile():
    """
    Creates a profile for encodebin, that establishes the container, encoder and other
    parameters for the produced video.
    """

    container_caps = Gst.Caps.from_string("video/quicktime")
    if not container_caps:
        raise RuntimeError("Could not create container_caps")

    container_profile = GstPbutils.EncodingContainerProfile.new(
        "mp4_profile", 
        "Blurrerina Output", 
        container_caps,
        None
    )

    video_caps = Gst.Caps.from_string("video/x-h264")
    if not video_caps:
        raise RuntimeError("Could not create video_caps")

    video_profile = GstPbutils.EncodingVideoProfile.new(
        video_caps,
        None,
        None,
        0
    )
    container_profile.add_profile(video_profile)

    return container_profile

if __name__ == '__main__':
    main()