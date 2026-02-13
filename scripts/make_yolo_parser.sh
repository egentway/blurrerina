#!/usr/bin/env bash

set -euo pipefail

WORKDIR="/app"
CUDA_VER="12.6"
export CUDA_VER

cd "$WORKDIR"

cd DeepStream-Yolo
make -C nvdsinfer_custom_impl_Yolo clean
make -C nvdsinfer_custom_impl_Yolo
mkdir -p "$WORKDIR/volume/lib"
cp nvdsinfer_custom_impl_Yolo/libnvdsinfer_custom_impl_Yolo.so $WORKDIR/volume/lib/