#!/bin/bash

echo "Starting RAG Desktop App deployment..."

# Build and start services
docker-compose down
docker-compose build
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Check service health
echo "Checking service health..."
docker-compose ps

# Check if Postgres is ready
until docker-compose exec postgres pg_isready -U postgres; do
  echo "Waiting for PostgreSQL..."
  sleep 2
done

# Check if Qdrant is ready
until curl -f http://localhost:6333/health; do
  echo "Waiting for Qdrant..."
  sleep 2
done

# Check if Ollama is ready
until curl -f http://localhost:11434/api/version; do
  echo "Waiting for Ollama..."
  sleep 2
done

echo "All services are running!"
echo "PostgreSQL: localhost:5432"
echo "Qdrant: localhost:6333"
echo "Ollama: localhost:11434"