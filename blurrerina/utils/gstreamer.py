import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstPbutils', '1.0')
from gi.repository import Gst, GstPbutils


def make_h264_mp4_profile():
    """
    Creates a profile for encodebin, that establishes the container, encoder and other
    parameters for the produced video.

    On the Jetson Orin Nano, encodebin will try to use the hardware encoder and fail,
    since this model doesn't have one. To make this use the software encoder, you need
    to export the env var GST_PLUGIN_FEATURE_RANK=nvv4l2h264enc:NONE,nvv4l2h265enc:NONE.

    >> pipeline.make("encodebin", "encoder_bin", properties={"profile": make_h264_mp4_profile()})
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
    video_profile.set_variableframerate(True)
    container_profile.add_profile(video_profile)

    return container_profile
