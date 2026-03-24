#!/usr/bin/env python3
"""Simple CLI for O'Reilly Downloader."""

import json
import random
import string
import sys
from pathlib import Path
from typing import Any

import requests

from core.kernel import create_default_kernel
from plugins.downloader import DownloaderPlugin

sys.path.insert(0, str(Path(__file__).parent.parent))


class SimpleCLI:
    """Simple command-line interface."""

    def __init__(self):
        self.kernel = create_default_kernel()
        self.running = True

    def run(self):
        """Run the CLI main loop."""
        while self.running:
            self.show_main_menu()

    def _menu(
        self, title: str, options: list[tuple[str, str]], prompt: str = "choice"
    ) -> str:
        """Render a compact, automation-friendly menu."""
        print(f"\n{title}")
        for key, label in options:
            print(f"{key}) {label}")
        return input(f"{prompt}> ").strip().lower()

    def _pause(self):
        input("\nPress Enter to continue...")

    def show_main_menu(self):
        """Display main menu."""
        auth_status = self._check_auth()
        status_text = "valid" if auth_status else "invalid"
        print(f"\nO'Reilly Book Downloader (auth: {status_text})")

        choice = self._menu(
            "Main menu",
            [
                ("1", "Cookies"),
                ("2", "Search books"),
                ("3", "View downloads"),
                ("4", "Exit"),
            ],
        )

        if choice == "1":
            self._handle_cookies()
        elif choice == "2":
            self._handle_search()
        elif choice == "3":
            self._handle_downloads()
        elif choice == "4":
            self.running = False
            print("\nGoodbye")
        else:
            print("\nInvalid choice")

    def _check_auth(self) -> bool:
        """Check if cookies are valid."""
        auth = self.kernel.get("auth")
        return auth.validate_session()

    def _handle_cookies(self):
        """Handle cookie setup."""
        choice = self._menu(
            "Cookie setup",
            [
                ("1", "Auto-register (academic SSO)"),
                ("2", "Paste cookies"),
                ("3", "Test existing cookies"),
                ("4", "Back"),
            ],
        )

        if choice == "1":
            self._auto_register()
        elif choice == "2":
            self._paste_cookies()
        elif choice == "3":
            self._test_cookies()

    def _auto_register(self):
        """Register using academic SSO."""
        print("\nAttempting academic registration")

        email = self._generate_academic_email()
        print(f"Email: {email}")

        headers = {
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.7",
            "Cache-Control": "no-cache",
            "Content-Type": "application/json",
            "Origin": "https://www.oreilly.com",
            "Referer": "https://www.oreilly.com/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        }

        try:
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

            print(f"Status code: {response.status_code}")

            if response.status_code in (200, 201):
                cookies_dict = {c.name: c.value for c in session.cookies}

                if "orm-jwt" in cookies_dict:
                    cookies_file = Path("cookies.json")
                    cookies_file.write_text(json.dumps(cookies_dict, indent=2))
                    self.kernel.http.reload_cookies()
                    print("\nRegistration successful")
                    print("Saved cookies: cookies.json")
                    print(f"Email used: {email}")
                else:
                    print("\nRegistration response did not include orm-jwt cookie")
                    print(f"Response preview: {response.text[:200]}")
            else:
                print("\nRegistration failed")
                print(f"Status: {response.status_code}")
                print(f"Response preview: {response.text[:200]}")

        except Exception as e:
            print(f"\nError: {str(e)}")

        self._pause()

    def _generate_academic_email(self) -> str:
        """Generate random academic email."""
        domains = [
            "baylor.edu",
        ]
        username = "".join(random.choices(string.ascii_lowercase, k=10))
        domain = random.choice(domains)
        return f"{username}@{domain}"

    def _paste_cookies(self):
        """Manually paste cookies."""
        choice = self._menu(
            "Paste cookies",
            [
                ("1", "Paste JSON object"),
                ("2", "Paste document.cookie string"),
            ],
            prompt="format",
        )

        if choice == "2":
            self._paste_cookie_string()
        else:
            self._paste_cookie_json()

    def _paste_cookie_string(self):
        """Parse and save cookie string."""
        print("\nPaste cookie string from document.cookie")
        print("Example: orm-jwt=abc123; orm-rt=def456; _ga=xyz789")

        try:
            cookie_text = input("cookie> ").strip()
        except EOFError:
            print("Input cancelled")
            self._pause()
            return

        if not cookie_text:
            print("No cookies entered")
            self._pause()
            return

        try:
            cookies = {}
            for cookie_pair in cookie_text.split(";"):
                cookie_pair = cookie_pair.strip()
                if not cookie_pair:
                    continue
                if "=" in cookie_pair:
                    key, value = cookie_pair.split("=", 1)
                    cookies[key.strip()] = value.strip()

            if not cookies:
                raise ValueError("No valid cookie pairs found")

            cookies_file = Path("cookies.json")
            cookies_file.write_text(json.dumps(cookies, indent=2))
            self.kernel.http.reload_cookies()
            print("\nCookies saved")
            print(f"Cookie count: {len(cookies)}")
            print(f"Cookie keys: {', '.join(cookies.keys())}")
        except Exception as e:
            print(f"\nError parsing cookie string: {str(e)}")

        self._pause()

    def _paste_cookie_json(self):
        """Parse and save cookie JSON."""
        print("\nPaste cookie JSON object")
        print('Example: {"orm-jwt":"abc123","orm-rt":"def456"}')

        try:
            cookie_text = input("json> ").strip()
        except EOFError:
            print("Input cancelled")
            self._pause()
            return

        if not cookie_text:
            print("No cookies entered")
            self._pause()
            return

        try:
            cookies = json.loads(cookie_text)
            if not isinstance(cookies, dict):
                raise ValueError("Cookies must be a JSON object, not an array")

            cookies_file = Path("cookies.json")
            cookies_file.write_text(json.dumps(cookies, indent=2))
            self.kernel.http.reload_cookies()
            print("\nCookies saved")
            print(f"Cookie count: {len(cookies)}")
        except json.JSONDecodeError as e:
            print("\nInvalid JSON syntax")
            print(f"Line {e.lineno}, Column {e.colno}: {e.msg}")
            if e.pos >= 0:
                print(f"Position: {e.pos}")
                print(f"Context: {cookie_text[max(0, e.pos - 20) : e.pos + 20]}")
        except ValueError as e:
            print(f"\nInvalid format: {str(e)}")
        except Exception as e:
            print(f"\nError: {type(e).__name__}: {str(e)}")

        self._pause()

    def _test_cookies(self):
        """Test if cookies are valid."""
        cookies_file = Path("cookies.json")

        if not cookies_file.exists():
            print("\nNo cookies.json file found")
            self._pause()
            return

        auth = self.kernel.get("auth")
        is_valid = auth.validate_session()

        if is_valid:
            print("\nCookies are valid")
        else:
            print("\nCookies are invalid or expired")

        self._pause()

    def _handle_search(self):
        """Handle book search."""
        print("\nSearch books")

        if not self._check_auth():
            print("Cookies may be invalid. Some books may be inaccessible.")

        query = input("query> ").strip()

        if not query or len(query) < 2:
            print("Query too short")
            self._pause()
            return

        print("Searching...")

        try:
            book = self.kernel.get("book")
            results = book.search(query)

            if not results:
                print("No results found")
                self._pause()
                return

            print(f"\nFound {len(results)} results")

            for i, r in enumerate(results[:10], 1):
                print(f"{i}) {r['title']}")
                print(f"   authors: {', '.join(r.get('authors', ['Unknown']))}")
                print(f"   id: {r['id']}")

            choice = input("book number (0 to back)> ").strip()

            if choice.isdigit() and 0 < int(choice) <= min(len(results), 10):
                book = results[int(choice) - 1]
                self._handle_book(book)
        except Exception as e:
            print(f"\nSearch error: {str(e)}")

        self._pause()

    def _handle_book(self, book: dict):
        """Handle book details and download."""
        print(f"\nBook: {book['title']}")
        print(f"authors: {', '.join(book.get('authors', []))}")
        print(f"id: {book['id']}")

        choice = self._menu(
            "Download format",
            [
                ("1", "EPUB"),
                ("2", "Markdown"),
                ("3", "PDF"),
                ("4", "All formats"),
                ("5", "Back"),
            ],
            prompt="format",
        )

        format_map = {
            "1": "epub",
            "2": "markdown",
            "3": "pdf",
            "4": "all",
        }

        if choice in format_map:
            self._download_book(book["id"], format_map[choice])

    def _download_book(self, book_id: str, format_type: str):
        """Download a book."""
        print("\nStarting download")

        def progress_callback(progress):
            print(f"{progress.status}: {progress.percentage}%")

        try:
            downloader = self.kernel.get("downloader")
            result = downloader.download(
                book_id=book_id,
                output_dir=Path("output"),
                formats=DownloaderPlugin.parse_formats(format_type),
                progress_callback=progress_callback,
            )

            print("\nDownload complete")
            print(f"Location: {result.output_dir}")

            if result.files:
                print("Files generated:")
                for fmt, path in result.files.items():
                    print(f"- {fmt}: {path}")

        except Exception as e:
            print(f"\nDownload failed: {str(e)}")

        self._pause()

    def _handle_downloads(self):
        """View downloaded books."""
        print("\nDownloaded books")

        output_dir = Path("output")

        if not output_dir.exists():
            print("No downloads folder found")
            self._pause()
            return

        downloads = [d for d in output_dir.iterdir() if d.is_dir()]

        if not downloads:
            print("No books downloaded yet")
        else:
            print(f"Found {len(downloads)} downloads")

            for d in downloads:
                size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
                size_mb = size / (1024 * 1024)
                print(f"- {d.name}")
                print(f"  size: {size_mb:.2f} MB")

        self._pause()


def main():
    """Run simple CLI."""
    cli = SimpleCLI()
    try:
        cli.run()
    except KeyboardInterrupt:
        print("\n\n  Goodbye!")


if __name__ == "__main__":
    main()
