# Multi-Source RAG + Text-to-SQL System

A production-ready FastAPI application that combines **Document RAG (Retrieval-Augmented Generation)** with **Text-to-SQL** capabilities, featuring intelligent query routing, multi-level caching, and cost optimization.

## ✨ Key Highlights

- 🎯 **18 Production-Ready API Endpoints** for comprehensive RAG + SQL operations
- ⚡ **Multi-Level Caching**: Document cache (S3/local) + Query cache (Redis) = 40-60% cost reduction
- 💰 **Cost Optimization**: ~$0.05 saved per cached RAG query, ~$0.08 per cached SQL generation
- 🧠 **Intelligent Routing**: Automatic SQL/Documents/Hybrid detection with 30+ keywords each
- 🔬 **Advanced Document Processing**: Docling integration with heading preservation and context-aware chunking
- ☁️ **Production-Ready**: AWS Lambda deployment with CI/CD, ARM64 optimization (20% cheaper)

---

## 📋 Table of Contents

- [Features](#features)
- [System Architecture](#system-architecture)
- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Usage Examples](#usage-examples)
- [Performance & Caching](#performance--caching)
- [Query Routing](#query-routing)
- [Architecture Deep Dive](#architecture-deep-dive)
- [Deployment](#deployment)
- [Evaluation](#evaluation)
- [Development](#development)
- [Resources](#resources)

---

## 🌟 Features

### Core Query Capabilities

- **Document RAG**: Query uploaded documents with GPT-4 + Pinecone retrieval
- **Text-to-SQL**: Natural language → SQL with Vanna 2.0 + approval workflow
- **Intelligent Routing**: Automatic query classification (SQL/Documents/Hybrid)
- **Hybrid Queries**: Combine database results with document context

### Intelligent Caching & Cost Optimization

- **Document Cache** (S3/Local): SHA-256 content-based deduplication for files
- **Query Cache** (Redis): 5-10ms retrieval for RAG answers, SQL, embeddings
- **Embedding Cache**: Per-text caching with 7-day TTL
- **Smart Invalidation**: Pattern-based cache clearing, automatic staleness detection
- **Cost Tracking**: Real-time estimated savings from cache hits

### Advanced Document Processing

- **Docling Integration**: Context-aware parsing with HybridChunker
- **Structure Preservation**: Heading hierarchy, page numbers, captions
- **Multi-Format Support**: PDF, DOCX, CSV, JSON, TXT with optimized parsers
- **Smart Chunking**: 256-512 token chunks with semantic boundaries

### Production Features

- **AWS Lambda Deployment**: Serverless with ARM64 (20% cost savings)
- **OPIK Monitoring**: LLM observability for all key endpoints
- **Comprehensive Validation**: File type/size, query length, SQL safety
- **Error Handling**: Structured responses with detailed messages

---

## 📊 System Architecture

```
┌─────────────────────────────────────────────────┐
│              Client Request                     │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│         1. Query Cache (Redis)                  │
│         • 5-10ms retrieval                      │
│         • RAG answers, SQL, embeddings          │
│         • TTL: 1-24 hours by type               │
└────────────────┬────────────────────────────────┘
                 │ MISS
                 ▼
┌─────────────────────────────────────────────────┐
│         2. Document Cache (S3/Local)            │
│         • SHA-256 content hashing               │
│         • Chunks, embeddings, metadata          │
│         • 100-200ms retrieval                   │
└────────────────┬────────────────────────────────┘
                 │ MISS
                 ▼
┌─────────────────────────────────────────────────┐
│         3. Full Processing                      │
│         • OpenAI API calls                      │
│         • Pinecone vector operations            │
│         • 2-5 seconds processing                │
└─────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

```bash
# 1. Clone the repository
cd text2sqlrag-project

# 2. Create virtual environment (Python 3.12+)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
# OR using UV (faster):
uv pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your API keys (see Configuration section)

# 5. Run the application
uvicorn app.main:app --reload

# 6. Visit the API docs
open http://localhost:8000/docs
```

---

## 📦 Prerequisites

### For Local Development

- **Python 3.12+**
- **OpenAI API Key** (for embeddings and LLM)
- **Pinecone Account** (for vector storage)
  - Create an index with dimension=1536, metric=cosine
- **PostgreSQL Database** (for Text-to-SQL)
  - Supabase recommended for easy setup
- **OPIK API Key** (optional, for monitoring)
- **Upstash Redis** (optional, for query caching - 40-60% cost savings)

### For AWS Lambda Deployment

**All of the above, plus:**

- **AWS Account** with admin access or permissions for ECR, Lambda, IAM, API Gateway
- **AWS CLI** (version 2.x) configured with credentials
- **Docker** for building Lambda container images
- **GitHub Repository** for CI/CD pipeline
- **Estimated Setup Time**: 30-45 minutes (one-time)

📖 **See [Deployment Troubleshooting](DEPLOYMENT_FIXES.md) for AWS setup instructions and common fixes**

---

## ⚙️ Configuration

Create a `.env` file in the project root:

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-...

# Pinecone Configuration
PINECONE_API_KEY=pcsk_...
PINECONE_ENVIRONMENT=us-east-1-aws
PINECONE_INDEX_NAME=rag-documents

# Supabase/PostgreSQL Configuration (IPv4 Session Pooler for Lambda)
DATABASE_URL=postgresql://user:password@host:port/database

# OPIK Monitoring (Optional)
OPIK_API_KEY=  # Leave empty for local tracking

# Upstash Redis (Optional - enables query caching for 40-60% cost savings)
UPSTASH_REDIS_URL=https://your-redis-url.upstash.io
UPSTASH_REDIS_TOKEN=your-redis-token

# Text Chunking Configuration
CHUNK_SIZE=512
MIN_CHUNK_SIZE=256
CHUNK_OVERLAP=50

# SQL LLM Configuration (Determinism)
VANNA_TEMPERATURE=0.0  # 0.0 = fully deterministic
VANNA_TOP_P=0.1
VANNA_SEED=42
VANNA_MAX_TOKENS=2000

# Cache TTL Configuration (in seconds)
CACHE_TTL_EMBEDDINGS=604800  # 7 days - embeddings are static
CACHE_TTL_RAG=3600           # 1 hour - may change with new documents
CACHE_TTL_SQL_GEN=86400      # 24 hours - schema relatively stable
CACHE_TTL_SQL_RESULT=900     # 15 minutes - data changes frequently
```

### SQL Determinism Configuration

**Why SQL Generation Needs Determinism:**

By default, language models use high randomness (temperature=1.0), which causes **inconsistent SQL generation** - the same question produces different SQL queries on each run. This is problematic for production systems where users expect predictable results.

**Solution:**

The system enforces **deterministic SQL generation** by controlling the LLM's randomness parameters:

- **`VANNA_TEMPERATURE`** (default: `0.0`): Controls randomness
  - `0.0` = Fully deterministic (recommended for production)
  - `0.1-0.2` = Slight variation while maintaining consistency
  - `1.0` = Creative but unpredictable

- **`VANNA_TOP_P`** (default: `0.1`): Nucleus sampling threshold
- **`VANNA_SEED`** (default: `42`): Random seed for reproducibility
- **`VANNA_MAX_TOKENS`** (default: `2000`): Maximum SQL length

**Expected Behavior:**
- With `VANNA_TEMPERATURE=0.0`: Same question → Identical SQL (>95% of time)
- Without determinism: Same question → Different SQL each time ❌

---

## 📖 API Reference

### Core Query Endpoints (Most Important)

#### **POST `/query`** - Unified Intelligent Routing ⭐ RECOMMENDED

Automatically routes queries to SQL, Documents, or both (HYBRID) based on keyword analysis.

**Parameters:**
- `question` (string, required): Natural language question
- `auto_approve_sql` (bool, default=false): Auto-execute SQL (testing only)
- `top_k` (int, default=3): Number of document chunks to retrieve (1-10)

**Example:**
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Show total revenue and explain our pricing strategy"}'
```

**Response:**
```json
{
  "question": "Show total revenue and explain our pricing strategy",
  "route": "HYBRID",
  "routing_explanation": "Keywords detected: 'show' (SQL), 'explain' (DOCUMENTS)",
  "sql_component": {
    "query_id": "abc123",
    "sql": "SELECT SUM(total_amount) FROM orders;",
    "status": "pending_approval"
  },
  "document_component": {
    "answer": "Our pricing strategy focuses on...",
    "sources": [...]
  }
}
```

---

#### **POST `/query/documents`** - Document RAG Queries

Query uploaded documents using Retrieval-Augmented Generation.

**Parameters:**
- `question` (string, required): Question to answer (3-1000 characters)
- `top_k` (int, default=3): Number of document chunks to retrieve (1-10)

**Example:**
```bash
curl -X POST "http://localhost:8000/query/documents" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the return policy?", "top_k": 3}'
```

**Response:**
```json
{
  "answer": "Our return policy allows customers to return items within 30 days...",
  "sources": [
    {"text": "Return policy details...", "filename": "policy.pdf", "page": 5}
  ],
  "chunks_used": 3,
  "model": "gpt-4-turbo-preview",
  "cached": false,
  "usage": {
    "embedding_tokens": 150,
    "llm_prompt_tokens": 800,
    "llm_completion_tokens": 200,
    "total_tokens": 1150
  }
}
```

---

### Document Management

#### **POST `/upload`** - Upload Documents

Upload and process documents with automatic caching.

**Parameters:**
- `file` (file, required): Document file (max 50 MB)
- Supported formats: PDF, DOCX, DOC, CSV, JSON, TXT

**Example:**
```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@policy.pdf"
```

**Response:**
```json
{
  "status": "success",
  "filename": "policy.pdf",
  "document_id": "a3f8b2c1d4e5f6g7...",
  "file_size": "2.5 MB",
  "chunks_created": 15,
  "total_tokens": 7680,
  "cache_hit": false,
  "storage_backend": "s3",
  "message": "Document processed and 15 chunks stored in Pinecone"
}
```

---

#### **GET `/documents`** - List Uploaded Documents

Returns all uploaded documents with metadata.

**Example:**
```bash
curl http://localhost:8000/documents
```

**Response:**
```json
{
  "total_documents": 5,
  "documents": [
    {
      "filename": "policy.pdf",
      "size_bytes": 2621440,
      "uploaded_at": "2026-01-24T10:30:00"
    }
  ]
}
```

---

### Cache Management (Critical for Production)

#### **GET `/cache/query/stats`** - Query Cache Statistics

Get detailed cache hit rates and cost savings for RAG, embeddings, SQL generation, and SQL results.

**Example:**
```bash
curl http://localhost:8000/cache/query/stats
```

**Response:**
```json
{
  "status": "success",
  "cache_stats": {
    "enabled": true,
    "cache_types": {
      "rag": {
        "hits": 600,
        "misses": 400,
        "total_queries": 1000,
        "hit_rate": "60.0%",
        "estimated_cost_saved": "$30.0000"
      },
      "embedding": {
        "hits": 3000,
        "misses": 2000,
        "total_queries": 5000,
        "hit_rate": "60.0%",
        "estimated_cost_saved": "$0.0600"
      },
      "sql_gen": {
        "hits": 300,
        "misses": 200,
        "total_queries": 500,
        "hit_rate": "60.0%",
        "estimated_cost_saved": "$24.0000"
      },
      "sql_result": {
        "hits": 400,
        "misses": 100,
        "total_queries": 500,
        "hit_rate": "80.0%",
        "estimated_cost_saved": "$4.0000"
      }
    }
  },
  "total_estimated_savings": "$58.0600"
}
```

---

#### **DELETE `/cache/query`** - Clear Query Cache

Clear query cache by type or all types.

**Parameters:**
- `cache_type` (string, optional): Type to clear ("rag", "embedding", "sql_gen", "sql_result")

**Examples:**
```bash
# Clear all query caches
curl -X DELETE "http://localhost:8000/cache/query"

# Clear only RAG response cache
curl -X DELETE "http://localhost:8000/cache/query?cache_type=rag"

# Clear only SQL generation cache
curl -X DELETE "http://localhost:8000/cache/query?cache_type=sql_gen"
```

**Response:**
```json
{
  "status": "success",
  "cache_type": "rag",
  "keys_deleted": 245,
  "message": "Cleared rag cache"
}
```

---

#### **GET `/cache/stats`** - Document Cache Statistics

Get statistics about document cache (S3/local storage).

**Example:**
```bash
curl http://localhost:8000/cache/stats
```

**Response:**
```json
{
  "status": "success",
  "cache_stats": {
    "total_documents": 25,
    "total_size_bytes": 52428800,
    "total_size_human": "50.0 MB",
    "storage_backend": "s3"
  }
}
```

---

#### **DELETE `/cache/clear`** - Clear Document Cache

Clear document cache (S3/local) and optionally Redis query cache.

**Parameters:**
- `document_id` (string, optional): Specific document ID to clear

**Example:**
```bash
# Clear all document cache + Redis query cache
curl -X DELETE "http://localhost:8000/cache/clear"

# Clear specific document
curl -X DELETE "http://localhost:8000/cache/clear?document_id=a3f8b2c1..."
```

---

#### **DELETE `/vectors/clear`** - Clear Pinecone Vectors

Clear all vectors from Pinecone vector database (requires confirmation).

**Parameters:**
- `namespace` (string, default="default"): Namespace to clear
- `confirm` (bool, required): Must be `true` to proceed

**Example:**
```bash
curl -X DELETE "http://localhost:8000/vectors/clear?namespace=default&confirm=true"
```

---

### SQL Operations

#### **POST `/query/sql/generate`** - Generate SQL

Generate SQL from natural language question using Vanna.ai.

**Parameters:**
- `question` (string, required): Natural language question about the database

**Example:**
```bash
curl -X POST "http://localhost:8000/query/sql/generate" \
  -H "Content-Type: application/json" \
  -d '{"question": "How many customers do we have?"}'
```

**Response:**
```json
{
  "query_id": "abc123",
  "sql": "SELECT COUNT(*) FROM customers;",
  "explanation": "This query counts all rows in the customers table",
  "cached": false
}
```

---

#### **POST `/query/sql/execute`** - Execute SQL

Execute a previously generated SQL query after approval.

**Parameters:**
- `query_id` (string, required): ID from generate_sql endpoint
- `approved` (bool, default=true): Whether to execute or reject

**Example:**
```bash
curl -X POST "http://localhost:8000/query/sql/execute" \
  -H "Content-Type: application/json" \
  -d '{"query_id": "abc123", "approved": true}'
```

**Response:**
```json
{
  "status": "executed",
  "sql": "SELECT COUNT(*) FROM customers;",
  "results": [{"count": 1523}],
  "result_count": 1
}
```

---

#### **GET `/query/sql/pending`** - List Pending SQL Queries

List all SQL queries awaiting approval.

**Example:**
```bash
curl http://localhost:8000/query/sql/pending
```

**Response:**
```json
{
  "total_pending": 3,
  "pending_queries": [
    {
      "query_id": "abc123",
      "question": "How many customers?",
      "sql": "SELECT COUNT(*) FROM customers;",
      "created_at": "2026-01-24T10:30:00"
    }
  ]
}
```

---

### System Information

#### **GET `/health`** - Health Check

Verify API is running and check service connectivity.

**Example:**
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "Multi-Source RAG + Text-to-SQL API",
  "timestamp": "2026-01-24T10:30:00",
  "version": "0.1.0",
  "services": {
    "embedding_service": true,
    "vector_service": true,
    "rag_service": true,
    "sql_service": true,
    "query_cache": true
  },
  "configuration": {
    "openai_configured": true,
    "pinecone_configured": true,
    "database_configured": true,
    "redis_cache_configured": true
  }
}
```

---

#### **GET `/info`** - System Information

Get detailed system information and available features.

**Example:**
```bash
curl http://localhost:8000/info
```

---

#### **GET `/stats`** - System Statistics

Get usage statistics with cache performance and cost savings.

**Example:**
```bash
curl http://localhost:8000/stats
```

**Response:**
```json
{
  "documents": {
    "total_uploaded": 5,
    "total_size": "12.5 MB"
  },
  "sql": {
    "pending_queries": 3,
    "service_available": true
  },
  "query_cache": {
    "enabled": true,
    "by_type": {
      "rag": {"hits": 600, "hit_rate": "60.0%", "estimated_cost_saved": "$30.00"}
    },
    "total_estimated_savings": "$58.06"
  }
}
```

---

#### **GET `/docs`** - Swagger UI

Interactive API documentation (Swagger UI).

---

#### **GET `/redoc`** - ReDoc

Alternative API documentation (ReDoc format).

---

## 💡 Usage Examples

### Example 1: Upload Document with Cache

```bash
# First upload - Full processing
curl -X POST "http://localhost:8000/upload" -F "file=@policy.pdf"

# Response:
{
  "status": "success",
  "filename": "policy.pdf",
  "chunks_created": 15,
  "processing_time": "2.3s",
  "cached": false,
  "cache_id": "a3f8b2c1...",
  "storage_backend": "s3"
}

# Re-upload same file (different name) - Cache hit
curl -X POST "http://localhost:8000/upload" -F "file=@policy_copy.pdf"

# Response:
{
  "status": "success",
  "filename": "policy_copy.pdf",
  "chunks_created": 15,
  "processing_time": "0.15s",  # 15x faster!
  "cached": true,
  "cache_id": "a3f8b2c1...",
  "message": "Document loaded from cache and 15 chunks stored in Pinecone"
}
```

---

### Example 2: RAG Query with Cache

```bash
# First query - Full processing
curl -X POST "http://localhost:8000/query/documents" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the return policy?", "top_k": 3}'

# Response includes cache status:
{
  "answer": "Our return policy allows customers to return items within 30 days...",
  "sources": [...],
  "cached": false,
  "usage": {
    "total_tokens": 1200
  }
}

# Same query again - Cache hit (within 1 hour)
curl -X POST "http://localhost:8000/query/documents" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the return policy?", "top_k": 3}'

# Response:
{
  "answer": "Our return policy allows customers to return items within 30 days...",
  "sources": [...],
  "cached": true,
  "cache_age": "5m 23s",
  "usage": {
    "total_tokens": 0  # No API calls made!
  }
}
# Cost saved: ~$0.048 per cached query
```

---

### Example 3: Manage Cache

```bash
# View cache statistics
curl http://localhost:8000/cache/query/stats

# Clear specific cache type (e.g., all RAG cache)
curl -X DELETE "http://localhost:8000/cache/query?cache_type=rag"

# Clear all query cache
curl -X DELETE "http://localhost:8000/cache/query"

# Clear document cache (S3 + Redis)
curl -X DELETE "http://localhost:8000/cache/clear"
```

---

### Example 4: SQL Query with Routing

```bash
# Intelligent routing automatically detects SQL query
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "How many orders were placed last month?", "auto_approve_sql": true}'

# Response:
{
  "question": "How many orders were placed last month?",
  "route": "SQL",
  "routing_explanation": "Keywords detected: 'how many' (SQL), 'orders' (SQL)",
  "sql": "SELECT COUNT(*) FROM orders WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month');",
  "results": [{"count": 1245}],
  "status": "executed"
}
```

---

## ⚡ Performance & Caching

### Multi-Level Caching Architecture

The system implements a sophisticated two-tier caching strategy to maximize performance and minimize costs:

```
┌─────────────────────────────────────────────────┐
│              Client Request                     │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│         Tier 1: Query Cache (Redis)             │
│         • 5-10ms retrieval speed                │
│         • RAG answers, SQL, embeddings          │
│         • TTL: 15min - 7 days by type           │
│         • ~$58/day savings at 60% hit rate      │
└────────────────┬────────────────────────────────┘
                 │ MISS
                 ▼
┌─────────────────────────────────────────────────┐
│      Tier 2: Document Cache (S3/Local)          │
│         • SHA-256 content hashing               │
│         • Chunks, embeddings, metadata          │
│         • 100-200ms retrieval                   │
│         • Permanent storage                     │
└────────────────┬────────────────────────────────┘
                 │ MISS
                 ▼
┌─────────────────────────────────────────────────┐
│         Full Processing Pipeline                │
│         • OpenAI API calls                      │
│         • Pinecone vector operations            │
│         • 2-5 seconds total time                │
└─────────────────────────────────────────────────┘
```

---

### Cache Types and TTL

| Cache Type | Storage | Purpose | TTL | Cost Savings per Hit |
|------------|---------|---------|-----|---------------------|
| **RAG Answers** | Redis | Full query responses | 1 hour | ~$0.05 |
| **SQL Generation** | Redis | Generated SQL queries | 24 hours | ~$0.08 |
| **SQL Results** | Redis | Query execution results | 15 minutes | ~$0.01 |
| **Embeddings** | Redis | OpenAI text embeddings | 7 days | ~$0.00002 |
| **Document Chunks** | S3/Local | Parsed + chunked files | Permanent | Avoids re-processing |

**TTL Configuration:**
- **Embeddings (7 days)**: Static, rarely change
- **SQL Generation (24 hours)**: Schema relatively stable
- **RAG Answers (1 hour)**: May change with new documents
- **SQL Results (15 minutes)**: Data changes frequently

---

### Cost Savings Analysis

#### Without Caching (1000 queries/day)

| Operation | Requests/Day | Cost per Request | Daily Cost |
|-----------|--------------|------------------|------------|
| RAG queries | 1000 | $0.05 | $50.00 |
| Embeddings | 5000 | $0.00002 | $0.10 |
| SQL generation | 500 | $0.08 | $40.00 |
| SQL execution | 500 | $0.01 | $5.00 |
| **Total** | | | **$95.10/day** |

**Monthly Cost**: ~$2,853/month

---

#### With Caching (60% hit rate)

| Operation | Cache Hits | API Calls | Daily Cost | Savings |
|-----------|------------|-----------|------------|---------|
| RAG queries | 600 | 400 | $20.00 | $30.00 |
| Embeddings | 3000 | 2000 | $0.04 | $0.06 |
| SQL generation | 300 | 200 | $16.00 | $24.00 |
| SQL execution | 300 | 200 | $2.00 | $3.00 |
| **Total** | | | **$38.04/day** | **$57.06/day** |

**Monthly Cost**: ~$1,141/month
**Monthly Savings**: ~$1,712/month (60% reduction)

---

### Cache Performance Monitoring

Monitor cache effectiveness in real-time:

```bash
# Get detailed cache statistics
curl http://localhost:8000/cache/query/stats
```

**Response shows:**
- Hit rates by cache type (rag, embedding, sql_gen, sql_result)
- Total queries processed
- Estimated cost savings in dollars
- Cache health status

**Target Hit Rates:**
- Embeddings: 70-80% (same text chunks)
- RAG answers: 40-60% (repeated questions)
- SQL generation: 50-70% (common queries)
- SQL results: 60-80% (frequent data access)

---

### Smart Cache Invalidation

The system automatically invalidates stale cache entries:

1. **New Document Upload**: Clears RAG cache (answers may change)
2. **Pattern-Based**: Clear by type (`rag:*`, `sql_gen:*`, etc.)
3. **Manual Control**: API endpoints for selective cache clearing
4. **Automatic TTL**: Entries expire based on data volatility

**Example: Clear RAG cache after document upload**
```bash
# Upload new document
curl -X POST "http://localhost:8000/upload" -F "file=@new_policy.pdf"

# System automatically clears RAG cache
# Next RAG query will get fresh results with new document
```

---

## 🧭 Query Routing

The system automatically routes queries based on keyword analysis:

### SQL Queries

Routed to Text-to-SQL service for data retrieval.

**Keywords** (30+ total): `count`, `total`, `sum`, `average`, `revenue`, `sales`, `orders`, `customers`, `list all`, `show all`, `how many`, `top`, `bottom`, `last`, `recent`, etc.

**Examples:**
- "How many customers do we have?"
- "What is the total revenue from delivered orders?"
- "Show me the top 10 customers by spending"

---

### Document Queries

Routed to RAG service for information retrieval.

**Keywords** (25+ total): `what is`, `explain`, `define`, `policy`, `procedure`, `guide`, `manual`, `how to`, `why`, `according to`, etc.

**Examples:**
- "What is our return policy?"
- "Explain the customer complaint procedure"
- "How should I process a refund?"

---

### Hybrid Queries

Routed to both services, combining data with context.

**Keywords** (8+ total): `and explain`, `and describe`, `show data and explain`, etc.

**Examples:**
- "Show total revenue by segment and explain our segmentation strategy"
- "List top products and describe pricing policies"

---

## 🏗️ Architecture Deep Dive

### Components

**Core Services:**
- **Document Service**: Parses PDF/DOCX/CSV/JSON using Docling (primary) + Unstructured.io (fallback)
- **Docling Service**: Context-aware parsing with HybridChunker for structure preservation
- **Embedding Service**: OpenAI text-embedding-3-small (1536 dimensions) with Redis caching
- **Vector Service**: Pinecone with gRPC for fast vector operations
- **RAG Service**: Retrieval + GPT-4 generation with source citations, Redis caching
- **SQL Service**: Vanna.ai for Text-to-SQL with training on schema, Redis caching
- **Cache Service**: SHA-256 content-based deduplication for chunks and embeddings (S3/local)
- **Query Cache Service**: Redis-based high-speed query result caching

**Routing & Validation:**
- **Query Router**: Keyword-based intelligent routing (SQL/Documents/Hybrid)
- **Validation**: File type/size, query length, SQL safety checks

**Deployment Options:**
- **AWS Lambda (Production)**: ARM64 serverless with API Gateway, CloudWatch, CI/CD
- **Docker (Development)**: Local containerized deployment for testing

**Monitoring:**
- **OPIK Tracking**: End-to-end request monitoring on all key endpoints
- **CloudWatch Logs**: Real-time Lambda logs and metrics (production only)

---

## 🚀 Deployment

### Deployment Overview

| Option | Best For | Setup Time | Monthly Cost |
|--------|----------|------------|--------------|
| **AWS Lambda** ⭐ | Production, team collaboration | 30-45 min | ~$127-227 |
| **Docker** | Local development, testing | 5 min | Self-hosted |

**Recommendation**: Use **AWS Lambda** for production, **Docker** for local development.

---

### Production (AWS Lambda) ⭐ RECOMMENDED

Serverless deployment with automatic scaling and CI/CD.

#### What You Get

- ☁️ **Serverless**: Automatic scaling (0 to 1000s of requests)
- 🔄 **CI/CD**: Push to `main` → Automatic deployment via GitHub Actions
- ⚡ **ARM64 Optimized**: 20% cheaper than x86_64 Lambda costs
- 📊 **CloudWatch Monitoring**: Real-time logs and metrics
- 🌐 **HTTPS API**: API Gateway endpoint with /prod base path

#### Quick Deploy

**1. One-Time Setup** (30-45 minutes)

Follow the complete guide to create:
- Lambda function (8GB RAM, ARM64, 15min timeout)
- ECR repository for Docker images
- API Gateway HTTP API
- GitHub Actions secrets


**2. Deploy Code** (automatic, ~15 minutes)

```bash
git add .
git commit -m "Update feature"
git push origin main  # GitHub Actions deploys automatically
```

**3. Your API is Live**

```
https://{api-id}.execute-api.us-east-1.amazonaws.com/prod/query
https://{api-id}.execute-api.us-east-1.amazonaws.com/prod/docs
https://{api-id}.execute-api.us-east-1.amazonaws.com/prod/health
```

#### Cost Estimate (100K requests/month, 30s avg)

**AWS Services (ARM64):**
- Lambda (ARM64): ~$40-65/month
- API Gateway: ~$1/month
- ECR: ~$0.50/month
- CloudWatch Logs: ~$5/month
- Data Transfer: ~$0.90/month
- **AWS Total**: ~$47-72/month

**External Services:**
- OpenAI: ~$10-30/month
- Pinecone: ~$70-100/month
- Supabase: ~$0-25/month
- **External Total**: ~$80-155/month

**Grand Total**: ~$127-227/month

💡 **ARM64 saves ~$10-16/month (20%) vs x86_64**

---

### Local Development (Docker)

#### Quick Start with Docker Compose

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 2. Start container
docker-compose up -d

# 3. API available at http://localhost:8000

# 4. View logs
docker-compose logs -f

# 5. Stop container
docker-compose down
```

#### When to Use

**Use Docker for:**
- ✅ Local development and testing
- ✅ Self-hosted deployment
- ✅ Learning without AWS setup

**Use Lambda for:**
- ⭐ Production deployments
- ⭐ Team collaboration
- ⭐ Automatic scaling
- ⭐ Minimal infrastructure management

---

## 📊 Evaluation

Run the RAGAS evaluation to measure system quality:

```bash
python evaluate.py
```

**Metrics:**
- **Faithfulness** (target > 0.7): Answer accuracy based on retrieved context
- **Answer Relevancy** (target > 0.8): How well the answer matches the question

**Output:**
- Console: Real-time progress and scores
- File: `evaluation_results.json` with detailed results

---

## 👨‍� Development

### Project Structure

```
text2sqlrag-project/
├── .github/
│   └── workflows/
│       ├── deploy.yml                  # CI/CD deployment pipeline
│       └── test.yml                    # PR testing workflow
├── app/
│   ├── __init__.py
│   ├── main.py                         # FastAPI app with 18 endpoints
│   ├── config.py                       # Pydantic settings
│   ├── logging_config.py               # Logging configuration
│   ├── utils.py                        # Validation and error handling
│   └── services/
│       ├── __init__.py
│       ├── cache_service.py            # Document cache orchestrator
│       ├── docling_service.py          # Docling integration
│       ├── document_service.py         # Document parsing & chunking
│       ├── embedding_service.py        # OpenAI embeddings (with cache)
│       ├── local_storage.py            # Local file storage backend
│       ├── query_cache_service.py      # Query cache (Redis)
│       ├── rag_service.py              # RAG pipeline (with cache)
│       ├── router_service.py           # Query routing
│       ├── s3_storage.py               # S3 storage backend
│       ├── sql_service.py              # Vanna Text-to-SQL (with cache)
│       ├── storage_backend.py          # Storage backend interface
│       └── vector_service.py           # Pinecone operations
├── data/
│   ├── cached_chunks/                  # Document cache (gitignored)
│   ├── uploads/                        # Uploaded documents (gitignored)
│   ├── sql/
│   │   └── schema.sql                  # Database schema
│   └── generate_sample_data.py         # Sample data generator
├── logs/                               # Application logs (gitignored)
│   ├── app.log
│   └── error.log
├── notebooks/                          # Jupyter notebooks for exploration
│   └── vanna_ai_text_to_sql_complete.ipynb
├── tests/
│   ├── test_queries.json               # Evaluation test queries
│   └── test_storage_backends.py        # Storage backend tests
├── .dockerignore                       # Docker build exclusions
├── .env.example                        # Environment template
├── .gitignore                          # Git ignore rules
├── Dockerfile                          # Local Docker image
├── Dockerfile.lambda                   # Lambda Docker image (no OCR)
├── Dockerfile.lambda.with-tesseract    # Lambda Docker image (with OCR)
├── docker-compose.yml                  # Docker Compose config
├── evaluate.py                         # RAGAS evaluation script
├── lambda_handler.py                   # Lambda entry point
├── pyproject.toml                      # UV/Python project config
├── README.md                           # This file
├── requirements.txt                    # Python dependencies
├── s3-cache-policy.json                # S3 bucket policy for cache
├── trust-policy.json                   # IAM trust policy for Lambda
└── uv.lock                             # UV dependency lock file
```

### Running Tests

```bash
# Run evaluation
python evaluate.py

# Test individual endpoints
curl http://localhost:8000/health
curl http://localhost:8000/info
curl http://localhost:8000/cache/query/stats
```

### Code Style

- **Type hints**: All functions have type annotations
- **Docstrings**: Google-style docstrings for all public functions
- **Validation**: Input validation on all endpoints
- **Error handling**: Structured error responses

---

## 📚 Resources

### Core Technologies

- [FastAPI Documentation](https://fastapi.tiangolo.com) - Modern Python web framework
- [Pinecone Documentation](https://docs.pinecone.io) - Vector database for embeddings
- [Vanna.ai Documentation](https://vanna.ai/docs) - Text-to-SQL generation
- [RAGAS Documentation](https://docs.ragas.io) - RAG evaluation framework
- [OPIK Documentation](https://www.opik.ai/docs) - LLM monitoring and tracking
- [Docling Documentation](https://github.com/DS4SD/docling) - Advanced document understanding
- [OpenAI API Documentation](https://platform.openai.com/docs) - Embeddings and LLM
- [Upstash Redis Documentation](https://docs.upstash.com/redis) - Serverless Redis

### AWS Deployment

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/) - Serverless compute
- [API Gateway HTTP API Guide](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html)
- [Amazon ECR Documentation](https://docs.aws.amazon.com/ecr/) - Container registry
- [CloudWatch Logs Documentation](https://docs.aws.amazon.com/cloudwatch/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions) - CI/CD workflows
- [Docker Multi-Platform Builds](https://docs.docker.com/build/building/multi-platform/)

### Project Deployment Guides

**Start here for deployment**:
- 🔧 [Deployment Troubleshooting](DEPLOYMENT_FIXES.md) - Fix common AWS Lambda issues
- 📖 [Project Context](CLAUDE.md) - Complete implementation history and decisions

---

## 🎯 Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Document Upload | All formats work | Test with PDF, DOCX, CSV, JSON |
| Document Retrieval | Top-3 relevant chunks | Manual review of query results |
| SQL Generation | 70%+ accuracy | Run evaluate.py |
| Query Routing | 80%+ correct | Test with mixed queries |
| RAGAS Faithfulness | > 0.7 | Run evaluate.py |
| RAGAS Relevancy | > 0.8 | Run evaluate.py |
| Response Time | < 15 seconds | Monitor OPIK dashboard |
| Cache Hit Rate | 40-60% | Check /cache/query/stats |
| Cost Reduction | 40-60% | Monitor cache savings |

---

**Built with ❤️ using FastAPI, OpenAI, Pinecone, Vanna.ai, Docling, Upstash Redis, and AWS Lambda**
