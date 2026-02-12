#!/usr/bin/env bash

# Instructions adapted from
# https://docs.ultralytics.com/guides/deepstream-nvidia-jetson/#deepstream-configuration-for-yolo26

# 1. Install Ultralytics with necessary dependencies
cd ~
pip install -U pip
git clone https://github.com/ultralytics/ultralytics
cd ultralytics
pip install -e ".[export]" onnxslim

# 2. Clone the DeepStream-Yolo repository
cd ~
git clone https://github.com/marcoslucianops/DeepStream-Yolo

# 3. Copy the export_yolo26.py file from DeepStream-Yolo/utils directory to the ultralytics folder
cp ~/DeepStream-Yolo/utils/export_yolo26.py ~/ultralytics
cd ultralytics

# 4. Copy the export_yolo26.py file from DeepStream-Yolo/utils directory to the ultralytics folder
wget https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26s.pt

# 5. Convert model to ONNX

# To simplify the ONNX model (DeepStream >= 6.0) --simplify
# To use static batch-size (example for batch-size = 4) --batch 4
# To use dynamic batch-size (DeepStream >= 6.1) --dynamic

python3 export_yolo26.py --simplify --dynamic -w yolo26s.pt

# 6. Copy the generated .onnx model file and labels.txt file to the DeepStream-Yolo folder
cp yolo26s.pt.onnx labels.txt ~/DeepStream-Yolo
cd ~/DeepStream-Yolo

# 7. Set the CUDA version according to the JetPack version installed
export CUDA_VER=12.6

# 8. Compile the library
make -C nvdsinfer_custom_impl_Yolo clean && make -C nvdsinfer_custom_impl_Yolo
