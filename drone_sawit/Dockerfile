# Drone Sawit Jetson/Server Dockerfile
FROM nvcr.io/nvidia/l4t-base:r32.7.1

WORKDIR /app

COPY jetson/requirements.txt ./
RUN apt-get update && apt-get install -y python3-pip && pip3 install -r requirements.txt

COPY jetson/ ./jetson/

CMD ["python3", "jetson/main.py"]
