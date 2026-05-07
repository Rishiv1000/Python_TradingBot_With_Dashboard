"""
terminal_capture.py
Redirects stdout/stderr of a strategy process to a log file
so the dashboard terminal tab can display it.
"""
import os
import sys

# Logs directory — one level up from shared/
_LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))

_original_stdout = sys.stdout
_original_stderr = sys.stderr


class _Tee:
    """Write to both original stream and a log file simultaneously."""
    def __init__(self, original, log_path):
        self._original = original
        self._log_path = log_path

    def write(self, data):
        try:
            self._original.write(data)
            self._original.flush()
        except Exception:
            pass
        try:
            with open(self._log_path, "a", encoding="utf-8", errors="replace") as f:
                f.write(data)
        except Exception:
            pass

    def flush(self):
        try:
            self._original.flush()
        except Exception:
            pass

    def fileno(self):
        return self._original.fileno()


def start_strategy_capture(strategy_name: str):
    """Start capturing stdout/stderr to logs/{strategy_lower}_terminal.log"""
    os.makedirs(_LOGS_DIR, exist_ok=True)
    log_path = os.path.join(_LOGS_DIR, f"{strategy_name.lower()}_terminal.log")
    sys.stdout = _Tee(_original_stdout, log_path)
    sys.stderr = _Tee(_original_stderr, log_path)


def stop_strategy_capture(strategy_name: str):
    """Restore original stdout/stderr."""
    sys.stdout = _original_stdout
    sys.stderr = _original_stderr
