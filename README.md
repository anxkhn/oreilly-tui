# O'Reilly Downloader

O'Reilly Book Downloader - Export any O'Reilly book to Markdown, PDF, EPUB, JSON, or plain text for personal and educational use.

## Disclaimer

For personal and educational use only. Please read the [O'Reilly Terms of Service](https://www.oreilly.com/terms/).

## Features

- **Export by chapters** - save tokens, focus on what matters
- **LLM-ready formats** - Markdown, JSON, plain text optimized for AI
- **Traditional formats** - PDF and EPUB 3
- **O'Reilly V2 API** - fast and reliable
- **Images & styles included** - complete book experience
- **Web UI** - search, preview, download
- **Simple TUI** - Lightweight command-line interface (default)
- **Rich TUI** - Full-featured terminal UI with `--rich-tui`

<img src="docs/main.png" alt="Main Page">

## Quick Start

### Docker (Recommended for most users)
```bash
git clone https://github.com/anxkhn/oreilly-tui.git
cd oreilly-tui
docker compose up -d
```
Then open http://localhost:8000

### Python with uv (Recommended for development)
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/anxkhn/oreilly-tui.git
cd oreilly-tui

# Install system dependencies (macOS only, for PDF support)
brew install pango pygobject

# Install dependencies and run
uv sync

# Run Simple TUI (Terminal UI) - Default
uv run main.py

# Run Rich TUI (full-featured terminal UI)
uv run main.py --rich-tui

# Run web UI
uv run main.py --web
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

Both TUI modes and the web UI provide automatic registration using an SSO academic registration loophole. No account needed.

**How it works:**
1. Generate a random academic email (e.g., user@baylor.edu)
2. Register via O'Reilly's academic API endpoint
3. Extract authentication cookies from the response
4. Save cookies automatically to `cookies.json`

**Usage:**
```bash
# Simple TUI (default)
uv run main.py
# Then select "Set Cookies" -> "Auto-register"

# Rich TUI
uv run main.py --rich-tui
# Then select "Set Cookies" -> "Register & Get Cookies"

# Web UI
uv run main.py --web
# Click "Auto-Register" button
```

> **Note**: This method exploits an SSO implementation flaw in the academic registration endpoint and may not work reliably. O'Reilly has tightened validation. If auto-registration fails (returns 422 error), use manual browser cookies instead.

### Manual Browser Cookies (Alternative)

If you already have an O'Reilly account or prefer manual setup:

1. Open [learning.oreilly.com](https://learning.oreilly.com) and log in
2. Open browser console (press F12 → Console)
3. Paste this command and press Enter:
    ```javascript
    copy(document.cookie)
    ```
4. The cookie string is now in your clipboard
5. Run this in TUI or paste into a JSON converter online:
    ```
    orm-jwt=YOUR_JWT_VALUE; orm-rt=YOUR_RT_VALUE; ...
    ```
6. Or use this helper to convert cookie string to JSON in TUI's paste mode

**Alternative: Use browser DevTools directly**
1. Open learning.oreilly.com and log in
2. Press F12 → Application tab → Cookies → https://learning.oreilly.com
3. Copy the values for `orm-jwt` and `orm-rt` (and any other cookies you want)
4. Format as JSON: `{"orm-jwt":"value","orm-rt":"value"}`

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
