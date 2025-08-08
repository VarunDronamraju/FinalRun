# RAG Desktop Application

Enterprise-grade Retrieval Augmented Generation desktop application with FastAPI backend and PyQt6 frontend.

## Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Git

### Setup
```bash
# Clone and setup
git clone <your-repo>
cd rag-desktop-app

# Setup development environment
python scripts/setup_dev.py

# Or manual setup
cp .env.example .env
pip install -r requirements.txt
docker-compose up -d