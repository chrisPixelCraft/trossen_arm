# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /uvx /usr/local/bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/cache/huggingface \
    HF_LEROBOT_HOME=/app/policy/captures/lerobot-cache \
    UV_HTTP_TIMEOUT=180

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential linux-libc-dev git ffmpeg libusb-1.0-0 \
       libgl1 libglib2.0-0 libgomp1 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY docker/requirements.lock /opt/requirements.lock

RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --python /usr/local/bin/python \
       --torch-backend cu126 --index https://pypi.nvidia.com \
       -r /opt/requirements.lock \
       "lerobot-robot-trossen @ git+https://github.com/TrossenRobotics/lerobot_trossen.git@337ed74df1ee617ddfb5987a9f7464cf3089c4a2#subdirectory=packages/lerobot_robot_trossen" \
    && python -m pip check

COPY policy/lerobot_observe.py policy/pi05_infer.py policy/pi05_infer_cpu.py \
     policy/pi05_preflight.py policy/test_lerobot_integration.py /app/policy/
COPY demos/python/*.py /app/demos/python/
COPY docker/verify.py /app/docker/verify.py

RUN python docker/verify.py \
    && python -m unittest discover -s policy -p test_lerobot_integration.py

LABEL io.trossen.arm.version="1.11.0" \
      io.lerobot.version="0.6.1" \
      io.trossen.plugin.revision="337ed74df1ee617ddfb5987a9f7464cf3089c4a2"

CMD ["python", "policy/pi05_preflight.py", "--config-only"]
