# LegalLens frontend

React, TypeScript, and Vite frontend connected to the standalone FastAPI backend.

## Run locally

Start the backend from the repository root in PowerShell:

```powershell
.\LegalLens\backend\run-backend.cmd
```

Then start the frontend from `LegalLens/frontend`:

```powershell
npm install
Copy-Item .env.example .env.local
npm run dev
```

The API base URL defaults to `http://127.0.0.1:8000`. Override it in `.env.local` with `VITE_API_BASE_URL` if the backend runs elsewhere. Vite uses `http://localhost:5173` by default, which is allowed by the backend's default CORS settings.

## Build and run the Docker image

From the repository root in PowerShell, build the static frontend image:

```powershell
docker build -f LegalLens/frontend/Dockerfile --build-arg VITE_API_BASE_URL=http://localhost:8000 -t legallens-frontend:local LegalLens/frontend
```

Start the container and open `http://localhost:5173`:

```powershell
docker run --rm -p 5173:80 legallens-frontend:local
```

The API URL is embedded in the frontend at build time. Use the backend address reachable by the user's browser for `VITE_API_BASE_URL`; when the backend publishes port 8000 on this same computer, `http://localhost:8000` works.
## Connected functionality and limits

- Conversations and user turns load from and persist to the backend. Conversation history remains after a browser refresh.
- PDF and DOCX files are uploaded to backend storage and extracted locally during upload. Successful uploads should return with status `ready`; text based PDFs and DOCX files can be used by workflows. Scanned PDFs need OCR, which is not configured.
- Ask, Draft, and Summary workflows use the configured OpenAI model. Set `OPENAI_API_KEY` in `LegalLens/backend/.env` and restart the backend after changing it.
- Export is unavailable. The app does not display sample assistant answers or citations in connected mode.
- The backend uses one shared development identity and has no authentication. Keep this local and use synthetic or public material only; do not enter real client information.

If the UI continues to show `Awaiting processing` after a successful upload, check that the frontend is calling the current backend at `http://127.0.0.1:8000` and restart any older backend process. The current upload route extracts synchronously and returns `ready`; it does not rely on a separate worker.
