# 使用官方的 Python 基础镜像
FROM python:3.10

# 设置工作目录
WORKDIR /app

# 复制 requirements.txt 文件到工作目录
COPY requirements.txt .

# 安装必要的系统依赖
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    libasound2 \
    libxcomposite1 \
    libxdamage1 \
    libxi6 \
    libxtst6 \
    libnss3 \
    libxrandr2 \
    libxrender1 \
    libxshmfence1 \
    libgl1 \
    libxcursor1 \
    libxkbcommon0 \
    libwayland-client0 \
    libwayland-cursor0 \
    libegl1 \
    libx11-xcb1 \
    libxcb-render0 \
    libxcb-shm0 \
    && rm -rf /var/lib/apt/lists/*
    
# 安装依赖项
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Playwright 及其浏览器依赖
RUN playwright install

# 复制项目文件到工作目录
COPY . .

# 暴露端口
EXPOSE 8000

# 启动 FastAPI 应用
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]