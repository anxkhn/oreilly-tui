# O'Reilly Ingest

We're in the AI era. You want to chat with your favorite technical books using Claude Code, Cursor, or any LLM tool. This gets you there.

Export any O'Reilly book to Markdown, PDF, EPUB, JSON, or plain text. Download by chapters so you don't burn through your context window.

## Disclaimer

For personal and educational use only. Please read the [O'Reilly Terms of Service](https://www.oreilly.com/terms/).

## Features

- **Export by chapters** - save tokens, focus on what matters
- **LLM-ready formats** - Markdown, JSON, plain text optimized for AI
- **Traditional formats** - PDF and EPUB 3
- **O'Reilly V2 API** - fast and reliable
- **Images & styles included** - complete book experience
- **Web UI** - search, preview, download
- **TUI** - Terminal User Interface for full CLI interaction

<img src="docs/main.png" alt="Main Page">

## Quick Start

### Docker (Recommended for most users)
```bash
git clone https://github.com/mosaibah/oreilly-downloader.git
cd oreilly-downloader
docker compose up -d
```
Then open http://localhost:8000

### Python with uv (Recommended for development)
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/mosaibah/oreilly-downloader.git
cd oreilly-downloader

# Install system dependencies (macOS only, for PDF support)
brew install pango pygobject

# Install dependencies and run
uv sync

# Run web UI
uv run main.py

# Run TUI (Terminal UI)
uv run main.py --tui
```
Then open http://localhost:8000

### Python with pip (Legacy)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## System Dependencies (for PDF generation)

### macOS
```bash
brew install pango pygobject  # Includes GLib, GObject, Cairo, required by WeasyPrint
```

### Ubuntu/Debian
```bash
sudo apt install libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0
```

### Docker
Already included in Dockerfile - no action needed.

> **Note**: PDF generation requires system dependencies. If you only need EPUB/Markdown/JSON formats, you can skip installing these.

## Authentication

### Academic Registration (SSO Loophole) - Automatic

The TUI provides automatic registration using an SSO academic registration loophole. No account needed.

**How it works:**
1. Generate a random academic email (e.g., user@baylor.edu)
2. Register via O'Reilly's academic API endpoint
3. Extract authentication cookies from the response
4. Save cookies automatically to `cookies.json`

**Usage in TUI:**
```bash
uv run main.py --tui
```
Then select "Register & Get Cookies" from the main menu.

> **Note**: This method exploits an SSO implementation flaw in the academic registration endpoint and may stop working if O'Reilly patches it. Use for educational purposes only.

### Manual Browser Cookies (Alternative)

If you already have an O'Reilly account or prefer manual setup:

1. Open [learning.oreilly.com](https://learning.oreilly.com) and log in
2. Open browser console (press F12 → Console)
3. Paste this command and press Enter:
   ```javascript
   JSON.stringify(document.cookie.split(";").map(c=>c.split("=")).reduce((r,[k,v])=>({...r,[k.trim()]:v?.trim()}),{}))
   ```
4. Copy the output and save it to `cookies.json` in JSON format

## Architecture

Plugin-based microkernel design:

| Layer | Components |
|-------|------------|
| **Kernel** | Plugin registry, shared HTTP client |
| **Core** | Auth, Book, Chapters, Assets, HtmlProcessor |
| **Output** | Epub, Markdown, Pdf, PlainText, JsonExport |
| **Utility** | Chunking, Token, Downloader |

### API

```
GET  /api/status       - auth check
GET  /api/search?q=    - find books
GET  /api/book/{id}    - metadata
POST /api/download     - start export
GET  /api/progress     - SSE stream
```

## Contributing

Found a bug or have an idea? PRs and issues are always welcome!


## License

MIT
