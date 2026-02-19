import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstPbutils', '1.0')
from gi.repository import Gst, GstPbutils


def raise_if_none(fn, *args, **kwargs):
    elem = fn(*args, **kwargs)
    if elem is None:
        raise RuntimeError(f"{fn}({', '.join(args)}) returned None")
    return elem


def make_h264_mp4_profile():
    """
    Creates a profile for encodebin, that establishes the container, encoder and other
    parameters for the produced video.

    On the Jetson Orin Nano, encodebin will try to use the hardware encoder and fail,
    since this model doesn't have one. To make this use the software encoder, you need
    to export the env var GST_PLUGIN_FEATURE_RANK=nvv4l2h264enc:NONE,nvv4l2h265enc:NONE.

    >> pipeline.make("encodebin", "encoder_bin", properties={"profile": make_h264_mp4_profile()})
    """

    container_profile = GstPbutils.EncodingContainerProfile.new(
        "mp4_profile", 
        "Blurrerina Output", 
        raise_if_none(Gst.Caps.from_string, "video/quicktime"),
        None
    )

    video_profile = GstPbutils.EncodingVideoProfile.new(
        raise_if_none(Gst.Caps.from_string, "video/x-h264"),
        None,
        None,
        0
    )
    video_profile.set_variableframerate(True)
    container_profile.add_profile(video_profile)

    return container_profile
