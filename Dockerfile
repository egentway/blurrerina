FROM nvcr.io/nvidia/deepstream:7.1-triton-multiarch

RUN mkdir /app
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_SYSTEM_PYTHON=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 1. Disable the default 'docker-clean' configuration that deletes packages after install
# 2. Persist /var/lib/apt/lists (for metadata) and /var/cache/apt (for packages)
RUN rm -f /etc/apt/apt.conf.d/docker-clean; \
    echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache

# apt-get update is run in user_additional_install.sh
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    /opt/nvidia/deepstream/deepstream/user_additional_install.sh

COPY --chmod=755 scripts/install_pyds.sh .
RUN ./install_pyds.sh -v 1.2.0

# Solves warnings about missing codecs when running GStreamer
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get install --reinstall -y --no-install-recommends \
    kmod \
    libflac8 \
    libmp3lame0 \
    libfaad2 \
    libvo-aacenc0 \
    libmjpegutils-2.1-0 \
    libopenh264-6 \
    libxvidcore4 \
    gstreamer1.0-libav


RUN git clone --depth 1 https://github.com/marcoslucianops/DeepStream-Yolo.git DeepStream-Yolo

RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install onnxscript onnxslim "ultralytics[export]"

COPY --chmod=755 scripts/convert_model.sh .
COPY --chmod=755 scripts/make_yolo_parser.sh .
COPY --chmod=755 scripts/entrypoint.sh .
COPY --chmod=755 blurrerina blurrerina

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python3", "blurrerina/main.py"]