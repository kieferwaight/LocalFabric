"""Execute a local test command and return a compact report."""

from __future__ import annotations

import subprocess


def run_local_tests(command: str = "pytest") -> str:
    """Run a local test command and trim output for downstream consumers."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return f"SUCCESS: All tests passed cleanly.\n\nOutput Trim:\n{result.stdout[-500:]}"

        error_log = result.stderr if result.stderr.strip() else result.stdout
        trimmed_error = error_log.splitlines()[-30:]
        return (
            f"FAILURE (Exit Code: {result.returncode})\n"
            "Trimmed Error Log for context window optimization:\n"
            "...\n" + "\n".join(trimmed_error)
        )
    except subprocess.TimeoutExpired:
        return "FAILURE: Test suite execution timed out after 30 seconds."
    except Exception as exc:
        return f"FAILURE: Could not execute test command. Error: {exc}"
