# Use the official DeepStream L4T image
FROM nvcr.io/nvidia/deepstream-l4t:6.3-samples

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
    libcommon-dev \
    libssl-dev \
    cmake \
    g++ \
    make \
    pkg-config \
    libglib2.0-dev \
    libglib2.0-dev-bin \
    python3-opencv \
    git \
    wget

# Clone and build the custom YOLO parser
RUN git clone https://github.com/marcoslucianops/DeepStream-Yolo.git /tmp/DeepStream-Yolo && \
    cd /tmp/DeepStream-Yolo && \
    make -C nvdsinfer_custom_impl_Yolo && \
    mkdir -p /app/nvdsinfer_custom_impl_Yolo && \
    cp nvdsinfer_custom_impl_Yolo/libnvdsinfer_custom_impl_Yolo.so /app/nvdsinfer_custom_impl_Yolo/ && \
    rm -rf /tmp/DeepStream-Yolo

# Install Python packages
RUN pip3 install --upgrade pip
RUN pip3 install numpy opencv-python onnx ultralytics

# Install DeepStream Python bindings (pyds)
# Note: In 6.3+, they might be pre-installed or need a specific build.
# For simplicity in this demo, we use the ones that might be available or 
# suggest the user to use the pre-built wheels if necessary.
# However, many newer DS images have them.

WORKDIR /app

# Copy the application files
COPY . .

# Set environment variables
ENV GST_DEBUG=3

CMD ["python3", "main.py"]
