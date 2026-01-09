# Production Deployment Quick Start

## ⚠️ Important: Server vs Runner

**This production deployment starts ONLY:**
- ✅ Frontend (nginx)
- ✅ API Server (FastAPI)
- ✅ PostgreSQL Database

**The Runner is NOT included** - it's a separate GPU worker that:
- Runs on a different machine with GPU
- Connects to this server via `SERVER_URL` and `RUNNER_API_KEY`
- Polls for transcription jobs

See [Production README](PRODUCTION_README.md) for complete architecture details.

## 🚀 Quick Start (5 minutes)

```bash
# 1. Setup environment
cp .env.prod .env
nano .env  # Edit required values

# 2. Build frontend
cd frontend && npm run build && cd ..

# 3. Start services
./start_prd.sh

# 4. Configure cloudflared tunnel to http://localhost:3080
```

## 📋 Required Environment Variables

Edit `.env` and set these:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-key
SUPABASE_SERVICE_ROLE_KEY=your-key
POSTGRES_PASSWORD=<strong-password>
RUNNER_API_KEY=<strong-api-key>
CORS_ORIGINS=https://your-domain.example.com
DISABLE_AUTH=false
```

## 🔧 Management Commands

```bash
./start_prd.sh    # Start services
./stop_prd.sh     # Stop services  
./status_prd.sh   # Check status
./logs_prd.sh     # View logs
```

## 🌐 Access

- **Local**: http://localhost:3080
- **Production**: Via Cloudflare Tunnel

## 📚 Full Documentation

See `PRODUCTION_README.md` for complete guide.

## ⚠️ Security Notes

- Only port 3080 exposed (HTTP for cloudflared)
- PostgreSQL internal only
- SSL/TLS by Cloudflare Tunnel
- Strong passwords required
- Authentication enforced (DISABLE_AUTH=false)
