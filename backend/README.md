# FINNOV Flask Backend

This is a lightweight Flask backend scaffold with endpoints to run your extractor and business logic.

## Quick start (Windows PowerShell)
- Create a virtual env and install deps:
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install -r backend/requirements.txt
  ```
- Run the server:
  ```powershell
  $env:FLASK_DEBUG="1"   # optional for dev
  python backend/run.py
  ```
  Server listens on http://127.0.0.1:5000

## Endpoints
- GET `/api/health` – health check
- POST `/api/extract` – runs your extractor
  - Accepts either multipart/form-data with `file` or JSON with `{ "text" | "url", "options"?: {} }`
- POST `/api/analyze` – runs your business logic
  - JSON: `{ "extracted": {}, "options"?: {} }`
- POST `/api/process` – extract then analyze in one call
  - Accepts same inputs as `/api/extract`; returns `{ extracted, result }` (and `intermediate` if requested)

## Plug in your code
Place your modules here and implement the expected functions:
- `backend/app/integrations/extractor.py` with:
  ```python
  def extract(input: dict) -> dict:
      """input may contain keys: text, file_path, url, options. Return extracted data dict."""
  ```
- `backend/app/integrations/logic.py` with:
  ```python
  def analyze(extracted: dict, options: dict | None = None) -> dict:
      """Return analysis result dict."""
  ```

The server will import these dynamically. Until provided, related endpoints return 501 Not Implemented.

## Config (env vars)
- `UPLOAD_FOLDER` – where uploaded files are stored (default: `./uploads` inside project root at runtime)
- `CORS_ORIGINS` – allowed origins (default: `*`)
- `PORT` – server port (default: 5000)

## Notes
- Max upload size is 20 MB by default (tweak in `app/config.py`).
- Ensure your extractor handles the input types you intend to support.
