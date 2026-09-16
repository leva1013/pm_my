# Backend guide

## Purpose

The backend is a FastAPI service that will own authentication, data persistence, and AI integration for the Project Management MVP.

## Current scaffold (Part 2)

- FastAPI app entrypoint: backend/app/main.py
- Routes currently available:
	- GET /
	- GET /api/health
- Test file:
	- backend/tests/test_app.py
- Python dependencies:
	- backend/requirements.txt

## Notes

- Current root route serves temporary hello-world HTML for scaffold verification.
- This will be replaced in Part 3 when backend serves built frontend assets.