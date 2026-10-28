FROM python:3.12-slim
WORKDIR /app
COPY ["Proyecto Micro Mercado/zyntra_api/requirements.txt", "./requirements.txt"]
RUN pip install --no-cache-dir -r requirements.txt
COPY ["Proyecto Micro Mercado/zyntra_api/", "./"]
CMD ["python", "main.py"]
