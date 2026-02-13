#!/usr/bin/env bash

# Script adapted from
# https://docs.ultralytics.com/guides/deepstream-nvidia-jetson/#deepstream-configuration-for-yolo26

# This script requires:
# - The ultralytics repository to be cloned in /app/ultralytics
# - The DeepStream-Yolo repository to be cloned in /app/DeepStream-Yolo

set -euo pipefail

WORKDIR="/app"
MODEL_VERSION=yoloV8
MODEL_PATH="$WORKDIR/volume/models/yolov8n.pt"
MODEL_DIR=$(dirname "$MODEL_PATH")
MODEL_NAME=$(basename "$MODEL_PATH" .pt)

if [ ! -f "$MODEL_PATH" ]; then
    echo "Model file not found at $MODEL_PATH. Please ensure the model is available before running this script."
    exit 1
fi

EXPORT_SCRIPT="$WORKDIR/DeepStream-Yolo/utils/export_$MODEL_VERSION.py"

cd "$MODEL_DIR"
python3 $EXPORT_SCRIPT \
  --simplify \
  --opset 18 \
  --size 640 640 \
  -w "$MODEL_PATH"
