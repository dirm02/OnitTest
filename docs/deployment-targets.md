# Deployment Targets

## Frontend: Netlify

The frontend is a Next.js app in `frontend/`. Netlify reads the root `netlify.toml` and builds from that directory.

Required Netlify environment variables:

```bash
NEXT_PUBLIC_API_URL=https://your-azure-backend.example.com
NEXT_PUBLIC_WS_URL=wss://your-azure-backend.example.com
```

For local development:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

## Backend: Azure VM

The backend is a FastAPI app in `backend/`. For the MVP, the simplest Azure VM deployment is Docker Compose with:

- FastAPI backend
- PostgreSQL
- optional reverse proxy for TLS

Required backend environment variables:

```bash
ENVIRONMENT=production
POSTGRES_HOST=...
POSTGRES_PORT=5432
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_DB=onit_test
SECRET_KEY=...
API_KEY=...
GOOGLE_API_KEY=...
AI_MODEL=gemini-2.5-flash
CORS_ORIGINS=["https://your-netlify-site.netlify.app"]
```

## Notes

- Keep secrets out of `netlify.toml` and source control.
- The MVP lead qualification endpoint can remain unauthenticated for the hiring-test demo.
- Before production use, protect the internal qualification workspace with staff authentication or a private network boundary.
- Authenticated dashboard/admin routes can remain available for future saved-lead review.
- Use HTTPS/WSS in production so browser WebSocket calls from Netlify are accepted.
