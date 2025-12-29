# Ark Auto-Summarizer - Technical Specification

## 1. Project Overview

**Ark Auto-Summarizer** is an automated audio transcription and summarization system that combines modern AI technologies with a microservices architecture. The system processes audio files through speech recognition, generates intelligent summaries using large language models, and provides a web-based interface for user interaction.

### 1.1 Purpose
- Automate batch audio transcription with timestamps
- Generate AI-powered summaries of transcribed content
- Provide user authentication and management through Microsoft Entra ID
- Deliver a responsive web interface for audio file management

### 1.2 Architecture
Three-tier microservices architecture:
- **Frontend**: React-based web application
- **Backend**: FastAPI REST API service
- **Summarizer**: Docker-containerized AI processing service

---

## 2. System Components

### 2.1 Frontend (React + TypeScript)

**Location**: `./frontend/`

**Technology Stack**:
| Component | Version |
|-----------|---------|
| React | 19.1.0 |
| TypeScript | 5.7.2 |
| Vite | 7.0.4 |
| Tailwind CSS | 3.x |
| Mantine | 7.x |

**Key Dependencies**:
- `@azure/msal-browser`: Microsoft Entra ID authentication
- `@mantine/core`: UI component library
- `framer-motion`: Animation library
- `react-router-dom`: Client-side routing

**Structure**:
```
frontend/
├── src/
│   ├── components/     # Reusable UI components
│   ├── pages/          # Page components
│   ├── services/       # API clients, auth services
│   ├── hooks/          # Custom React hooks
│   ├── types/          # TypeScript type definitions
│   └── utils/          # Utility functions
├── public/             # Static assets
├── vite.config.ts      # Vite configuration
└── package.json        # Dependencies
```

### 2.2 Backend (FastAPI)

**Location**: `./backend/`

**Technology Stack**:
| Component | Version |
|-----------|---------|
| FastAPI | 0.116.1 |
| Python | 3.12 |
| SQLAlchemy | 2.0.42 |
| PostgreSQL | - |
| Uvicorn | - |

**Key Dependencies**:
- `fastapi`: Web framework
- `sqlalchemy`: ORM for database operations
- `asyncpg`: Async PostgreSQL driver
- `pydantic`: Data validation
- `alembic`: Database migrations
- `python-jose`: JWT handling
- `passlib`: Password hashing
- `python-multipart`: Form data parsing

**API Endpoints**:
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | User login |
| POST | `/api/auth/register` | User registration |
| GET | `/api/users/me` | Get current user |
| PUT | `/api/users/me` | Update user profile |
| POST | `/api/audio/upload` | Upload audio files |
| GET | `/api/audio/{id}` | Get audio file details |
| GET | `/api/transcriptions` | List transcriptions |
| GET | `/api/transcriptions/{id}` | Get transcription details |

**Structure**:
```
backend/
├── app/
│   ├── api/            # API route handlers
│   ├── core/           # Configuration, security
│   ├── models/         # Database models
│   ├── schemas/        # Pydantic schemas
│   ├── services/       # Business logic
│   └── db/             # Database session
├── alembic/            # Database migrations
├── requirements.txt    # Python dependencies
└── Dockerfile          # Container definition
```

### 2.3 Summarizer Service

**Location**: `./summarizer/`

**Technology Stack**:
| Component | Version |
|-----------|---------|
| Python | 3.12 |
| Faster-Whisper | 1.2.1 |
| NVIDIA CUDA | 12.x |
| Docker | - |

**Key Dependencies**:
- `faster-whisper`: Speech recognition
- `openai`: Azure OpenAI API client
- `python-dotenv`: Environment variable management
- `audioop`: Audio format conversion

**Configuration Files**:
- `.env.sample`: Environment variables template
- `summarize_prompt.md`: System prompt for AI summarization
- `Dockerfile_DEV`: Multi-stage Docker build

**Processing Pipeline**:
1. **Input**: Audio files from batch directory
2. **Transcription**: Faster-Whisper with CUDA acceleration
3. **Summarization** (optional): Azure OpenAI GPT-4o
4. **Output**: Text files with timestamps and summaries

**Structure**:
```
summarizer/
├── batch_transcribe.py    # Main processing script
├── .env.sample           # Environment template
├── summarize_prompt.md   # AI system prompt
├── Dockerfile_DEV        # Docker build definition
├── data/                 # Input audio files
├── output/               # Transcription results
└── models/               # Cached Whisper models
```

---

## 3. Audio Processing Specification

### 3.1 Supported Formats
- **Input**: m4a, mp3, wav, aac, flac, ogg
- **Output**: txt (transcription), md (summary with timestamps)

### 3.2 Transcription Configuration

| Setting | Value | Description |
|---------|-------|-------------|
| Model | large-v3-turbo | Whisper model for high accuracy |
| Device | CUDA | GPU acceleration |
| Compute Type | float16 | Precision for computation |
| Beam Size | 5 | Decoding beam size |
| VAD Filter | True | Voice Activity Detection enabled |
| VAD Threshold | 0.5 | Voice detection sensitivity |

### 3.3 Output Format

**Transcription File** (`{filename}_raw.txt`):
```
[00:00:00] <transcribed text segment 1>
[00:01:30] <transcribed text segment 2>
...
```

**Summary File** (`{filename}_summary.md`):
```markdown
# Summary

<generated summary content from Azure OpenAI>
```

---

## 4. AI Integration

### 4.1 Speech Recognition (Faster-Whisper)

**Model**: deepdml/faster-whisper-large-v3-turbo-ct2
- Optimized for high accuracy transcription
- Supports multilingual transcription
- GPU-accelerated via CUDA
- VAD filtering for silent regions

### 4.2 Summarization (Azure OpenAI)

**Model**: GPT-4o
**Endpoint**: Configured via `.env`

**System Prompt Template** (from `summarize_prompt.md`):
Customizable system prompt for generating summaries from transcriptions.

**API Configuration** (`.env`):
```bash
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<api-key>
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
```

---

## 5. Authentication & Authorization

### 5.1 Authentication Methods

**Microsoft Entra ID Integration**:
- MSAL (Microsoft Authentication Library)
- OAuth 2.0 / OpenID Connect
- Token-based authentication

**JWT-based API Authentication**:
- Access tokens with expiration
- Refresh token support
- Bearer token in Authorization header

### 5.2 User Roles

| Role | Permissions |
|------|-------------|
| Admin | Full system access, user management |
| User | Upload audio, view own transcriptions |
| Guest | Read-only access to public content |

---

## 6. Database Schema

### 6.1 Core Tables

**users**
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| email | VARCHAR(255) | Unique email address |
| azure_id | VARCHAR(255) | Microsoft Entra ID |
| full_name | VARCHAR(255) | User's full name |
| is_active | BOOLEAN | Account status |
| role | ENUM | User role |
| created_at | TIMESTAMP | Registration time |
| updated_at | TIMESTAMP | Last update |

**audio_files**
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key to users |
| filename | VARCHAR(255) | Original filename |
| file_path | TEXT | Storage path |
| file_size | BIGINT | Size in bytes |
| duration | INTEGER | Duration in seconds |
| status | ENUM | Processing status |
| created_at | TIMESTAMP | Upload time |

**transcriptions**
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| audio_file_id | UUID | Foreign key to audio_files |
| content | TEXT | Transcribed text |
| summary | TEXT | AI-generated summary |
| language | VARCHAR(10) | Detected language |
| confidence | FLOAT | Transcription confidence |
| created_at | TIMESTAMP | Processing time |

---

## 7. Docker Configuration

### 7.1 Development Environment

**docker-compose.dev.yml**:
```yaml
services:
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    volumes: ["./frontend:/app"]

  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql://...
    volumes: ["./backend:/app"]

  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=ark_summarizer
      - POSTGRES_USER=ark_user
      - POSTGRES_PASSWORD=ark_pass
    volumes: ["postgres_data:/var/lib/postgresql/data"]

  summarizer:
    build:
      context: ./summarizer
      dockerfile: Dockerfile_DEV
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]
    volumes:
      - ./summarizer/data:/app/data
      - ./summarizer/output:/app/output
```

### 7.2 Summarizer Dockerfile

**Dockerfile_DEV** - Multi-stage build:
```dockerfile
# Stage 1: Model download
FROM ubuntu:24.04 AS model-downloader
# Downloads and caches Whisper model

# Stage 2: Runtime
FROM nvidia/cuda:12.9.1-cudnn-runtime-ubuntu24.04
# Python 3.12 runtime with faster-whisper
```

---

## 8. Environment Variables

### 8.1 Backend Environment

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/ark_summarizer

# JWT
SECRET_KEY=<your-secret-key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Azure AD
AZURE_CLIENT_ID=<client-id>
AZURE_CLIENT_SECRET=<client-secret>
AZURE_TENANT_ID=<tenant-id>
```

### 8.2 Summarizer Environment

```bash
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<api-key>
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o

# Processing
DO_SUMMARIZE=true
MODEL_SIZE=deepdml/faster-whisper-large-v3-turbo-ct2
LANGUAGE=ja
COMPUTE_TYPE=float16
DEVICE=cuda
INPUT_FOLDER=input_audio
OUTPUT_FOLDER=batch_output
MAX_RETRIES=3
DELAY=5
```

---

## 9. Deployment

### 9.1 Development Launch

**Script**: `launch_summarizer.dev.sh`
```bash
#!/bin/bash
docker-compose -f docker-compose.dev.yml up --build
```

### 9.2 Production Deployment

```bash
# Build and start all services
docker-compose -f docker-compose.prd.yml up -d

# Run database migrations
docker-compose exec backend alembic upgrade head

# Check service health
docker-compose ps
```

---

## 10. API Endpoints Reference

### 10.1 Authentication

**POST /api/auth/login**
```json
// Request
{
  "email": "user@example.com",
  "password": "password123"
}

// Response
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": { "id": "...", "email": "..." }
}
```

**POST /api/auth/azure**
Redirects to Microsoft Entra ID login

### 10.2 Audio Management

**POST /api/audio/upload**
- Content-Type: multipart/form-data
- Body: audio file
- Response: audio file metadata

**GET /api/audio/{id}**
```json
{
  "id": "...",
  "filename": "recording.m4a",
  "status": "completed",
  "transcription": { "content": "...", "summary": "..." }
}
```

### 10.3 Transcription

**GET /api/transcriptions**
- Query params: `?user_id={id}&status={status}&limit=10&offset=0`

**GET /api/transcriptions/{id}**
- Returns full transcription with summary

---

## 11. Security Considerations

### 11.1 Authentication Security
- JWT tokens with short expiration (30 minutes)
- Refresh token rotation
- Secure password hashing (bcrypt)
- HTTPS-only in production

### 11.2 API Security
- Rate limiting per user
- Input validation and sanitization
- SQL injection prevention (ORM)
- CORS configuration

### 11.3 File Security
- File type validation
- Size limits (configurable)
- Virus scanning (optional integration)
- Secure file storage with encrypted paths

---

## 12. Monitoring & Logging

### 12.1 Logging Strategy
- Structured JSON logging
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Centralized log aggregation (ELK stack optional)

### 12.2 Metrics
- Request latency
- Transcription processing time
- API error rates
- GPU utilization

---

## 13. Future Enhancements

### 13.1 Planned Features
- Real-time transcription streaming
- Multi-language summary support
- Custom summary templates
- Integration with cloud storage (S3, Azure Blob)
- Batch job scheduling
- Advanced speaker identification

### 13.2 Scalability
- Horizontal scaling of processing workers
- Load balancing for API services
- Database read replicas
- CDN for static content

---

## 14. Development Guidelines

### 14.1 Code Style
- **Python**: PEP 8, Black formatter
- **TypeScript**: ESLint, Prettier
- **Commits**: Conventional Commits specification

### 14.2 Testing
- Unit tests for business logic
- Integration tests for API endpoints
- E2E tests for critical user flows

### 14.3 Documentation
- API documentation with FastAPI auto-generated docs
- Component documentation with Storybook
- Architecture decision records (ADRs)

---

## Appendix A: Quick Start

```bash
# Clone repository
git clone <repository-url>
cd ark_auto-summarizer

# Configure environment
cp summarizer/.env.sample summarizer/.env
# Edit .env with your Azure OpenAI credentials

# Launch development environment
./launch_summarizer.dev.sh

# Access services
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

## Appendix B: Troubleshooting

### Common Issues

**GPU not detected**:
- Verify NVIDIA driver installation: `nvidia-smi`
- Check Docker NVIDIA runtime configuration

**Azure OpenAI connection errors**:
- Verify API key and endpoint
- Check network connectivity from Docker container

**Database connection failures**:
- Ensure PostgreSQL container is running
- Verify connection string in environment variables
