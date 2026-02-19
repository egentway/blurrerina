import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstPbutils', '1.0')
from gi.repository import Gst

import cv2
import pyds


def make_blur_probe_callback(classes_to_blur):

    def blur_probe_callback(pad, info, u_data=None):
        gst_buffer = info.get_buffer()
        if not gst_buffer:
            return Gst.PadProbeReturn.OK

        # Estrai i metadati della batch
        batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
        l_frame = batch_meta.frame_meta_list
        
        while l_frame is not None:
            try:
                frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
            except StopIteration:
                break

            # Ottieni il frame come array NumPy (mappa la memoria NVMM)
            # Nota: n_frame è una "view" sulla memoria originale, modificarlo cambia il video
            n_frame = pyds.get_nvds_buf_surface(hash(gst_buffer), frame_meta.batch_id)
            
            l_obj = frame_meta.obj_meta_list
            while l_obj is not None:
                try:
                    obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
                except StopIteration:
                    break

                # FILTRO: Puoi decidere cosa sfocare (es: class_id 0 per persone)
                # if obj_meta.class_id == 0:
                if obj_meta.class_id in classes_to_blur:
                    apply_blur_to_object(n_frame, obj_meta.rect_params)

                l_obj = l_obj.next
            
            l_frame = l_frame.next
        
        return Gst.PadProbeReturn.OK
    
    return blur_probe_callback


def apply_blur_to_object(frame, rect_params):
    """
    Blurs a specific region of a frame.
    """
    top = int(rect_params.top)
    left = int(rect_params.left)
    width = int(rect_params.width)
    height = int(rect_params.height)

    # avoids crash in case of out-of-frame coords
    img_h, img_w = frame.shape[:2]
    bottom = min(top + height, img_h)
    right = min(left + width, img_w)
    top = max(0, top)
    left = max(0, left)

    if (right > left) and (bottom > top):
        roi = frame[top:bottom, left:right]
        # Kernel (51, 51) for a heavy blur. needs to be not even
        blurred_roi = cv2.GaussianBlur(roi, (51, 51), 0)
        frame[top:bottom, left:right] = blurred_roi
