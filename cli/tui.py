"""Textual TUI for O'Reilly Downloader."""

import json
import random
import string
import subprocess
from pathlib import Path

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import (
    Button,
    Header,
    Footer,
    Static,
    Input,
    ListItem,
    ListView,
    ProgressBar,
    DataTable,
    Label,
)
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual import on
from core.kernel import create_default_kernel
from plugins.downloader import DownloaderPlugin
import asyncio


class MainScreen(Screen):
    """Main menu screen."""

    BINDINGS = [
        ("c", "push_screen('cookies')", "Cookies"),
        ("s", "push_screen('search')", "Search"),
        ("d", "push_screen('downloads')", "Downloads"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, kernel):
        super().__init__()
        self.kernel = kernel

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("O'Reilly Book Downloader - TUI"),
            Vertical(
                Button("Set Cookies", id="btn-cookies", variant="primary"),
                Button("Search Books", id="btn-search"),
                Button("View Downloads", id="btn-downloads"),
                Button("Exit", id="btn-exit", variant="error"),
            ),
            id="main-container",
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cookies":
            self.app.push_screen("cookies")
        elif event.button.id == "btn-search":
            self.app.push_screen("search")
        elif event.button.id == "btn-downloads":
            self.app.push_screen("downloads")
        elif event.button.id == "btn-exit":
            self.app.exit()


class CookiesScreen(Screen):
    """Cookie setup screen using SSO academic registration loophole."""

    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def __init__(self, kernel):
        super().__init__()
        self.kernel = kernel
        self.registering = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("O'Reilly Academic Registration (SSO Loophole)", classes="title"),
            Static(
                "Click below to auto-register using academic SSO loophole. "
                "This uses a random academic email domain to get free access.",
                classes="info",
            ),
            Vertical(
                Button(
                    "Register & Get Cookies",
                    id="btn-register",
                    variant="primary",
                    disabled=self.registering,
                ),
                Button("Test Existing Cookies", id="btn-test"),
                Button("Back", id="btn-back"),
            ),
            id="cookies-container",
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-register" and not self.registering:
            self._register_academic()
        elif event.button.id == "btn-test":
            self._test_cookies()

    def _generate_random_email(self) -> str:
        """Generate a random academic email for registration."""
        domains = [
            "baylor.edu",
            "tamu.edu",
            "stanford.edu",
            "mit.edu",
            "gatech.edu",
            "harvard.edu",
            "yale.edu",
            "princeton.edu",
            "columbia.edu",
            "duke.edu",
        ]
        username = "".join(random.choices(string.ascii_lowercase, k=10))
        domain = random.choice(domains)
        return f"{username}@{domain}"

    def _register_academic(self) -> None:
        """Register using academic SSO loophole and extract cookies."""
        self.registering = True

        try:
            email = self._generate_random_email()
            self.app.notify(f"Registering with {email}...", severity="information")

            cmd = [
                "curl",
                "https://www.oreilly.com/api/v1/registration/academic/",
                "-H",
                "accept: */*",
                "-H",
                "accept-language: en-US,en;q=0.7",
                "-H",
                "cache-control: no-cache",
                "-H",
                "content-type: application/json",
                "-H",
                "origin: https://www.oreilly.com",
                "-H",
                "pragma: no-cache",
                "-H",
                "priority: u=1, i",
                "-H",
                "referer: https://www.oreilly.com/",
                "-H",
                "sec-ch-ua: 'Not A-Brand';v='99', 'Brave';v='145', 'Chromium';v='145'",
                "-H",
                "sec-ch-ua-mobile: ?0",
                "-H",
                "sec-ch-ua-platform: 'macOS'",
                "-H",
                "sec-fetch-dest: empty",
                "-H",
                "sec-fetch-mode: cors",
                "-H",
                "sec-gpc: 1",
                "-H",
                "user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
                "--data-raw",
                json.dumps(
                    {
                        "email": email,
                        "signature": "",
                        "timestamp": "",
                        "referer": "",
                        "ar": "true",
                    }
                ),
                "-v",  # Include response headers
                "-s",  # Silent
                "-L",  # Follow redirects
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                self.app.notify(
                    f"Registration failed: {result.stderr}", severity="error"
                )
                self.registering = False
                return

            output = result.stdout + result.stderr
            cookies_dict = {}

            for line in output.split("\n"):
                if line.startswith("< set-cookie:"):
                    cookie_line = line[13:].strip()
                    if cookie_line.startswith("orm-jwt="):
                        cookies_dict["orm-jwt"] = cookie_line[8:]
                    elif cookie_line.startswith("orm-rt="):
                        cookies_dict["orm-rt"] = cookie_line[7:]
                    elif cookie_line.startswith("_vwo_uuid_v2="):
                        cookies_dict["_vwo_uuid_v2"] = cookie_line[15:].split(";")[0]

            if not cookies_dict or "orm-jwt" not in cookies_dict:
                self.app.notify(
                    "Failed to extract cookies from registration response",
                    severity="error",
                )
                self.registering = False
                return

            cookies_file = Path("cookies.json")
            cookies_file.write_text(json.dumps(cookies_dict, indent=2))
            self.app.notify(
                f"Successfully registered and saved cookies!", severity="success"
            )

        except Exception as e:
            self.app.notify(f"Registration error: {str(e)}", severity="error")
        finally:
            self.registering = False

    def _test_cookies(self):
        cookies_file = Path("cookies.json")
        if not cookies_file.exists():
            self.app.notify(
                "No cookies found. Please register first.", severity="warning"
            )
            return

        auth = self.kernel.get("auth")
        is_valid = auth.validate_session()
        if is_valid:
            self.app.notify("Cookies are valid!", severity="success")
        else:
            self.app.notify("Cookies are invalid!", severity="error")


class SearchScreen(Screen):
    """Search books screen."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("s", "search", "Search"),
        ("r", "reset_search", "Reset"),
    ]

    def __init__(self, kernel):
        super().__init__()
        self.kernel = kernel
        self.search_results = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Input(
                id="search-input",
                placeholder="Enter book title, ISBN, or author...",
            ),
            DataTable(id="results-table"),
            Vertical(
                Button("Select Book", id="btn-select", variant="primary"),
                Button("Search", id="btn-search"),
                Button("Back", id="btn-back"),
            ),
            id="search-container",
        )
        yield Footer()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._perform_search(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-search":
            search_input = self.query_one("#search-input", Input)
            self._perform_search(search_input.value)
        elif event.button.id == "btn-select":
            table = self.query_one("#results-table", DataTable)
            if table.cursor_row:
                book_id = self.search_results[table.cursor_row][0]
                self.app.push_screen("book", book_id)

    def _perform_search(self, query: str):
        if not query or len(query) < 2:
            self.app.notify("Enter at least 2 characters!", severity="warning")
            return

        book = self.kernel.get("book")
        try:
            results = book.search(query)
            self.search_results = [
                (r["id"], r["title"], ", ".join(r["authors"])) for r in results
            ]
            table = self.query_one("#results-table", DataTable)

            table.add_column("ID", key="id")
            table.add_column("Title", key="title")
            table.add_column("Authors", key="authors")

            table.clear()
            for result in self.search_results:
                table.add_row(id=result[0], title=result[1], authors=result[2])

            self.app.notify(f"Found {len(results)} books", severity="information")
        except Exception as e:
            self.app.notify(f"Search error: {str(e)}", severity="error")


class BookDetailsScreen(Screen):
    """Book details and download screen."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("d", "start_download", "Download"),
    ]

    def __init__(self, kernel, book_id):
        super().__init__()
        self.kernel = kernel
        self.book_id = book_id
        self.book_info = None
        self.chapters = []

    def on_mount(self) -> None:
        self._load_book_details()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static(f"Book ID: {self.book_id}", id="book-id"),
            Vertical(
                Static("Loading book details...", id="loading-msg"),
                id="book-details",
            ),
            id="details-container",
        )
        yield Footer()

    def _load_book_details(self):
        book = self.kernel.get("book")
        chapters_plugin = self.kernel.get("chapters")

        try:
            self.book_info = book.fetch(self.book_id)
            self.chapters = chapters_plugin.fetch_list(self.book_id)

            details = self.query_one("#book-details", Vertical)
            details.remove_children()

            details.mount(
                Static(
                    f"Title: {self.book_info.get('title', 'Unknown')}", classes="title"
                ),
                Static(
                    f"Authors: {', '.join(self.book_info.get('authors', []))}",
                    classes="authors",
                ),
                Static(f"Chapters: {len(self.chapters)}", classes="chapters"),
                Button("Download EPUB", id="btn-epub", variant="primary"),
                Button("Download Markdown", id="btn-markdown"),
                Button("Download PDF", id="btn-pdf"),
                Button("Download All", id="btn-all", variant="success"),
                Button("Back", id="btn-back"),
            )
        except Exception as e:
            self.query_one("#loading-msg", Static).update(f"Error: {str(e)}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        else:
            format_map = {
                "btn-epub": "epub",
                "btn-markdown": "markdown",
                "btn-pdf": "pdf",
                "btn-all": "all",
            }
            self.app.push_screen(
                "download", (self.book_id, format_map[event.button.id])
            )


class DownloadScreen(Screen):
    """Download progress screen."""

    BINDINGS = [("c", "cancel", "Cancel")]

    def __init__(self, kernel, book_id, format_type):
        super().__init__()
        self.kernel = kernel
        self.book_id = book_id
        self.format_type = format_type
        self.progress = 0
        self.status = "Starting..."

    def on_mount(self) -> None:
        self._start_download()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static(f"Downloading: {self.book_id}", classes="title"),
            Static(f"Format: {self.format_type}", classes="format"),
            Static(f"Status: {self.status}", id="status-msg", classes="status"),
            ProgressBar(total=100, show_eta=True, id="progress-bar"),
            Button("Cancel", id="btn-cancel", variant="error"),
            id="download-container",
        )
        yield Footer()

    def _start_download(self):
        downloader = self.kernel.get("downloader")
        from pathlib import Path

        def progress_callback(progress):
            self.progress = progress.percentage
            self.status = progress.status
            self.query_one("#status-msg", Static).update(f"Status: {progress.status}")
            self.query_one("#progress-bar", ProgressBar).update(
                progress=progress.percentage / 100
            )

        asyncio.create_task(
            downloader.download(
                book_id=self.book_id,
                output_dir=Path("output"),
                formats=DownloaderPlugin.parse_formats(self.format_type),
                progress_callback=progress_callback,
            )
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.app.pop_screen()


class DownloadsScreen(Screen):
    """View downloads screen."""

    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def __init__(self, kernel):
        super().__init__()
        self.kernel = kernel

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("Recent Downloads"),
            DataTable(id="downloads-table"),
            Button("Back", id="btn-back"),
            id="downloads-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        self._load_downloads()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()

    def _load_downloads(self):
        from pathlib import Path
        import os

        output_dir = Path("output")
        if not output_dir.exists():
            self.query_one("#downloads-table", DataTable).add_column(
                "No downloads found"
            )
            return

        downloads = []
        for item in output_dir.iterdir():
            if item.is_dir():
                downloads.append((item.name, os.path.getsize(item)))

        table = self.query_one("#downloads-table", DataTable)
        table.add_column("Name", key="name")
        table.add_column("Size", key="size")

        table.clear()
        for name, size in downloads:
            size_mb = f"{size / (1024 * 1024):.2f} MB" if size > 0 else "0 MB"
            table.add_row(name=name, size=size_mb)


class OreillyTuiApp(App):
    """Main TUI application."""

    CSS = """
    App {
        background: $surface;
    }
    #main-container {
        align: center middle;
    }
    Button {
        margin: 1;
    }
    .title {
        text-style: bold;
        text-align: center;
        margin: 2;
    }
    .format {
        text-style: italic;
        text-align: center;
    }
    .status {
        text-align: center;
        margin: 1;
    }
    """

    SCREENS = {
        "main": MainScreen,
        "cookies": CookiesScreen,
        "search": SearchScreen,
        "book": BookDetailsScreen,
        "download": DownloadScreen,
        "downloads": DownloadsScreen,
    }

    def __init__(self, kernel):
        super().__init__()
        self.kernel = kernel

    def on_mount(self) -> None:
        self.push_screen("main")

    def push_screen(self, screen_name: str, *args):
        if screen_name in self.SCREENS:
            if args:
                screen = self.SCREENS[screen_name](self.kernel, *args)
            else:
                screen = self.SCREENS[screen_name](self.kernel)
            self.push_screen(screen)


def main():
    """Run TUI application."""
    kernel = create_default_kernel()
    app = OreillyTuiApp(kernel)
    app.run()


if __name__ == "__main__":
    main()
