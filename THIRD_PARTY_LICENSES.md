# Third-Party Licenses

This document lists all third-party dependencies used in the MCP Ecosystem and their respective licenses.

## Overview

The MCP Ecosystem uses various open-source libraries and frameworks. We respect and comply with all license requirements. This document provides a comprehensive list of all third-party dependencies, their versions, and license information.

## Python Dependencies

### Core Framework
- **FastAPI** (0.104.1) - MIT License
  - High-performance web framework for building APIs
  - https://github.com/tiangolo/fastapi

- **Uvicorn** (0.24.0) - BSD 3-Clause License
  - ASGI server implementation
  - https://github.com/encode/uvicorn

### Security
- **python-jose[cryptography]** (3.3.0) - MIT License
  - JSON Web Token implementation
  - https://github.com/mpdavis/python-jose

- **passlib[bcrypt]** (1.7.4) - BSD 2-Clause License
  - Password hashing library
  - https://github.com/glic3rinu/passlib

- **cryptography** (41.0.7) - Apache 2.0 / BSD 3-Clause
  - Cryptographic recipes and primitives
  - https://github.com/pyca/cryptography

### Database Clients
- **redis** (5.0.1) - MIT License
  - Redis Python client
  - https://github.com/redis/redis-py

- **neo4j** (5.14.1) - Apache 2.0 License
  - Neo4j Python driver
  - https://github.com/neo4j/neo4j-python-driver

- **asyncpg** (0.29.0) - Apache 2.0 License
  - PostgreSQL client for Python
  - https://github.com/MagicStack/asyncpg

### Machine Learning & AI
- **openai** (1.3.7) - MIT License
  - OpenAI API client
  - https://github.com/openai/openai-python

- **anthropic** (0.7.7) - MIT License
  - Anthropic Claude API client
  - https://github.com/anthropics/anthropic-sdk-python

- **transformers** (4.35.2) - Apache 2.0 License
  - State-of-the-art NLP models
  - https://github.com/huggingface/transformers

- **sentence-transformers** (2.2.2) - Apache 2.0 License
  - Sentence embeddings
  - https://github.com/UKPLab/sentence-transformers

### Vector Databases
- **qdrant-client** (1.7.0) - Apache 2.0 License
  - Qdrant vector database client
  - https://github.com/qdrant/qdrant-client

- **chromadb** (0.4.18) - Apache 2.0 License
  - Chroma vector database
  - https://github.com/chroma-core/chroma

### Data Processing
- **pandas** (2.1.4) - BSD 3-Clause License
  - Data manipulation and analysis
  - https://github.com/pandas-dev/pandas

- **numpy** (1.26.2) - BSD 3-Clause License
  - Numerical computing
  - https://github.com/numpy/numpy

- **scipy** (1.11.4) - BSD 3-Clause License
  - Scientific computing
  - https://github.com/scipy/scipy

- **scikit-learn** (1.3.2) - BSD 3-Clause License
  - Machine learning library
  - https://github.com/scikit-learn/scikit-learn

### Audio/Video Processing
- **pydub** (0.25.1) - MIT License
  - Audio processing
  - https://github.com/jiaaro/pydub

- **opencv-python** (4.8.1.78) - Apache 2.0 License
  - Computer vision library
  - https://github.com/opencv/opencv-python

- **moviepy** (1.0.3) - MIT License
  - Video editing
  - https://github.com/Zulko/moviepy

- **whisper** (1.1.10) - MIT License
  - Speech recognition
  - https://github.com/openai/whisper

### Document Processing
- **pypdf** (3.17.1) - BSD 3-Clause License
  - PDF processing
  - https://github.com/py-pdf/pypdf

- **python-docx** (1.1.0) - MIT License
  - Word document processing
  - https://github.com/python-openxml/python-docx

- **openpyxl** (3.1.2) - MIT License
  - Excel file processing
  - https://github.com/openpyxl/openpyxl

- **pytesseract** (0.3.10) - Apache 2.0 License
  - OCR wrapper
  - https://github.com/madmaze/pytesseract

### Monitoring & Logging
- **prometheus-client** (0.19.0) - Apache 2.0 License
  - Prometheus metrics
  - https://github.com/prometheus/client_python

- **python-logging-loki** (1.3.1) - MIT License
  - Loki logging handler
  - https://github.com/GreyZmeem/python-logging-loki

### Testing
- **pytest** (7.4.3) - MIT License
  - Testing framework
  - https://github.com/pytest-dev/pytest

- **pytest-asyncio** (0.21.1) - Apache 2.0 License
  - Async testing support
  - https://github.com/pytest-dev/pytest-asyncio

- **locust** (2.17.0) - MIT License
  - Load testing framework
  - https://github.com/locustio/locust

- **httpx** (0.25.2) - BSD 3-Clause License
  - HTTP client
  - https://github.com/encode/httpx

### Utilities
- **pydantic** (2.5.2) - MIT License
  - Data validation
  - https://github.com/pydantic/pydantic

- **python-multipart** (0.0.6) - Apache 2.0 License
  - Multipart form data parsing
  - https://github.com/andrew-d/python-multipart

- **python-dotenv** (1.0.0) - BSD 3-Clause License
  - Environment variable management
  - https://github.com/theskumar/python-dotenv

- **pyyaml** (6.0.1) - MIT License
  - YAML parser
  - https://github.com/yaml/pyyaml

- **click** (8.1.7) - BSD 3-Clause License
  - Command line interface
  - https://github.com/pallets/click

## Docker Images

### Databases
- **redis:7-alpine** - BSD 3-Clause License
  - In-memory data structure store
  - https://redis.io/

- **neo4j:5-community** - GPL v3 License
  - Graph database (Community Edition)
  - https://neo4j.com/
  - Note: Enterprise features require commercial license

- **postgres:16-alpine** - PostgreSQL License
  - Relational database
  - https://www.postgresql.org/

### Infrastructure
- **nginx:alpine** - BSD 2-Clause License
  - Web server and reverse proxy
  - https://nginx.org/

- **grafana/grafana:latest** - Apache 2.0 License
  - Monitoring and observability platform
  - https://grafana.com/

- **prom/prometheus:latest** - Apache 2.0 License
  - Monitoring system and time series database
  - https://prometheus.io/

- **grafana/loki:2.9.0** - Apache 2.0 License
  - Log aggregation system
  - https://grafana.com/oss/loki/

### Base Images
- **python:3.10-slim** - PSF License
  - Python runtime
  - https://www.python.org/

- **alpine:latest** - MIT License
  - Minimal Linux distribution
  - https://alpinelinux.org/

## JavaScript/Node.js Dependencies

### Build Tools
- **vite** (5.0.0) - MIT License
  - Frontend build tool
  - https://github.com/vitejs/vite

- **typescript** (5.3.3) - Apache 2.0 License
  - TypeScript language
  - https://github.com/microsoft/TypeScript

### Testing
- **jest** (29.7.0) - MIT License
  - JavaScript testing framework
  - https://github.com/facebook/jest

## System Dependencies

### Required System Packages
- **ffmpeg** - LGPL 2.1+ License
  - Audio/video processing
  - https://ffmpeg.org/

- **tesseract-ocr** - Apache 2.0 License
  - OCR engine
  - https://github.com/tesseract-ocr/tesseract

- **git** - GPL v2 License
  - Version control
  - https://git-scm.com/

## License Compliance

### GPL/LGPL Components
- Neo4j Community Edition (GPL v3) - Used only for graph database functionality
- FFmpeg (LGPL 2.1+) - Dynamically linked, no modifications

### Commercial Considerations
- Neo4j Enterprise features require a commercial license
- All other components use permissive licenses (MIT, BSD, Apache 2.0)

### Attribution Requirements
- All MIT, BSD, and Apache licensed components require attribution
- Attribution is provided through this document and in source code where applicable

## Updates and Maintenance

This document is maintained as part of the MCP Ecosystem and is updated whenever dependencies change. Last updated: {{current_date}}

To regenerate this list:
```bash
# Python dependencies
pip-licenses --format=markdown --output-file=python-licenses.md

# Docker images
docker images --format "table {{.Repository}}:{{.Tag}}" | tail -n +2 > docker-images.txt

# System packages
dpkg -l | grep -E "ffmpeg|tesseract|git" > system-packages.txt
```

## Questions and Concerns

For questions about licensing or to report a concern, please contact:
- Email: legal@insightpulseai.com
- GitHub Issues: https://github.com/InsightPulseAI/mcp-ecosystem/issues