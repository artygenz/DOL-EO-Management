import os
import signal
import subprocess
import time
from typing import Optional


def start_celery_worker(env: Optional[dict] = None, log_dir: Optional[str] = "/app/logs") -> subprocess.Popen:
    """Start Celery worker as a background subprocess.

    Returns the Popen handle so the caller can manage lifecycle.
    """
    merged_env = dict(os.environ)
    if env:
        merged_env.update(env)

    # Ensure log directory exists
    try:
        if log_dir and not os.path.isdir(log_dir):
            os.makedirs(log_dir, exist_ok=True)
    except Exception:
        # Fallback to default without raising
        log_dir = "/app/logs"

    # Match current compose command
    cmd = [
        "celery",
        "-A",
        "src.workflow.celery_app",
        "worker",
        "--loglevel=info",
        "-Q",
        "ingest,ai,db,email,review",
    ]

    # Direct Celery logs to file as well
    if log_dir:
        cmd.extend(["--logfile", os.path.join(log_dir, "celery_worker.log")])

    proc = subprocess.Popen(cmd, env=merged_env)
    return proc


def stop_celery_worker(proc: Optional[subprocess.Popen], timeout_seconds: int = 20) -> None:
    """Stop Celery worker process gracefully, then force if needed."""
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
            # Give a brief moment after kill
            time.sleep(0.5)


