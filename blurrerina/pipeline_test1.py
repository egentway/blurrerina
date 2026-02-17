#!/usr/bin/env python3

################################################################################
# SPDX-FileCopyrightText: Copyright (c) 2019-2023 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
################################################################################

from pathlib import Path
import sys

sys.path.append('../')
import os
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GLib, Gst

from blurrerina.pipeline import Pipeline
import utils.platform_info as platform_info

import pyds

MUXER_BATCH_TIMEOUT_USEC = 33000

base_path = Path("/app/volume")
input_file = base_path / "data/input.mp4"
output_file = base_path / "output/output.mp4"
config_file = base_path / "config/config_infer_primary.txt"
models_path = base_path / "models"


def main():
    loop = GLib.MainLoop()
    pipeline = Pipeline(loop, "blurrerina")

    pipeline.make("filesrc", "source", properties={"location": str(input_file.resolve())})
    pipeline.make("h264parse", "h264parse_dec")
    pipeline.make("nvv4l2decoder", "decoder")
    pipeline.make("nvstreammux", "streammux", properties={"batch-size": 1, "width": 1920, "height": 1080, "batched-push-timeout": MUXER_BATCH_TIMEOUT_USEC})
    pipeline.make("nvinfer", "nvinfer", properties={"config-file-path": str(config_file.resolve())})
    pipeline.make("nvdsosd", "osd")
    pipeline.make("nvvideoconvert", "videoconvert")
    pipeline.make("x264enc", "x264enc")
    pipeline.make("h264parse", "h264parse_enc")
    pipeline.make("mp4mux", "mp4mux")
    pipeline.make("filesink", "filesink", properties={"location": str(output_file.resolve())})

    decoder_sourcepad = pipeline["decoder"].get_static_pad("src")
    if not decoder_sourcepad:
        raise RuntimeError("Could not get sourcepad for decoder")

    streammux_sinkpad = pipeline["streammux"].request_pad_simple("sink_0")
    if not streammux_sinkpad:
        raise RuntimeError("Could not get sinkpad for streammux")

    pipeline.link(["source", "h264parse_dec", "decoder"])
    decoder_sourcepad.link(streammux_sinkpad)
    pipeline.link(["nvinfer", "osd", "videoconvert", "x264enc", "h264parse_enc", "mp4mux", "filesink"])

    # osdsinkpad = nvosd.get_static_pad("sink")
    # if not osdsinkpad:
    #     sys.stderr.write(" Unable to get sink pad of nvosd \n")

    # osdsinkpad.add_probe(Gst.PadProbeType.BUFFER, osd_sink_pad_buffer_probe, 0)

    # start play back and listen to events
    pipeline.pipeline.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    except:
        pass
    pipeline.pipeline.set_state(Gst.State.NULL)

PGIE_CLASS_ID_VEHICLE = 0
PGIE_CLASS_ID_BICYCLE = 1
PGIE_CLASS_ID_PERSON = 2
PGIE_CLASS_ID_ROADSIGN = 3

def osd_sink_pad_buffer_probe(pad,info,u_data):
    frame_number=0
    num_rects=0

    gst_buffer = info.get_buffer()
    if not gst_buffer:
        print("Unable to get GstBuffer ")
        return

    # Retrieve batch metadata from the gst_buffer
    # Note that pyds.gst_buffer_get_nvds_batch_meta() expects the
    # C address of gst_buffer as input, which is obtained with hash(gst_buffer)
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    l_frame = batch_meta.frame_meta_list
    while l_frame is not None:
        try:
            # Note that l_frame.data needs a cast to pyds.NvDsFrameMeta
            # The casting is done by pyds.NvDsFrameMeta.cast()
            # The casting also keeps ownership of the underlying memory
            # in the C code, so the Python garbage collector will leave
            # it alone.
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break

        #Intiallizing object counter with 0.
        obj_counter = {
            PGIE_CLASS_ID_VEHICLE:0,
            PGIE_CLASS_ID_PERSON:0,
            PGIE_CLASS_ID_BICYCLE:0,
            PGIE_CLASS_ID_ROADSIGN:0
        }
        frame_number=frame_meta.frame_num
        num_rects = frame_meta.num_obj_meta
        l_obj=frame_meta.obj_meta_list
        while l_obj is not None:
            try:
                # Casting l_obj.data to pyds.NvDsObjectMeta
                obj_meta=pyds.NvDsObjectMeta.cast(l_obj.data)
            except StopIteration:
                break
            obj_counter[obj_meta.class_id] += 1
            obj_meta.rect_params.border_color.set(0.0, 0.0, 1.0, 0.8) #0.8 is alpha (opacity)
            try: 
                l_obj=l_obj.next
            except StopIteration:
                break

        # Acquiring a display meta object. The memory ownership remains in
        # the C code so downstream plugins can still access it. Otherwise
        # the garbage collector will claim it when this probe function exits.
        display_meta=pyds.nvds_acquire_display_meta_from_pool(batch_meta)
        display_meta.num_labels = 1
        py_nvosd_text_params = display_meta.text_params[0]
        # Setting display text to be shown on screen
        # Note that the pyds module allocates a buffer for the string, and the
        # memory will not be claimed by the garbage collector.
        # Reading the display_text field here will return the C address of the
        # allocated string. Use pyds.get_string() to get the string content.
        py_nvosd_text_params.display_text = "Frame Number={} Number of Objects={} Vehicle_count={} Person_count={}".format(frame_number, num_rects, obj_counter[PGIE_CLASS_ID_VEHICLE], obj_counter[PGIE_CLASS_ID_PERSON])

        # Now set the offsets where the string should appear
        py_nvosd_text_params.x_offset = 10
        py_nvosd_text_params.y_offset = 12

        # Font , font-color and font-size
        py_nvosd_text_params.font_params.font_name = "Serif"
        py_nvosd_text_params.font_params.font_size = 10
        # set(red, green, blue, alpha); set to White
        py_nvosd_text_params.font_params.font_color.set(1.0, 1.0, 1.0, 1.0)

        # Text background color
        py_nvosd_text_params.set_bg_clr = 1
        # set(red, green, blue, alpha); set to Black
        py_nvosd_text_params.text_bg_clr.set(0.0, 0.0, 0.0, 1.0)
        # Using pyds.get_string() to get display_text as string
        print(pyds.get_string(py_nvosd_text_params.display_text))
        pyds.nvds_add_display_meta_to_frame(frame_meta, display_meta)
        try:
            l_frame=l_frame.next
        except StopIteration:
            break
			
    return Gst.PadProbeReturn.OK	


if __name__ == '__main__':
    sys.exit(main())
