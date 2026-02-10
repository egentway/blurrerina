# Use the official DeepStream L4T image
FROM nvcr.io/nvidia/deepstream-l4t:7.1-triton-multiarch

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    python3-gst-1.0 \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gstreamer-1.0 \
    gir1.2-gst-rtsp-server-1.0 \
    libgstrtspserver-1.0-0 \
    libgirepository1.0-dev \
    libcairo2-dev \
    libssl-dev \
    cmake \
    g++ \
    make \
    pkg-config \
    libglib2.0-dev \
    libglib2.0-dev-bin \
    python3-opencv \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install TensorRT development libraries (if not already present)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnvinfer-dev \
    libnvinfer-plugin-dev \
    libnvonnxparsers-dev \
    && rm -rf /var/lib/apt/lists/*

# Install CUDA toolkit (for headers/libraries)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     cuda-toolkit-12-6 \
#     && rm -rf /var/lib/apt/lists/*

# # Symlink for compatibility with Makefile CUDA_VER=12.2
RUN if [ ! -d /usr/local/cuda-12.2 ]; then ln -s /usr/local/cuda /usr/local/cuda-12.2; fi

# Clone and build the custom YOLO parser
RUN git clone https://github.com/marcoslucianops/DeepStream-Yolo.git /tmp/DeepStream-Yolo && \
    cd /tmp/DeepStream-Yolo && \
    make -C nvdsinfer_custom_impl_Yolo CUDA_VER=12.6 && \
    mkdir -p /app/nvdsinfer_custom_impl_Yolo && \
    cp nvdsinfer_custom_impl_Yolo/libnvdsinfer_custom_impl_Yolo.so /app/nvdsinfer_custom_impl_Yolo/ && \
    rm -rf /tmp/DeepStream-Yolo

# Install Python packages
RUN pip3 install --upgrade pip
RUN pip3 install numpy opencv-python onnx ultralytics

# # Install DeepStream Python bindings (pyds)
# RUN if ls /opt/nvidia/deepstream/deepstream/lib/pyds*.whl 1> /dev/null 2>&1; then \
#         pip3 install /opt/nvidia/deepstream/deepstream/lib/pyds*.whl; \
#     elif [ -f /opt/nvidia/deepstream/deepstream/sw_install/pyds-1.1.8-py3-none-linux_aarch64.whl ]; then \
#         pip3 install /opt/nvidia/deepstream/deepstream/sw_install/pyds-1.1.8-py3-none-linux_aarch64.whl; \
#     else \
#         echo "pyds wheel not found. Checking if already installed or accessible via PYTHONPATH."; \
#     fi

# Download and install pyds wheel for DeepStream Python bindings
RUN wget -O /tmp/pyds-1.2.0-cp310-cp310-linux_aarch64.whl \
    https://github.com/NVIDIA-AI-IOT/deepstream_python_apps/releases/download/v1.2.0/pyds-1.2.0-cp310-cp310-linux_aarch64.whl && \
    pip3 install /tmp/pyds-1.2.0-cp310-cp310-linux_aarch64.whl && \
    rm /tmp/pyds-1.2.0-cp310-cp310-linux_aarch64.whl

WORKDIR /app

# Copy the application files
COPY . .

# Set environment variables
ENV GST_DEBUG=3

# Set DeepStream library and plugin paths
ENV LD_LIBRARY_PATH="/opt/nvidia/deepstream/deepstream/lib:/opt/nvidia/deepstream/deepstream/lib/gst-plugins:/opt/nvidia/deepstream/deepstream/lib/gst-plugins-extra:${LD_LIBRARY_PATH}"
ENV GST_PLUGIN_PATH="/opt/nvidia/deepstream/deepstream/lib/gst-plugins:/opt/nvidia/deepstream/deepstream/lib/gst-plugins-extra:${GST_PLUGIN_PATH}"

CMD ["python3", "main.py"]