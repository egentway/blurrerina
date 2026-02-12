# Use the official DeepStream L4T image
FROM nvcr.io/nvidia/deepstream-l4t:7.1-triton-multiarch

RUN /opt/nvidia/deepstream/deepstream/user_additional_install.sh
RUN /opt/nvidia/deepstream/deepstream/user_deepstream_python_apps_install.sh -v 1.2.0

RUN pip3 install --no-cache-dir opencv-python

WORKDIR /app
COPY config .
COPY blurrerina .

CMD ["python3", "main.py"]