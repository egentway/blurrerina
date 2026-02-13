FROM nvcr.io/nvidia/deepstream:7.1-triton-multiarch

RUN mkdir /app
WORKDIR /app

RUN /opt/nvidia/deepstream/deepstream/user_additional_install.sh
RUN /opt/nvidia/deepstream/deepstream/update_rtpmanager.sh

COPY --chmod=755 scripts/install_pyds.sh .
RUN ./install_pyds.sh -v 1.2.0

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1

RUN git clone --depth 1 https://github.com/marcoslucianops/DeepStream-Yolo.git DeepStream-Yolo
RUN git clone --depth 1 https://github.com/ultralytics/ultralytics.git ultralytics
RUN cd ultralytics && pip install onnxscript onnxslim && pip install -e ".[export]" && cd ..

COPY --chmod=755 scripts/convert_model.sh .
COPY --chmod=755 scripts/make_yolo_parser.sh .

CMD ["python3", "blurrerina/main.py"]