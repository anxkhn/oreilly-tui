#!/usr/bin/env python3
"""O'Reilly Downloader - Main Entry Point"""

import argparse
from web.server import run_server


def main():
    parser = argparse.ArgumentParser(description="O'Reilly Book Downloader")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument(
        "--web", action="store_true", help="Launch web server instead of TUI"
    )
    parser.add_argument(
        "--rich-tui",
        action="store_true",
        help="Use rich Textual TUI instead of simple TUI",
    )
    args = parser.parse_args()

    if args.web:
        print("=" * 50)
        print("  O'Reilly Downloader")
        print("=" * 50)
        print(f"\n  Open http://{args.host}:{args.port} in your browser\n")
        print("  Press Ctrl+C to stop\n")
        print("=" * 50)

        run_server(args.host, args.port)
    elif args.rich_tui:
        from cli.tui import main as tui_main

        tui_main()
    else:
        from cli.simple_tui import main as simple_tui_main

        simple_tui_main()


if __name__ == "__main__":
    main()
