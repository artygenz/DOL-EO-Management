import os
import signal
import subprocess
import time
from typing import Optional


def start_celery_beat(env: Optional[dict] = None, log_dir: Optional[str] = "/app/logs") -> subprocess.Popen:
    """Start Celery beat as a background subprocess."""
    merged_env = dict(os.environ)
    if env:
        merged_env.update(env)

    try:
        if log_dir and not os.path.isdir(log_dir):
            os.makedirs(log_dir, exist_ok=True)
    except Exception:
        log_dir = "/app/logs"

    cmd = [
        "celery",
        "-A",
        "src.workflow.celery_app",
        "beat",
        "--loglevel=info",
    ]

    if log_dir:
        cmd.extend(["--logfile", os.path.join(log_dir, "celery_beat.log")])

    proc = subprocess.Popen(cmd, env=merged_env)
    return proc


def stop_celery_beat(proc: Optional[subprocess.Popen], timeout_seconds: int = 20) -> None:
    """Stop Celery beat process gracefully, then force if needed."""
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
