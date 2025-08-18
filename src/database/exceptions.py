"""
Database-specific exceptions for the Email Agent system.
"""


class DatabaseError(Exception):
    """Base exception for database operations."""
    pass


class ConnectionError(DatabaseError):
    """Exception raised when database connection fails."""
    pass


class PoolError(DatabaseError):
    """Exception raised for connection pool issues."""
    pass


class AuditError(DatabaseError):
    """Exception raised for audit logging failures."""
    pass


class StateTrackingError(DatabaseError):
    """Exception raised for email state tracking issues."""
    pass


class FailoverError(DatabaseError):
    """Exception raised during database failover operations."""
    pass


class SchemaError(DatabaseError):
    """Exception raised for database schema issues."""
    pass


class IntegrityError(DatabaseError):
    """Exception raised for data integrity violations."""
    pass


class QueryError(DatabaseError):
    """Exception raised for query execution failures."""
    pass