# Lyric Video Generator — Frontend

React/Vite editor UI. Pair with `../backend` (FastAPI) — this dev server
proxies `/api` to `http://localhost:8000` (see `vite.config.ts`).

## Setup & run

```bash
cd frontend
npm install
npm run dev
```

Open the printed URL (typically `http://localhost:5173`). Requires the
backend running on port 8000 first (`cd ../backend && uvicorn app.main:app
--reload --port 8000`).

## Layout

```
src/
  App.tsx                  upload + polling + panel wiring
  api.ts                    typed fetch wrappers for the backend API
  types.ts                  TS mirrors of the backend's pydantic schemas
  components/
    TranscriptEditor.tsx     draggable timeline + click-to-edit transcript
    BackgroundAndRender.tsx   preset/upload picker + preview render
    ExportPanel.tsx           resolution/codec + final export
```
