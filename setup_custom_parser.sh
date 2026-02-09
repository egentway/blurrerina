#!/bin/bash
# Clone the DeepStream-Yolo repository to get the YOLOv8 parser
git clone https://github.com/marcoslucianops/DeepStream-Yolo.git
cd DeepStream-Yolo
# We need to set the CUDA version correctly for Orin Nano (usually 11.4 or 12.x)
# DeepStream 6.3 uses CUDA 11.4 or 12.1. 
# The build process will detect CUDA if it's in the PATH.
make -C nvdsinfer_custom_impl_Yolo
cp nvdsinfer_custom_impl_Yolo/libnvdsinfer_custom_impl_Yolo.so ../nvdsinfer_custom_impl_Yolo/
cd ..
rm -rf DeepStream-Yolo
