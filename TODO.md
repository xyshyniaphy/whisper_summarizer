# Project TODO List

## 🚀 High Priority (Immediate)
- [ ] **Performance Optimization**
    - [ ] Increase `WHISPER_THREADS` in `.env` (Default is 1, causing slow transcription).
    - [ ] Evaluate `whisper-cli` parameters for better speed/accuracy balance.
- [ ] **Summarization Feature**
    - [ ] Implement GLM4.7 integration in `SummarizeService`.
    - [ ] Add "Summarize" button in Frontend.
    - [ ] Display summary in `TranscriptionDetail` page.

## 🛠 Features & Improvements
- [ ] **UI/UX**
    - [ ] Add "Download" button for transcription results (txt, srt).
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

## 🧪 Testing
- [x] **Unit Tests**
    - [x] Add Backend tests (FastAPI + Pytest).
    - [x] Add Frontend tests (React Testing Library).
- [x] **E2E Tests**
    - [x] Automate the "Upload -> Transcribe -> Verify" flow with Cypress or Playwright.
