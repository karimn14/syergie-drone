#!/bin/bash
# Drone Sawit deployment script

echo "Stopping existing containers..."
docker stop drone_sawit || true
docker rm drone_sawit || true

echo "Building Docker image..."
docker build -t drone_sawit .

echo "Starting new container..."
docker run -d --name drone_sawit --env-file .env -p 8000:8000 -p 8080:8080 drone_sawit

echo "Deployment complete."
