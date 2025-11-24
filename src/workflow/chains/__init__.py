"""
Workflow Chains Package

This package contains orchestrated task chains that use the refactored services
from workflow/services/ to provide proper task sequencing, error handling,
and state management.
"""

from .eo_processing_chain import (
    process_eo_chain,
    process_eo_with_auto_approval,
    retry_failed_eo
)

from .pmo_response_chain import (
    process_pmo_response_chain,
    handle_bulk_approval,
    retry_pmo_response
)

from .daily_update_chain import (
    process_daily_update_chain,
    aggregate_daily_updates_chain,
    send_daily_reminders_chain,
    retry_daily_update
)

__all__ = [
    # EO Processing Chain
    "process_eo_chain",
    "process_eo_with_auto_approval", 
    "retry_failed_eo",
    
    # PMO Response Chain
    "process_pmo_response_chain",
    "handle_bulk_approval",
    "retry_pmo_response",
    
    # Daily Update Chain
    "process_daily_update_chain",
    "aggregate_daily_updates_chain",
    "send_daily_reminders_chain",
    "retry_daily_update"
]
