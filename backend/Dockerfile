FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# 视频合成/占位片段依赖 ffmpeg
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY data/.gitkeep ./data/.gitkeep

# 运行时数据目录（docker-compose 挂载 volume）
RUN mkdir -p /app/data/projects

EXPOSE 8000

# 流水线在进程内后台线程运行，worker=1 避免重复执行
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
