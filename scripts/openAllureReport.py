from __future__ import annotations
import argparse
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

def create_server(report_directory: Path, port: int = 0) -> ThreadingHTTPServer:
    report_directory = report_directory.resolve()
    if not (report_directory / "index.html").is_file():
        raise FileNotFoundError(
            f"No Allure index.html found in {report_directory}"
        )
    handler = partial(
        SimpleHTTPRequestHandler, directory=str(report_directory)
    )
    return ThreadingHTTPServer(("127.0.0.1", port), handler)

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Serve an extracted Allure HTML report over localhost."
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Allure report directory (defaults to this script's directory).",
    )
    args = parser.parse_args()
    server = create_server(args.report_dir)
    report_url = f"http://127.0.0.1:{server.server_port}/"
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Serving Allure report at {report_url}. Press Ctrl+C to stop.")
    try:
        webbrowser.open(report_url)
        thread.join()
    except KeyboardInterrupt:
        print("Stopped Allure report server.")
    finally:
        server.shutdown()
        server.server_close()

if __name__ == "__main__":
    main()
