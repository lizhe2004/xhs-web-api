# 使用官方的 Python 基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 复制 requirements.txt 文件到工作目录
COPY requirements.txt .

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