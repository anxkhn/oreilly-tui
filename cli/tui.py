"""Textual TUI for O'Reilly Downloader."""

import json
import random
import string
import subprocess
from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    ProgressBar,
    Static,
    TextArea,
)
from textual import on

from core.kernel import create_default_kernel
from plugins.downloader import DownloaderPlugin, DownloadProgress

import asyncio
import concurrent.futures


class MainScreen(Screen):
    """Main menu screen."""

    BINDINGS = [
        ("c", "app.push_screen_to_name('cookies')", "Cookies"),
        ("s", "app.push_screen_to_name('search')", "Search"),
        ("d", "app.push_screen_to_name('downloads')", "Downloads"),
        ("q", "app.quit", "Quit"),
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
            self.app.push_screen_to_name("cookies")
        elif event.button.id == "btn-search":
            self.app.push_screen_to_name("search")
        elif event.button.id == "btn-downloads":
            self.app.push_screen_to_name("downloads")
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
            Static("O'Reilly Academic Registration (SSO Loophole)"),
            Static(
                "Click below to auto-register using academic SSO loophole. "
                "This uses a random academic email domain to get free access.",
            ),
            Vertical(
                Button(
                    "Register & Get Cookies",
                    id="btn-register",
                    variant="primary",
                    disabled=self.registering,
                ),
                Button("Test Existing Cookies", id="btn-test"),
                Button("Paste Cookie JSON", id="btn-paste"),
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
        elif event.button.id == "btn-paste":
            self.app.push_screen_to_name("cookie_input")

    def _generate_random_email(self) -> str:
        """Generate a random academic email for registration."""
        domains = ["baylor.edu"]
        username = "".join(random.choices(string.ascii_lowercase, k=10))
        domain = random.choice(domains)
        return f"{username}@{domain}"

    def _register_academic(self) -> None:
        """Register using academic SSO loophole and extract cookies."""
        self.registering = True

        try:
            email = self._generate_random_email()
            self.app.notify(f"Registering with {email}...", severity="information")

            headers = {
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.7",
                "Cache-Control": "no-cache",
                "Content-Type": "application/json",
                "Origin": "https://www.oreilly.com",
            }

            import requests

            session = requests.Session()
            session.headers.update(headers)

            data = {
                "email": email,
                "signature": "",
                "timestamp": "",
                "referer": "",
                "ar": "true",
            }

            response = session.post(
                "https://www.oreilly.com/api/v1/registration/academic/",
                json=data,
                timeout=30,
            )

            if response.status_code != 200:
                self.app.notify(
                    f"Registration failed: HTTP {response.status_code}",
                    severity="error",
                )
                self.registering = False
                return

            cookies_dict = {}
            for cookie in session.cookies:
                cookies_dict[cookie.name] = cookie.value

            if not cookies_dict or "orm-jwt" not in cookies_dict:
                self.app.notify(
                    "Failed to extract cookies from registration response",
                    severity="error",
                )
                self.registering = False
                return

            cookies_file = Path("cookies.json")
            cookies_file.write_text(json.dumps(cookies_dict, indent=2))
            self.kernel.http.reload_cookies()
            self.app.notify(
                "Successfully registered and saved cookies!", severity="information"
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
            self.app.notify("Cookies are valid!", severity="information")
        else:
            self.app.notify("Cookies are invalid!", severity="error")


class CookieInputScreen(Screen):
    """Screen for manually pasting cookie JSON."""

    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def __init__(self, kernel):
        super().__init__()
        self.kernel = kernel

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("Paste Cookie JSON"),
            Static("Paste your browser cookie JSON below:"),
            TextArea(
                id="cookie-input", placeholder='{"orm-jwt": "...", "orm-rt": "..."}'
            ),
            Vertical(
                Button("Save", id="btn-save", variant="primary"),
                Button("Back", id="btn-back"),
            ),
            id="cookie-input-container",
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-save":
            self._save_cookies()

    def _save_cookies(self):
        input_widget = self.query_one("#cookie-input", TextArea)
        cookie_text = input_widget.text.strip()

        if not cookie_text:
            self.app.notify("Please paste cookie JSON", severity="warning")
            return

        try:
            cookies = json.loads(cookie_text)
            if not isinstance(cookies, dict):
                raise ValueError("Invalid format")

            cookies_file = Path("cookies.json")
            cookies_file.write_text(json.dumps(cookies, indent=2))
            self.kernel.http.reload_cookies()
            self.app.notify("Cookies saved successfully!", severity="information")
            self.app.pop_screen()
        except Exception as e:
            self.app.notify(f"Invalid JSON: {str(e)}", severity="error")


class SearchScreen(Screen):
    """Search books screen."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("s", "search_books", "Search"),
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
            if table.cursor_row is not None and table.cursor_row < len(
                self.search_results
            ):
                book_id = self.search_results[table.cursor_row][0]
                self.app.push_screen_to_name("book", book_id)

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

            table.clear()
            table.add_column("ID")
            table.add_column("Title")
            table.add_column("Authors")

            for result in self.search_results:
                table.add_row(*result)

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
            Static(f"Book ID: {self.book_id}"),
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
                    f"Title: {self.book_info.get('title', 'Unknown')}",
                ),
                Static(
                    f"Authors: {', '.join(self.book_info.get('authors', []))}",
                ),
                Static(f"Chapters: {len(self.chapters)}"),
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
            self.app.push_screen_to_name(
                "download", self.book_id, format_map[event.button.id]
            )


class DownloadScreen(Screen):
    """Download progress screen."""

    BINDINGS = [("c", "cancel_download", "Cancel")]

    def __init__(self, kernel, book_id, format_type):
        super().__init__()
        self.kernel = kernel
        self.book_id = book_id
        self.format_type = format_type
        self.progress = 0
        self.status = "Starting..."
        self.download_task = None
        self.is_complete = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static(f"Downloading: {self.book_id}"),
            Static(f"Format: {self.format_type}"),
            Static(f"Status: {self.status}", id="status-msg"),
            ProgressBar(total=100, show_eta=True, id="progress-bar"),
            Button("Cancel", id="btn-cancel", variant="error"),
            id="download-container",
        )
        yield Footer()

    async def on_mount(self) -> None:
        self._start_download()
        while not self.is_complete:
            await asyncio.sleep(0.1)

        if self.is_complete:
            self.query_one("#status-msg", Static).update("Download complete!")
            cancel_btn = self.query_one("#btn-cancel", Button)
            cancel_btn.label = "Done"
            cancel_btn.variant = "primary"
            cancel_btn.id = "btn-done"

    def _start_download(self):
        downloader = self.kernel.get("downloader")
        loop = asyncio.get_event_loop()

        def progress_callback(progress: DownloadProgress):
            self.progress = progress.percentage
            self.status = progress.status
            self.query_one("#status-msg", Static).update(f"Status: {progress.status}")
            self.query_one("#progress-bar", ProgressBar).update(
                progress=progress.percentage / 100
            )

        def run_download():
            try:
                downloader.download(
                    book_id=self.book_id,
                    output_dir=Path("output"),
                    formats=DownloaderPlugin.parse_formats(self.format_type),
                    progress_callback=progress_callback,
                )
                self.is_complete = True
            except Exception as e:
                self.status = f"Error: {str(e)}"
                self.query_one("#status-msg", Static).update(self.status)

        self.download_task = loop.run_in_executor(None, run_download)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel" and self.download_task:
            self.download_task.cancel()
            self.app.pop_screen()
        elif event.button.id == "btn-done":
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
            table = self.query_one("#downloads-table", DataTable)
            table.add_column("Message")
            table.add_row("No downloads found")
            return

        downloads = []
        for item in output_dir.iterdir():
            if item.is_dir():
                downloads.append((item.name, os.path.getsize(item)))

        table = self.query_one("#downloads-table", DataTable)
        table.clear()
        table.add_column("Name")
        table.add_column("Size")

        for name, size in downloads:
            size_mb = f"{size / (1024 * 1024):.2f} MB" if size > 0 else "0 MB"
            table.add_row(name, size_mb)


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
    Container {
        padding: 2;
    }
    """

    def __init__(self, kernel):
        super().__init__()
        self.kernel = kernel

    def on_mount(self) -> None:
        self.push_screen_to_name("main")

    def push_screen_to_name(self, screen_name: str, *args: Any):
        """Push a screen by name with optional arguments."""
        screen_classes = {
            "main": MainScreen,
            "cookies": CookiesScreen,
            "cookie_input": CookieInputScreen,
            "search": SearchScreen,
            "book": BookDetailsScreen,
            "download": DownloadScreen,
            "downloads": DownloadsScreen,
        }

        if screen_name in screen_classes:
            if args:
                screen = screen_classes[screen_name](self.kernel, *args)
            else:
                screen = screen_classes[screen_name](self.kernel)
            super().push_screen(screen)


def main():
    """Run TUI application."""
    kernel = create_default_kernel()
    app = OreillyTuiApp(kernel)
    app.run()


if __name__ == "__main__":
    main()
