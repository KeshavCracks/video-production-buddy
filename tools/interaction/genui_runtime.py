"""Shared local runtime helpers for GenUI browser serving."""

from __future__ import annotations

import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

from lib.genui import is_wsl2


class LocalGenUIServerRuntime:
    """Browser/server helpers shared by localhost GenUI interaction tools."""

    def _try_open_browser(self, url: str) -> bool:
        import webbrowser

        if is_wsl2():
            try:
                windows_url = url.replace("127.0.0.1", "localhost", 1)
                completed = subprocess.run(
                    ["cmd.exe", "/c", "start", windows_url],
                    check=False,
                    capture_output=True,
                    timeout=5,
                )
                return completed.returncode == 0
            except (FileNotFoundError, subprocess.TimeoutExpired):
                return False
        return webbrowser.open(url)

    def _choose_port(self, host: str) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((host, 0))
            return int(sock.getsockname()[1])

    def _start_server(self, bundle: Any, host: str, port: int, submit_nonce: str) -> subprocess.Popen:
        cmd = [
            sys.executable,
            "-m",
            "lib.genui.server",
            "--config-path",
            str(bundle.config_path),
            "--response-path",
            str(bundle.response_path),
            "--view-spec-path",
            str(bundle.view_spec_path),
            f"--submit-nonce={submit_nonce}",
            "--host",
            host,
            "--port",
            str(port),
        ]
        return subprocess.Popen(
            cmd,
            cwd=Path(__file__).resolve().parent.parent.parent,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    def _wait_until_ready(
        self,
        process: subprocess.Popen,
        host: str,
        port: int,
        *,
        timeout_seconds: float = 3.0,
    ) -> None:
        deadline = time.monotonic() + timeout_seconds
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(
                    "GenUI browser server did not become ready "
                    f"(process exited with code {process.returncode})"
                )
            try:
                with urllib.request.urlopen(f"http://{host}:{port}/", timeout=0.25) as response:
                    if response.status == 200:
                        return
            except Exception as exc:
                if process.poll() is not None:
                    raise RuntimeError(
                        "GenUI browser server did not become ready "
                        f"(process exited with code {process.returncode})"
                    ) from exc
                last_error = exc
                try:
                    with socket.create_connection((host, port), timeout=0.25):
                        pass
                except OSError:
                    pass
                time.sleep(0.05)
            else:
                if process.poll() is None:
                    return
        raise RuntimeError(
            "GenUI browser server did not become ready "
            f"on {host}:{port}: {last_error}"
        )
