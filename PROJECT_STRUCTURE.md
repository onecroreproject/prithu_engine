# 🏗️ Project Structure - Prithu Recommendation Engine

## Overview

This is a **production-grade Python backend** for the Prithu Android social media app's recommendation system. The backend uses a scalable, modular structure based on Django/FastAPI conventions.

---

## 📁 Directory Layout

```
Backend - New/
│
├── 📦 app/                           ← Main Application Package
│   ├── __init__.py                   ← Package identifier
│   ├── exceptions.py                 ← Custom exception classes (12+ types)
│   │
│   ├── 📁 core/                      ← Core Utilities
│   │   ├── __init__.py
│   │   ├── config.py                 ← Configuration management (295 lines)
│   │   └── logger_setup.py           ← Logging infrastructure (85 lines)
│   │
│   ├── 📁 database/                  ← Data Layer
│   │   ├── __init__.py
│   │   └── db_connection.py          ← MongoDB manager (450+ lines)
│   │
│   ├── 📁 models/                    ← Data Models
│   │   ├── __init__.py
│   │   └── schemas.py                ← Pydantic I/O models (250+ lines)
│   │
│   ├── 📁 engine/                    ← Recommendation Engine
│   │   ├── __init__.py
│   │   └── optimizer.py              ← RFRE engine (550+ lines)
│   │
│   └── 📁 api/                       ← REST API Layer
│       ├── __init__.py
│       └── routes.py                 ← FastAPI endpoints (500+ lines)
│
├── 📁 tests/                         ← Test Suite
│   ├── __init__.py
│   └── test_api.py                   ← Unit tests
│
├── 📁 scripts/                       ← Utility Scripts
│   ├── check_categories.py           ← Database analyzer
│   └── list_categories_simple.py     ← Category lister
│
├── 📄 main.py                        ← Application Entry Point (57 lines)
├── 📄 requirements-new.txt           ← Python Dependencies
├── 📄 .env                           ← Environment Variables
├── 📄 README.md                      ← Full Documentation
├── 📄 QUICKSTART.md                  ← Quick Start Guide
├── 📄 PROJECT_STRUCTURE.md           ← This File
└── 📁 .venv/                         ← Virtual Environment
```

---

## 📚 Module Descriptions

### Core Utilities (`app/core/`)

#### `config.py` - Configuration Management
- **Purpose**: Centralized configuration with environment variables
- **Key Components**:
  - `Config` class with all settings
  - Database (MongoDB) configuration
  - Scoring weights (Festival 40%, Push 30%, Trending 30%)
  - Logging configuration
  - Collection names and constants
  - Validation methods

#### `logger_setup.py` - Structured Logging
- **Purpose**: Centralized logging with console + file handlers
- **Key Components**:
  - `LoggerSetup` singleton
  - Rotating file handler (10MB per file, 5 backups)
  - Console handler with formatting
  - Module-level logger retrieval

---

### Database Layer (`app/database/`)

#### `db_connection.py` - MongoDB Connection Manager
- **Purpose**: Singleton database manager with connection pooling
- **Key Components**:
  - `DatabaseManager` singleton
  - Connection pooling and timeout handling
  - Query methods:
    - `find_one()` - Get single document
    - `find_many()` - Get multiple with sorting
    - `insert_one()` - Insert with timestamps
    - `update_one()` - Update with updatedAt
    - `delete_one()` - Delete document
    - `count_documents()` - Count matching
    - `get_distinct()` - Get unique values
  - Health check capability
  - Error handling with custom exceptions

---

### Data Models (`app/models/`)

#### `schemas.py` - Pydantic Data Models
- **Purpose**: Input/output validation and serialization
- **Key Models**:
  - **Input**:
    - `RecommendationRequest` - User request for recommendations
    - `FeedAnalysisRequest` - Feed content analysis request
  - **Output**:
    - `RecommendationResponse` - Ranked feed recommendations
    - `AnalysisResponse` - Content classification results
    - `FeedRecommendation` - Single feed with score
    - `FeedAnalysisResult` - Detailed analysis breakdown
  - **Internal**:
    - `CategoryMetadata` - Category information
    - `ScoringMetrics` - Score breakdown
    - `UserProfile` - User data model
  - **Standard**:
    - `ErrorResponse` - Error format
    - `HealthCheckResponse` - Health status

---

### Recommendation Engine (`app/engine/`)

#### `optimizer.py` - RFRE Recommendation Engine
- **Purpose**: Core recommendation scoring and generation
- **Key Components**:
  - `CategoryOptimizer` - Main optimizer class
  - Scoring methods:
    - `_calculate_festival_score()` - Festival relevance (32+ festivals)
    - `_calculate_push_score()` - Viral threshold detection
    - `_calculate_trending_score()` - Views + likes normalization
    - `_calculate_time_relevance_score()` - Time-aware recommendations
  - `calculate_final_score()` - Combines all scores with weights
  - `get_recommendations()` - Main recommendation pipeline
  - `_apply_diversity_filter()` - Cross-category diversity
  - Category caching (1-hour TTL)
  - Singleton instance via `get_optimizer()`

**Scoring Algorithm**:
```
Final Score = (0.40 × Festival) + (0.30 × Push) + (0.30 × Trending)
              × 1.5 (if Time Relevant)
              Capped at 100
```

---

### REST API Layer (`app/api/`)

#### `routes.py` - FastAPI Application
- **Purpose**: HTTP endpoints for Node.js integration
- **Key Endpoints**:
  - `GET /health` - Health check
  - `GET /` - Root info
  - `POST /api/v1/recommend` - Get recommendations
  - `POST /api/v1/analyze` - Analyze feed content
  - `GET /api/v1/errors` - Error code reference
- **Key Features**:
  - Lifespan management (startup/shutdown)
  - Exception handlers for custom/validation errors
  - CORS middleware
  - Request/response logging
  - Content analysis helpers:
    - `_classify_content_type()`
    - `_classify_emotion()`
    - `_extract_topics()`
    - `_generate_recommendation_tags()`

---

### Exception Handling (`app/exceptions.py`)

- **Purpose**: Production-grade error handling with codes
- **Components**:
  - `ErrorCode` enum (15+ codes)
  - `PrithuException` - Base exception class
  - Derived exceptions:
    - `DatabaseException`
    - `DatabaseConnectionException`
    - `ResourceNotFoundException`
    - `ValidationException`
    - `OptimizerException`
    - `ScoringException`
    - `CacheException`
  - Standardized JSON error responses

---

## 🔄 Data Flow Architecture

```
NODE.JS BACKEND
       ↓
    HTTP Request
  (POST /api/v1/recommend)
       ↓
   FastAPI Routes
  (app/api/routes.py)
       ↓
   Request Validation
  (Pydantic schemas)
       ↓
  Recommendation Engine
  (app/engine/optimizer.py)
       ├─ Load Categories
       │  (Database query)
       ├─ Score Feeds
       │  (5-component scoring)
       ├─ Apply Filters
       │  (Diversity, preferences)
       └─ Sort & Return Top N
       ↓
   Database Queries
  (app/database/db_connection.py)
       ↓
    MongoDB Atlas
   (Prithu-DB)
       ↓
   Response Format
  (RecommendationResponse)
       ↓
    HTTP Response
       ↓
NODE.JS BACKEND
```

---

## 📦 Dependencies

All dependencies specified in `requirements-new.txt`:

**Framework**:
- `fastapi==0.104.1` - Web framework
- `uvicorn[standard]==0.24.0` - ASGI server
- `pydantic==2.5.0` - Data validation

**Database**:
- `pymongo==4.6.0` - MongoDB driver
- `python-dotenv==1.0.0` - Environment variables

**Data Processing**:
- `pandas==2.1.3` - Data manipulation
- `numpy==1.26.2` - Numerical computing
- `scikit-learn==1.3.2` - ML utilities

**ML/AI** (Phase 2):
- `torch==2.1.1` - Deep learning
- `transformers==4.35.2` - NLP models
- `ultralytics==8.0.207` - YOLO object detection
- `easyocr==1.7.1` - Optical character recognition

**Caching**:
- `redis==5.0.1` - Redis client

**Development**:
- `pytest==7.4.3` - Testing framework
- `black==23.12.0` - Code formatter
- `pylint==3.0.3` - Code linter
- `mypy==1.7.1` - Type checker

---

## 🚀 How to Use This Structure

### 1. **Running the Application**
```bash
cd "Backend - New"
python main.py
```
Server starts on `http://localhost:8000`

### 2. **Making Requests**
```bash
# Get recommendations
curl -X POST http://localhost:8000/api/v1/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user123","limit":20}'

# Analyze feed
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"feed_id":"feed123","caption":"Good morning","post_type":"image"}'
```

### 3. **Importing Modules**
```python
# In other Python files:
from app.core.config import Config
from app.database.db_connection import get_db_manager
from app.engine.optimizer import get_optimizer
from app.models.schemas import RecommendationRequest
from app.exceptions import PrithuException
```

### 4. **Running Tests**
```bash
pytest tests/
```

---

## 🎯 Design Patterns Used

✅ **Singleton Pattern**: `DatabaseManager`, `LoggerSetup`, `CategoryOptimizer`
✅ **Dependency Injection**: Via `get_*()` functions
✅ **Factory Pattern**: Logger and optimizer creation
✅ **Exception Hierarchy**: Custom exception types with codes
✅ **Caching**: Category caching with TTL
✅ **MVC Separation**: Models (schemas) → Controllers (api) → Logic (optimizer)

---

## 📊 Module Sizes

| Module | Lines | Purpose |
|--------|-------|---------|
| config.py | ~295 | Configuration |
| exceptions.py | ~195 | Error handling |
| logger_setup.py | ~85 | Logging |
| db_connection.py | ~450 | Database |
| schemas.py | ~250 | Data validation |
| optimizer.py | ~550 | Recommendation engine |
| routes.py | ~500 | API endpoints |
| main.py | ~57 | Entry point |
| **TOTAL** | **~2,382** | **Full backend** |

---

## ✅ Production Features

✓ Type hints throughout (mypy compatible)
✓ Comprehensive error handling
✓ Structured logging
✓ Input validation (Pydantic)
✓ Database connection pooling
✓ Singleton patterns (no resource leaks)
✓ Graceful shutdown
✓ Health checks
✓ CORS support
✓ API documentation (/docs)
✓ Configurable via environment variables
✓ Docker-ready structure

---

## 🔗 Integration with Node.js

The Node.js backend calls these endpoints:
- `POST /api/v1/recommend` - Get feed recommendations
- `POST /api/v1/analyze` - Analyze feed content
- `GET /health` - Check backend health

All responses are in standardized JSON format with error codes.

---

## 📝 Next Steps

1. **Testing**: Run integration tests with Node.js
2. **Phase 2**: Add ML models (sentiment, object detection)
3. **Caching**: Implement Redis for scored feeds
4. **Monitoring**: Add metrics and dashboards
5. **Deployment**: Docker containerization

---

**Structure Created**: September 2026
**Status**: ✅ Production Ready
