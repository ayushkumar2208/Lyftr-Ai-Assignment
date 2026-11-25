# Lyftr AI — Full-Stack LLM Chatbot

A production-style full-stack AI chatbot built with **React, FastAPI, LiteLLM, Gemini, and SQLite**.

The application demonstrates reliable LLM integration with **multi-key failover, LiteLLM response caching, multi-turn conversation history, token usage tracking, failure simulation, and Docker support**.

---

## Live URLs

### Frontend
**URL:** https://lyftr-ai-assignment-delta.vercel.app/

### Backend API
**URL:** https://lyftr-ai-assignment-ynen-6tht0c1be-ayush-kumar19.vercel.app/

### GitHub Repository
**URL:** https://github.com/ayushkumar2208/Lyftr-Ai-Assignment

---

## Features

### AI Chat Interface

The React frontend provides a clean chat interface where users can:

- Start a new conversation
- Send messages to the AI
- Continue multi-turn conversations
- Provide an optional system prompt
- View metadata for every AI response
- See readable error messages when the backend or provider is unavailable

Each page load creates a new session ID.

### Response Metadata

Every successful AI response displays:

- Resolution source
- Model name
- Latency
- Input token count
- Output token count

The backend additionally tracks:

- API key identifier
- Number of fallback attempts

Example:

```json
{
  "session_id": "s-example",
  "reply": "Hello! How can I help you today?",
  "metadata": {
    "resolution_source": "LIVE_INFERENCE",
    "model": "gemini/gemini-3.5-flash-lite",
    "latency_ms": 2356,
    "input_tokens": 14,
    "output_tokens": 9,
    "key_id": "key_1",
    "fallback_attempts": 0
  }
}
```

---

## System Architecture

```text
React / Vite Frontend
        |
        | POST /chat
        v
FastAPI Backend
        |
        +----------------------+
        |                      |
        v                      v
     SQLite                 LiteLLM
   Conversation                |
     History                   |
                               v
                       Gemini API Key Pool
                          |         |
                       key_1     key_2
```

The frontend communicates with the FastAPI backend through HTTP.

The backend is responsible for:

1. Loading previous conversation history from SQLite
2. Reconstructing the conversation
3. Sending the request through LiteLLM
4. Handling API-key failover
5. Detecting cached responses
6. Tracking token usage and latency
7. Persisting successful messages
8. Returning structured metadata to the frontend

---

## Tech Stack

### Frontend

- React
- Vite
- JavaScript
- CSS
- Nginx for containerized production serving

### Backend

- Python
- FastAPI
- LiteLLM
- SQLAlchemy
- aiosqlite
- Pydantic

### AI Provider

- Google Gemini
- Model: `gemini/gemini-3.5-flash-lite`

### Database

- SQLite

### Testing

- Pytest
- pytest-asyncio
- HTTPX

### DevOps

- Docker
- Docker Compose
- Makefile
- GitHub
- Vercel

---

# API Endpoints

The backend exposes three main endpoints.

## 1. Health Check

```http
GET /health
```

Example response:

```json
{
  "status": "ok",
  "keys_configured": 2,
  "cache_enabled": true
}
```

This verifies that:

- The backend is running
- SQLite is accessible
- At least two LLM API keys are configured
- LiteLLM caching is enabled

---

## 2. Chat

```http
POST /chat
```

Example request:

```json
{
  "session_id": "s-123",
  "message": "What is the capital of India?"
}
```

An optional system prompt can also be supplied:

```json
{
  "session_id": "s-123",
  "message": "Explain artificial intelligence.",
  "system_prompt": "Answer in simple English."
}
```

Example response:

```json
{
  "session_id": "s-123",
  "reply": "New Delhi is the capital of India.",
  "metadata": {
    "resolution_source": "LIVE_INFERENCE",
    "model": "gemini/gemini-3.5-flash-lite",
    "latency_ms": 1547,
    "input_tokens": 23,
    "output_tokens": 8,
    "key_id": "key_1",
    "fallback_attempts": 0
  }
}
```

---

## 3. Session History

```http
GET /sessions/{session_id}/messages
```

Example:

```http
GET /sessions/s-123/messages
```

This returns the messages stored for the requested session in chronological order.

If the session does not exist, the API returns:

```json
{
  "detail": "session not found"
}
```

with HTTP status `404`.

---

# Multi-Turn Conversation Memory

Conversation history is stored in SQLite.

For example:

```text
User:
My favorite programming language is Python.

Assistant:
Python is a great choice!

User:
What is my favorite programming language?

Assistant:
Your favorite programming language is Python.
```

The client only sends the newest user message.

The backend retrieves previous messages from SQLite and reconstructs the conversation before calling the LLM.

This keeps conversation state on the server instead of requiring the client to resend the entire conversation.

---

# LLM API-Key Failover

The backend uses a pool containing at least two Gemini API keys.

```text
Request
   |
   v
 key_1
   |
   +---- Success --------> Response
   |
   +---- 429 / 5xx / quota error
                    |
                    v
                  key_2
                    |
                    +---- Success ----> Response
                    |
                    +---- Failure ----> HTTP 503
```

Retryable provider failures include:

- HTTP `429`
- Rate limits
- Quota exhaustion
- HTTP `500`
- HTTP `502`
- HTTP `503`
- Temporary provider unavailability

The backend automatically tries the next configured API key.

---

# Deterministic Failure Simulation

The application supports the `X-Simulate-Failure` header so failover can be tested without intentionally exhausting API quotas.

## Simulate key_1 failure

Header:

```text
X-Simulate-Failure: key_1=429
```

Expected behavior:

```text
key_1 -> simulated 429
key_2 -> successful request
```

Successful response metadata includes:

```json
{
  "key_id": "key_2",
  "fallback_attempts": 1
}
```

---

## Simulate all providers failing

Header:

```text
X-Simulate-Failure: *=429
```

Expected response:

```json
{
  "detail": "all providers unavailable"
}
```

with:

```text
HTTP 503 Service Unavailable
```

Failed requests are not persisted to conversation history.

---

# LiteLLM Response Caching

LiteLLM's built-in cache is enabled.

The first identical request performs live inference:

```text
resolution_source = LIVE_INFERENCE
```

A matching cached request can return:

```text
resolution_source = LLM_CACHE
```

Cached responses do not expose an API key:

```json
{
  "resolution_source": "LLM_CACHE",
  "key_id": null,
  "fallback_attempts": 0
}
```

Caching reduces unnecessary provider calls and improves response latency.

---

# SQLite Persistence

Messages are stored in a SQLite `messages` table.

Each message contains:

- ID
- Session ID
- Role
- Content
- Metadata
- Creation timestamp

Assistant response metadata is serialized and stored alongside assistant messages.

During Docker execution, the database is configured under:

```text
/data/app.db
```

and `/data` is backed by a Docker named volume.

This allows conversation history to survive container restarts.

---

# Input Validation and Error Handling

The API validates incoming chat requests.

### Session ID

```text
1–128 characters
```

### Message

```text
1–4000 characters
```

Whitespace-only messages are rejected.

Invalid requests return:

```text
HTTP 422
```

Unknown sessions return:

```text
HTTP 404
```

If all configured LLM providers fail:

```text
HTTP 503
```

with:

```json
{
  "detail": "all providers unavailable"
}
```

The React frontend converts backend failures into readable error messages.

---

# Frontend Test IDs

The frontend includes stable `data-testid` attributes for automated evaluation.

```text
chat-input
send-button
assistant-message
meta-source
meta-model
meta-latency
meta-input-tokens
meta-output-tokens
system-prompt-input
```

---

# Project Structure

```text
lyftr-ai-assignment/
|
|-- backend/
|   |-- app/
|   |   |-- __init__.py
|   |   |-- main.py
|   |   |-- config.py
|   |   |-- database.py
|   |   |-- models.py
|   |   |-- schemas.py
|   |   `-- llm.py
|   |
|   |-- tests/
|   |   |-- __init__.py
|   |   `-- test_api.py
|   |
|   |-- requirements.txt
|   `-- Dockerfile
|
|-- frontend/
|   |-- src/
|   |   |-- components/
|   |   |   `-- ChatMessage.jsx
|   |   |
|   |   |-- App.jsx
|   |   |-- App.css
|   |   |-- index.css
|   |   `-- main.jsx
|   |
|   |-- public/
|   |-- package.json
|   |-- vite.config.js
|   |-- nginx.conf
|   `-- Dockerfile
|
|-- docker-compose.yml
|-- Makefile
|-- .env.example
|-- .gitignore
`-- README.md
```

---

# Environment Variables

Create a `.env` file in the project root.

Example:

```env
APP_ENV=development

LLM_MODEL=gemini/gemini-3.5-flash-lite

LLM_API_KEYS=your_first_api_key,your_second_api_key

DATABASE_URL=sqlite+aiosqlite:///./app.db

ALLOWED_ORIGINS=http://localhost:3000

ENABLE_FAILURE_SIMULATION=true
```

For the frontend:

```env
VITE_API_URL=http://127.0.0.1:8000
```

## Security

Real API keys must never be committed to GitHub.

The repository contains `.env.example` files containing placeholders only.

The real `.env` files are excluded through `.gitignore`.

---

# Running Locally Without Docker

## Backend

Create and activate a virtual environment.

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

Start FastAPI:

```bash
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend:

```text
http://127.0.0.1:8000
```

Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

Health endpoint:

```text
http://127.0.0.1:8000/health
```

---

## Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:3000
```

---

# Running With Docker

The entire stack can be started using:

```bash
make up
```

Equivalent Docker Compose command:

```bash
docker compose up --build
```

Services:

```text
Frontend: http://localhost:3000
Backend:  http://localhost:8000
```

Stop the application:

```bash
make down
```

or:

```bash
docker compose down
```

---

# Running Tests

Activate the Python virtual environment and run:

```bash
python -m pytest backend/tests -v
```

The backend test suite covers:

- Health endpoint
- Empty-message validation
- Whitespace-only message validation
- Missing session ID
- Maximum message length validation
- Unknown session handling

---

# Verified Behaviors

The following behaviors were tested during development:

### Health Check

```text
GET /health -> 200 OK
```

### Live LLM Inference

```text
resolution_source = LIVE_INFERENCE
key_id = key_1
fallback_attempts = 0
```

### Key Failover

Using:

```text
X-Simulate-Failure: key_1=429
```

produced:

```text
HTTP 200
key_id = key_2
fallback_attempts = 1
```

### Complete Provider Failure

Using:

```text
X-Simulate-Failure: *=429
```

produced:

```text
HTTP 503
```

with:

```json
{
  "detail": "all providers unavailable"
}
```

### Backend Tests

```text
6 passed
```

### Full-Stack Integration

The React frontend successfully communicates with FastAPI and displays:

- AI reply
- Resolution source
- Model
- Latency
- Input tokens
- Output tokens

---

# Design Decisions

## LiteLLM as the LLM Gateway

LiteLLM provides a consistent interface to the Gemini provider while allowing caching and provider-error handling to remain centralized in the backend.

## Server-Side Conversation State

SQLite stores conversation history by `session_id`.

This prevents the frontend from needing to resend the full conversation on every request.

## API-Key Pool

API keys are configured through the environment rather than hardcoded into source code.

Each key is represented externally only through identifiers such as:

```text
key_1
key_2
```

The actual key values are never returned by the API.

## Failover Strategy

Only retryable provider failures cause the application to move to the next API key.

This prevents invalid application requests from being unnecessarily retried.

## Successful-Request Persistence

Messages are persisted only after a successful LLM response.

Therefore, failed requests do not pollute conversation history.

## Frontend Configuration

The frontend reads its backend base URL from:

```text
VITE_API_URL
```

This allows the same frontend codebase to work locally and in deployment without hardcoding the backend address.

---

# Deployment

The frontend is deployed separately from the backend.

### Frontend

Vercel:

```text
ADD_YOUR_FRONTEND_URL
```

### Backend

Public FastAPI deployment:

```text
ADD_YOUR_BACKEND_URL
```

Deployment secrets are configured through the hosting provider's environment-variable settings and are never stored in the repository.

---

# Demo Verification Checklist

The application can be demonstrated in the following order:

1. Open the deployed frontend.
2. Send a normal message and show `LIVE_INFERENCE`.
3. Show model, latency, input tokens, and output tokens.
4. Continue the same session to demonstrate multi-turn conversation.
5. Send an identical first message from a new session to demonstrate caching.
6. Call `/chat` with `X-Simulate-Failure: key_1=429`.
7. Show `key_id = key_2` and `fallback_attempts = 1`.
8. Call `/chat` with `X-Simulate-Failure: *=429`.
9. Show the clean `503 all providers unavailable` response.
10. Show `/health`.
11. Show session history through `/sessions/{session_id}/messages`.

---

# Author

**Ayush Kumar**

Full-Stack AI Assignment — Lyftr AI
