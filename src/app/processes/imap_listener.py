import os
import signal
import subprocess
import time
from typing import Optional, List, IO


_open_files: List[IO] = []


def start_imap_listener(env: Optional[dict] = None, log_dir: Optional[str] = "/app/logs") -> subprocess.Popen:
    """Start IMAP listener (src.email.service_manager) as a background subprocess."""
    merged_env = dict(os.environ)
    if env:
        merged_env.update(env)

    try:
        if log_dir and not os.path.isdir(log_dir):
            os.makedirs(log_dir, exist_ok=True)
    except Exception:
        log_dir = "/app/logs"

    cmd = [
        "python",
        "-m",
        "src.email.service_manager",
    ]

    # Redirect stdout/stderr to a dedicated logfile
    logfile_path = os.path.join(log_dir or "/app/logs", "imap_listener.log")
    try:
        fh = open(logfile_path, "a", buffering=1)
        _open_files.append(fh)
        proc = subprocess.Popen(cmd, env=merged_env, stdout=fh, stderr=fh)
    except Exception:
        # Fallback to default stdout/stderr
        proc = subprocess.Popen(cmd, env=merged_env)
    return proc


def stop_imap_listener(proc: Optional[subprocess.Popen], timeout_seconds: int = 20) -> None:
    """Stop IMAP listener process gracefully, then force if needed."""
    if not proc:
        return
    try:
        proc.terminate()
        proc.wait(timeout=timeout_seconds)
    except Exception:
        try:
            proc.send_signal(signal.SIGKILL)
        except Exception:
            pass
        finally:
            time.sleep(0.5)
    # Close any open log file handles
    try:
        while _open_files:
            fh = _open_files.pop()
            try:
                fh.flush()
                fh.close()
            except Exception:
                pass
    except Exception:
        pass


