# DIRS Deployment & Local Development Guide

## Prerequisites
- Docker Engine 20.10+
- Docker Compose v2+
- Python 3.11+ (for local backend testing)
- Node.js 18+ (for local frontend testing)

## Environment Setup
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

## Launching Local Development Stack
```bash
docker compose up --build -d
```

## Running Database Migrations & Seed Data
```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed_database.py
```

## Stopping Environment
```bash
docker compose down -v
```
