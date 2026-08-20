#!/usr/bin/env python3
"""Regression check for the live-preview startup signal."""

import io
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

import server


def main() -> None:
    events = []

    class ReadyServer:
        def serve_forever(self):
            events.append("served")

    def bind(*_args, **_kwargs):
        events.append("bound")
        return ReadyServer()

    with tempfile.TemporaryDirectory() as project, patch.object(
        server, "make_server", side_effect=bind
    ), redirect_stdout(io.StringIO()) as stdout:
        assert server.main([project, "--live", "--no-browser"]) == 0
    assert events == ["bound", "served"]
    assert "SVG Editor running at" in stdout.getvalue()

    with tempfile.TemporaryDirectory() as project, patch.object(
        server, "make_server", side_effect=SystemExit(1)
    ), redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()):
        assert server.main([project, "--live", "--no-browser"]) == 1
    assert "SVG Editor running at" not in stdout.getvalue()

    print("OK: live-preview startup signal")


if __name__ == "__main__":
    main()
