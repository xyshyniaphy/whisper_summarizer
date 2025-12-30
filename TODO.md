# Project TODO List

## 🚀 High Priority (Immediate)
- [ ] **Performance Optimization**
    - [ ] Increase `WHISPER_THREADS` in `.env` (Default is 1, causing slow transcription).
    - [ ] Evaluate `whisper-cli` parameters for better speed/accuracy balance.
- [x] **Summarization Feature**
    - [x] Implement Google Gemini integration in `GeminiClient`.
    - [x] Add "Summarize" button in Frontend.
    - [x] Display summary in `TranscriptionDetail` page.

## 🛠 Features & Improvements
- [ ] **UI/UX**
    - [x] Add "Download" button for transcription results (txt, srt).
    - [ ] Add "Edit" functionality for transcription text (fix typos).
    - [ ] Improve "Processing" status indication (Projected time or progress bar).
- [ ] **Data Management**
    - [ ] Implement auto-cleanup for old temporary files (wav).
    - [ ] Sort history by date (Asc/Desc toggle).

## 🔒 Security & Infrastructure
- [ ] **Authentication**
    - [ ] Secure API endpoints (Verify Supabase JWT token on every request).
    - [ ] Add Row Level Security (RLS) policies in Supabase DB (ensure users only see their own data).
- [ ] **Docker**
    - [ ] Optimize production build (`multi-stage build` for frontend).
    - [ ] Ensure non-root user execution in all containers.

## 🧪 Testing (Completed)
- [x] **Unit Tests**
    - [x] Add Backend tests (FastAPI + Pytest) - 73.37% coverage achieved.
    - [x] Add Frontend tests (React Testing Library + Vitest).
- [x] **E2E Tests**
    - [x] Automate the "Upload -> Transcribe -> Verify" flow with Playwright.
- [x] **Test Infrastructure**
    - [x] Docker-based test environment (`tests/run.sh`).
    - [x] Automated test execution for CI/CD readiness.

## 📊 Code Quality
- [ ] **Code Coverage**
    - [ ] Increase backend coverage to 80%+ (currently 73.37%).
    - [ ] Add frontend coverage tracking.
- [ ] **Linting & Formatting**
    - [ ] Setup ESLint for frontend.
    - [ ] Setup Black/Ruff for backend.
    - [ ] Add pre-commit hooks.
