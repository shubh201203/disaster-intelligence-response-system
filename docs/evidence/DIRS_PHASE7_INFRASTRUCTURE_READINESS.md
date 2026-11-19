# DIRS — Phase 7 Infrastructure Readiness & Deployment Topology Guide
## Work Package WP7.11: Production Infrastructure Sizing, Topology & Host Requirements

**Document Identifier:** `DIRS-PH7-INFRA-001`  
**Classification:** OFFICIAL / INFRASTRUCTURE ENGINEERING GUIDE  
**Phase:** Phase 7 — Enterprise Hardening, Reliability & Operational Readiness  
**Target Release:** DIRS v6.0 (Enterprise Hardened)  
**Status:** Certified / Complete  

---

## 1. Executive Summary

This specification establishes the hardware, operating system, network, and containerization requirements necessary to transition the Disaster Intelligence & Response System (DIRS) from local capstone verification to high-availability municipal or provincial production deployment.

> [!NOTE]  
> Under governing Capstone verification constraints, live cloud infrastructure was not provisioned during this audit. The system is classified as **CAPSTONE & STAGING READY**. This guide defines the target infrastructure topology required for full production rollout.

---

## 2. Infrastructure Sizing & Compute Specifications

### 2.1 Node Sizing Matrix
| Node Tier | CPU (Cores) | Memory (RAM) | Storage (NVMe SSD) | Primary Workload | Recommended Redundancy |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **API Gateway / Web** | 4 vCPU | 8 GB | 50 GB | FastAPI ASGI, TLS termination, Nginx | $N+1$ behind load balancer |
| **Solver Compute Worker** | 16 vCPU | 32 GB | 100 GB | OR-Tools CP-SAT parallel branch-and-bound | Auto-scaling worker pool (min 2) |
| **Primary Database** | 8 vCPU | 32 GB | 500 GB (Provisioned IOPS) | PostgreSQL 16 + PostGIS 3.4 | Primary + Hot Standby (Replica) |
| **Redis Cache / Broker** | 2 vCPU | 4 GB | 20 GB | Redis 7 Cluster (Idempotency & Celery) | Redis Sentinel (HA) |

### 2.2 Mathematical Solver Compute Profile
Google OR-Tools CP-SAT benefits significantly from multi-threaded search (`num_search_workers`). For heavy Tier 3 and Tier 4 disaster recovery portfolios (involving up to 180 candidate civil restoration projects across 52 planning periods), dedicated compute nodes with at least 8 to 16 physical cores ensure search convergence within acceptable operational boundaries.

---

## 3. High-Availability Network Topology

```
                         [Internet / Emergency Cellular APN]
                                         |
                                         v
                         [Edge Layer: Cloudflare / CDN]
                         (DDoS Protection, WAF, DNS)
                                         |
                                         v
                      [Reverse Proxy & Load Balancer: Nginx]
                      (TLS 1.3 Termination, Rate Limiting)
                                         |
         +-------------------------------+-------------------------------+
         |                                                               |
         v                                                               v
[FastAPI Web Node 1]                                            [FastAPI Web Node 2]
(Port 8000, ASGI Worker Pool)                                   (Port 8000, ASGI Worker Pool)
         |                                                               |
         +-------------------------------+-------------------------------+
                                         |
                       +-----------------+-----------------+
                       |                                   |
                       v                                   v
             [PgBouncer Connection Pooler]       [Redis 7 Cluster]
                       |                         (Idempotency & Celery)
                       v                                   ^
            [PostgreSQL 16 Primary]                        |
            (PostGIS 3.4 Relational Core)                  v
                       |                         [OR-Tools Worker Nodes]
                       v (Streaming Replication) (Asynchronous Tier 4 Solver)
            [PostgreSQL Read Standby]
```

---

## 4. Reverse Proxy & Security Hardening Configuration

A production Nginx reverse proxy configuration template for DIRS:
```nginx
upstream dirs_backend {
    server 127.0.0.1:8000;
    keepalive 64;
}

server {
    listen 443 ssl http2;
    server_name dirs.disaster-response.gov;

    ssl_certificate /etc/ssl/certs/dirs_fullchain.pem;
    ssl_certificate_key /etc/ssl/private/dirs_privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Payload ceiling (matches FastAPI MAX_REQUEST_BODY_BYTES)
    client_max_body_size 10M;

    # Static frontend assets
    location / {
        root /var/www/dirs-frontend/dist;
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "public, max-age=3600";
    }

    # API endpoints
    location /api/ {
        proxy_pass http://dirs_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 135s; # Exceeds 130s Axios solver timeout
    }

    # Real-time WebSocket Feed
    location /ws/ {
        proxy_pass http://dirs_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_read_timeout 86400s;
    }
}
```

---

## 5. Storage & Database Migration Invariants

- **Active Relational Tables:** 40 tables spanning civil defense, GIS spatial assets, incident media, damage assessments, dual financial/CCU ledgers, precedence DAGs, and CP-SAT results.
- **Alembic Migration Version:** Head strictly pinned to `phase6b_recovery_foundation`.
- **Database Engine Support:** Native PostgreSQL 14+ with PostGIS extensions installed by database administrator (`CREATE EXTENSION IF NOT EXISTS postgis`). SQLite is supported as an isolated development/testing fallback.

---

## 6. Infrastructure Readiness Verdict

**VERDICT: COMPLETE SPECIFICATION FOR CAPSTONE & PRODUCTION PROVISIONING**  
All compute requirements, network topologies, reverse proxy rules, and database specifications are fully documented and ready for automated deployment via Infrastructure as Code (Terraform / Ansible / Kubernetes Helm).
