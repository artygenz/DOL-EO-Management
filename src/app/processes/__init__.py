"""Process starters for background services (worker, beat, imap).

Each module exposes start_* and stop_* functions that return/accept
subprocess.Popen handles. Import these in api startup to manage lifecycle.
"""

from .celery_worker import start_celery_worker, stop_celery_worker
from .celery_beat import start_celery_beat, stop_celery_beat
from .imap_listener import start_imap_listener, stop_imap_listener

__all__ = [
    "start_celery_worker",
    "stop_celery_worker",
    "start_celery_beat",
    "stop_celery_beat",
    "start_imap_listener",
    "stop_imap_listener",
]


