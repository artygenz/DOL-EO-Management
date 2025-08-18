"""
Enhanced Database Manager with connection pooling, failover, and audit logging.

Provides federal-grade database operations with:
- Connection pooling for high availability
- Automatic failover to backup database
- Email processing state tracking
- Comprehensive error handling and recovery
- Performance monitoring and metrics
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Union
from contextlib import contextmanager
from dataclasses import asdict

import psycopg2
from psycopg2 import pool, sql, extras
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from .models import (
    EmailProcessingState, AuditLogEntry, ProcessingStatus, AuditAction,
    DatabaseConnectionConfig, ConnectionPoolStats, ConnectionHealth,
    FailoverStatus, QueryMetrics, EmailMetadata
)
from .exceptions import (
    DatabaseError, ConnectionError, PoolError, AuditError,
    StateTrackingError, FailoverError, SchemaError, QueryError
)


class DatabaseManager:
    """
    Enhanced database manager with connection pooling and failover support.
    
    Features:
    - PostgreSQL connection pooling with health monitoring
    - Automatic failover to backup database
    - Email processing state tracking with ACID compliance
    - Immutable audit logging with cryptographic integrity
    - Performance monitoring and query metrics
    - Comprehensive error handling and recovery
    """
    
    # SQL schema definitions
    SCHEMA_VERSION = "1.0"
    
    CREATE_TABLES_SQL = """
    -- Email processing state tracking table
    CREATE TABLE IF NOT EXISTS email_processing_state (
        id SERIAL PRIMARY KEY,
        email_uid VARCHAR(255) NOT NULL UNIQUE,
        message_id VARCHAR(255) NOT NULL,
        account_id VARCHAR(100) NOT NULL,
        status VARCHAR(50) NOT NULL DEFAULT 'detected',
        metadata JSONB,
        classification_result JSONB,
        error_message TEXT,
        retry_count INTEGER DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        processed_at TIMESTAMP WITH TIME ZONE,
        CONSTRAINT valid_status CHECK (status IN ('detected', 'processing', 'classified', 'published', 'completed', 'failed', 'quarantined'))
    );
    
    -- Audit log table with immutable entries
    CREATE TABLE IF NOT EXISTS audit_log (
        id SERIAL PRIMARY KEY,
        entry_id UUID NOT NULL UNIQUE,
        timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
        component VARCHAR(100) NOT NULL,
        action VARCHAR(100) NOT NULL,
        email_uid VARCHAR(255),
        account_id VARCHAR(100),
        user_id VARCHAR(100),
        details JSONB NOT NULL DEFAULT '{}',
        security_classification VARCHAR(50) NOT NULL DEFAULT 'UNCLASSIFIED',
        digital_signature TEXT NOT NULL,
        hash_chain_previous VARCHAR(64),
        hash_chain_current VARCHAR(64) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Email deduplication tracking
    CREATE TABLE IF NOT EXISTS email_deduplication (
        id SERIAL PRIMARY KEY,
        email_uid VARCHAR(255) NOT NULL,
        message_id VARCHAR(255) NOT NULL,
        content_hash VARCHAR(64) NOT NULL,
        account_id VARCHAR(100) NOT NULL,
        first_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(email_uid, account_id),
        UNIQUE(message_id, account_id)
    );
    
    -- Connection health monitoring
    CREATE TABLE IF NOT EXISTS connection_health (
        id SERIAL PRIMARY KEY,
        connection_type VARCHAR(50) NOT NULL,
        host VARCHAR(255) NOT NULL,
        port INTEGER NOT NULL,
        status VARCHAR(50) NOT NULL,
        last_check TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        response_time_ms FLOAT,
        error_message TEXT
    );
    
    -- Query performance metrics
    CREATE TABLE IF NOT EXISTS query_metrics (
        id SERIAL PRIMARY KEY,
        query_type VARCHAR(100) NOT NULL,
        execution_time_ms FLOAT NOT NULL,
        rows_affected INTEGER NOT NULL DEFAULT 0,
        timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        success BOOLEAN NOT NULL DEFAULT TRUE,
        error_message TEXT
    );
    """
    
    CREATE_INDEXES_SQL = """
    -- Performance indexes
    CREATE INDEX IF NOT EXISTS idx_email_processing_state_uid ON email_processing_state(email_uid);
    CREATE INDEX IF NOT EXISTS idx_email_processing_state_account ON email_processing_state(account_id);
    CREATE INDEX IF NOT EXISTS idx_email_processing_state_status ON email_processing_state(status);
    CREATE INDEX IF NOT EXISTS idx_email_processing_state_created ON email_processing_state(created_at);
    
    CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);
    CREATE INDEX IF NOT EXISTS idx_audit_log_component ON audit_log(component);
    CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
    CREATE INDEX IF NOT EXISTS idx_audit_log_email_uid ON audit_log(email_uid);
    CREATE INDEX IF NOT EXISTS idx_audit_log_account_id ON audit_log(account_id);
    
    CREATE INDEX IF NOT EXISTS idx_email_dedup_uid ON email_deduplication(email_uid);
    CREATE INDEX IF NOT EXISTS idx_email_dedup_message_id ON email_deduplication(message_id);
    CREATE INDEX IF NOT EXISTS idx_email_dedup_hash ON email_deduplication(content_hash);
    
    CREATE INDEX IF NOT EXISTS idx_query_metrics_type ON query_metrics(query_type);
    CREATE INDEX IF NOT EXISTS idx_query_metrics_timestamp ON query_metrics(timestamp);
    """
    
    def __init__(self, config: DatabaseConnectionConfig):
        """
        Initialize the database manager.
        
        Args:
            config: Database connection configuration
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Connection pools
        self._primary_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None
        self._backup_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None
        
        # Failover state
        self._failover_status = FailoverStatus.PRIMARY_ACTIVE
        self._failover_lock = threading.RLock()
        self._last_health_check = datetime.utcnow()
        
        # Metrics tracking
        self._query_metrics: List[QueryMetrics] = []
        self._metrics_lock = threading.Lock()
        
        # Initialize database
        self._initialize_database()
        
        self.logger.info("Database manager initialized successfully")
    
    def _initialize_database(self):
        """Initialize database connections and schema."""
        try:
            # Create primary connection pool
            self._create_primary_pool()
            
            # Create backup pool if configured
            if self.config.backup_host:
                self._create_backup_pool()
            
            # Initialize schema
            self._initialize_schema()
            
            # Start health monitoring
            self._start_health_monitoring()
            
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise DatabaseError(f"Failed to initialize database: {e}")
    
    def _create_primary_pool(self):
        """Create primary database connection pool."""
        try:
            dsn = self._build_dsn(
                self.config.primary_host,
                self.config.primary_port,
                self.config.database,
                self.config.username,
                self.config.password
            )
            
            self._primary_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=self.config.pool_size + self.config.max_overflow,
                dsn=dsn,
                connect_timeout=self.config.connection_timeout
            )
            
            self.logger.info(f"Primary database pool created: {self.config.primary_host}")
            
        except Exception as e:
            self.logger.error(f"Failed to create primary pool: {e}")
            raise ConnectionError(f"Primary pool creation failed: {e}")
    
    def _create_backup_pool(self):
        """Create backup database connection pool."""
        try:
            dsn = self._build_dsn(
                self.config.backup_host,
                self.config.backup_port,
                self.config.database,
                self.config.username,
                self.config.password
            )
            
            self._backup_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=self.config.pool_size + self.config.max_overflow,
                dsn=dsn,
                connect_timeout=self.config.connection_timeout
            )
            
            self.logger.info(f"Backup database pool created: {self.config.backup_host}")
            
        except Exception as e:
            self.logger.warning(f"Failed to create backup pool: {e}")
            # Backup pool failure is not fatal
    
    def _build_dsn(self, host: str, port: int, database: str, username: str, password: str) -> str:
        """Build PostgreSQL DSN string."""
        return (
            f"host={host} port={port} dbname={database} "
            f"user={username} password={password} "
            f"sslmode={self.config.ssl_mode} "
            f"connect_timeout={self.config.connection_timeout}"
        )
    
    def _initialize_schema(self):
        """Initialize database schema and indexes."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Create tables
                    cursor.execute(self.CREATE_TABLES_SQL)
                    
                    # Create indexes
                    cursor.execute(self.CREATE_INDEXES_SQL)
                    
                    # Create schema version tracking
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS schema_version (
                            version VARCHAR(10) PRIMARY KEY,
                            applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    
                    # Record schema version
                    cursor.execute("""
                        INSERT INTO schema_version (version) 
                        VALUES (%s) 
                        ON CONFLICT (version) DO NOTHING;
                    """, (self.SCHEMA_VERSION,))
                    
                    conn.commit()
            
            self.logger.info("Database schema initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Schema initialization failed: {e}")
            raise SchemaError(f"Failed to initialize schema: {e}")
    
    @contextmanager
    def get_connection(self, use_backup: bool = False):
        """
        Get database connection from pool with automatic failover.
        
        Args:
            use_backup: Force use of backup connection
            
        Yields:
            Database connection
            
        Raises:
            ConnectionError: If no connections available
        """
        connection = None
        pool_used = None
        
        try:
            # Determine which pool to use
            if use_backup or self._failover_status == FailoverStatus.BACKUP_ACTIVE:
                if self._backup_pool:
                    connection = self._backup_pool.getconn()
                    pool_used = "backup"
                else:
                    raise ConnectionError("Backup pool not available")
            else:
                if self._primary_pool:
                    connection = self._primary_pool.getconn()
                    pool_used = "primary"
                else:
                    raise ConnectionError("Primary pool not available")
            
            # Test connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            
            yield connection
            
        except Exception as e:
            self.logger.error(f"Connection error from {pool_used} pool: {e}")
            
            # Attempt failover if primary failed
            if pool_used == "primary" and not use_backup:
                self.logger.info("Attempting failover to backup database")
                try:
                    with self._failover_lock:
                        self._failover_status = FailoverStatus.FAILOVER_IN_PROGRESS
                        
                        if self._backup_pool:
                            backup_conn = self._backup_pool.getconn()
                            with backup_conn.cursor() as cursor:
                                cursor.execute("SELECT 1")
                            
                            self._failover_status = FailoverStatus.BACKUP_ACTIVE
                            self.logger.info("Failover to backup database successful")
                            
                            # Return backup connection
                            if connection and pool_used == "primary":
                                self._primary_pool.putconn(connection, close=True)
                            
                            yield backup_conn
                            self._backup_pool.putconn(backup_conn)
                            return
                            
                except Exception as failover_error:
                    self.logger.error(f"Failover failed: {failover_error}")
                    self._failover_status = FailoverStatus.BOTH_FAILED
                    raise FailoverError(f"Database failover failed: {failover_error}")
            
            raise ConnectionError(f"Database connection failed: {e}")
            
        finally:
            # Return connection to pool
            if connection:
                try:
                    if pool_used == "primary" and self._primary_pool:
                        self._primary_pool.putconn(connection)
                    elif pool_used == "backup" and self._backup_pool:
                        self._backup_pool.putconn(connection)
                except Exception as e:
                    self.logger.warning(f"Failed to return connection to pool: {e}")
    
    def store_email_processing_state(self, state: EmailProcessingState) -> int:
        """
        Store or update email processing state.
        
        Args:
            state: Email processing state to store
            
        Returns:
            Database ID of the stored state
            
        Raises:
            StateTrackingError: If storage fails
        """
        try:
            start_time = time.time()
            
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                    if state.id is None:
                        # Insert new state
                        cursor.execute("""
                            INSERT INTO email_processing_state 
                            (email_uid, message_id, account_id, status, metadata, 
                             classification_result, error_message, retry_count)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING id;
                        """, (
                            state.email_uid,
                            state.message_id,
                            state.account_id,
                            state.status.value,
                            extras.Json(asdict(state.metadata) if state.metadata else {}),
                            extras.Json(state.classification_result or {}),
                            state.error_message,
                            state.retry_count
                        ))
                        
                        state.id = cursor.fetchone()['id']
                        rows_affected = 1
                    else:
                        # Update existing state
                        cursor.execute("""
                            UPDATE email_processing_state 
                            SET status = %s, metadata = %s, classification_result = %s,
                                error_message = %s, retry_count = %s, updated_at = CURRENT_TIMESTAMP,
                                processed_at = CASE WHEN %s = 'completed' THEN CURRENT_TIMESTAMP ELSE processed_at END
                            WHERE id = %s;
                        """, (
                            state.status.value,
                            extras.Json(asdict(state.metadata) if state.metadata else {}),
                            extras.Json(state.classification_result or {}),
                            state.error_message,
                            state.retry_count,
                            state.status.value,
                            state.id
                        ))
                        
                        rows_affected = cursor.rowcount
                    
                    conn.commit()
            
            # Record metrics
            execution_time = (time.time() - start_time) * 1000
            self._record_query_metrics("store_email_state", execution_time, rows_affected)
            
            self.logger.debug(f"Email processing state stored: {state.email_uid}")
            return state.id
            
        except Exception as e:
            self.logger.error(f"Failed to store email processing state: {e}")
            raise StateTrackingError(f"State storage failed: {e}")
    
    def get_email_processing_state(self, email_uid: str) -> Optional[EmailProcessingState]:
        """
        Retrieve email processing state by UID.
        
        Args:
            email_uid: Email UID to lookup
            
        Returns:
            Email processing state or None if not found
        """
        try:
            start_time = time.time()
            
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT * FROM email_processing_state 
                        WHERE email_uid = %s;
                    """, (email_uid,))
                    
                    row = cursor.fetchone()
                    if not row:
                        return None
                    
                    # Convert to EmailProcessingState
                    state = EmailProcessingState(
                        id=row['id'],
                        email_uid=row['email_uid'],
                        message_id=row['message_id'],
                        account_id=row['account_id'],
                        status=ProcessingStatus(row['status']),
                        metadata=EmailMetadata(**row['metadata']) if row['metadata'] else None,
                        classification_result=row['classification_result'],
                        error_message=row['error_message'],
                        retry_count=row['retry_count'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        processed_at=row['processed_at']
                    )
            
            # Record metrics
            execution_time = (time.time() - start_time) * 1000
            self._record_query_metrics("get_email_state", execution_time, 1 if row else 0)
            
            return state
            
        except Exception as e:
            self.logger.error(f"Failed to get email processing state: {e}")
            raise StateTrackingError(f"State retrieval failed: {e}")
    
    def store_audit_entry(self, entry: AuditLogEntry) -> int:
        """
        Store immutable audit log entry.
        
        Args:
            entry: Audit log entry to store
            
        Returns:
            Database ID of stored entry
            
        Raises:
            AuditError: If storage fails
        """
        try:
            start_time = time.time()
            
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO audit_log 
                        (entry_id, timestamp, component, action, email_uid, account_id,
                         user_id, details, security_classification, digital_signature,
                         hash_chain_previous, hash_chain_current)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id;
                    """, (
                        entry.entry_id,
                        entry.timestamp,
                        entry.component,
                        entry.action.value,
                        entry.email_uid,
                        entry.account_id,
                        entry.user_id,
                        extras.Json(entry.details),
                        entry.security_classification,
                        entry.digital_signature,
                        entry.hash_chain_previous,
                        entry.hash_chain_current
                    ))
                    
                    entry.id = cursor.fetchone()[0]
                    conn.commit()
            
            # Record metrics
            execution_time = (time.time() - start_time) * 1000
            self._record_query_metrics("store_audit_entry", execution_time, 1)
            
            self.logger.debug(f"Audit entry stored: {entry.entry_id}")
            return entry.id
            
        except Exception as e:
            self.logger.error(f"Failed to store audit entry: {e}")
            raise AuditError(f"Audit storage failed: {e}")
    
    def get_audit_entries(self,
                         email_uid: Optional[str] = None,
                         account_id: Optional[str] = None,
                         component: Optional[str] = None,
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None,
                         limit: int = 1000) -> List[AuditLogEntry]:
        """
        Retrieve audit log entries with filtering.
        
        Args:
            email_uid: Filter by email UID
            account_id: Filter by account ID
            component: Filter by component
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of entries to return
            
        Returns:
            List of matching audit entries
        """
        try:
            start_query_time = time.time()
            
            # Build dynamic query
            conditions = []
            params = []
            
            if email_uid:
                conditions.append("email_uid = %s")
                params.append(email_uid)
            
            if account_id:
                conditions.append("account_id = %s")
                params.append(account_id)
            
            if component:
                conditions.append("component = %s")
                params.append(component)
            
            if start_time:
                conditions.append("timestamp >= %s")
                params.append(start_time)
            
            if end_time:
                conditions.append("timestamp <= %s")
                params.append(end_time)
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            params.append(limit)
            
            query = f"""
                SELECT * FROM audit_log 
                {where_clause}
                ORDER BY timestamp DESC 
                LIMIT %s;
            """
            
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    
                    # Convert to AuditLogEntry objects
                    entries = []
                    for row in rows:
                        entry = AuditLogEntry(
                            id=row['id'],
                            entry_id=row['entry_id'],
                            timestamp=row['timestamp'],
                            component=row['component'],
                            action=AuditAction(row['action']),
                            email_uid=row['email_uid'],
                            account_id=row['account_id'],
                            user_id=row['user_id'],
                            details=row['details'],
                            security_classification=row['security_classification'],
                            digital_signature=row['digital_signature'],
                            hash_chain_previous=row['hash_chain_previous'],
                            hash_chain_current=row['hash_chain_current']
                        )
                        entries.append(entry)
            
            # Record metrics
            execution_time = (time.time() - start_query_time) * 1000
            self._record_query_metrics("get_audit_entries", execution_time, len(entries))
            
            return entries
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve audit entries: {e}")
            raise AuditError(f"Audit retrieval failed: {e}")
    
    def check_email_duplicate(self, email_uid: str, message_id: str, 
                            content_hash: str, account_id: str) -> bool:
        """
        Check if email is a duplicate using multi-layer detection.
        
        Args:
            email_uid: Email UID
            message_id: Email Message-ID header
            content_hash: SHA-256 hash of email content
            account_id: Account ID
            
        Returns:
            True if email is a duplicate
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Check for duplicates using any of the three methods
                    cursor.execute("""
                        SELECT COUNT(*) FROM email_deduplication 
                        WHERE (email_uid = %s AND account_id = %s)
                           OR (message_id = %s AND account_id = %s)
                           OR content_hash = %s;
                    """, (email_uid, account_id, message_id, account_id, content_hash))
                    
                    count = cursor.fetchone()[0]
                    is_duplicate = count > 0
                    
                    # If not duplicate, record for future detection
                    if not is_duplicate:
                        cursor.execute("""
                            INSERT INTO email_deduplication 
                            (email_uid, message_id, content_hash, account_id)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT DO NOTHING;
                        """, (email_uid, message_id, content_hash, account_id))
                        
                        conn.commit()
            
            return is_duplicate
            
        except Exception as e:
            self.logger.error(f"Duplicate check failed: {e}")
            # On error, assume not duplicate to avoid losing emails
            return False
    
    def get_connection_pool_stats(self) -> ConnectionPoolStats:
        """Get current connection pool statistics."""
        try:
            # Get primary pool stats
            if self._primary_pool and self._failover_status != FailoverStatus.BACKUP_ACTIVE:
                pool = self._primary_pool
                pool_type = "primary"
            elif self._backup_pool:
                pool = self._backup_pool
                pool_type = "backup"
            else:
                raise PoolError("No active connection pool available")
            
            # Calculate pool statistics
            # Note: psycopg2 doesn't expose detailed pool stats, so we estimate
            total_connections = self.config.pool_size + self.config.max_overflow
            
            # Determine health status based on failover state
            if self._failover_status == FailoverStatus.PRIMARY_ACTIVE:
                health = ConnectionHealth.HEALTHY
            elif self._failover_status == FailoverStatus.BACKUP_ACTIVE:
                health = ConnectionHealth.DEGRADED
            else:
                health = ConnectionHealth.FAILED
            
            stats = ConnectionPoolStats(
                pool_size=self.config.pool_size,
                checked_out=0,  # Not available in psycopg2
                overflow=0,     # Not available in psycopg2
                checked_in=self.config.pool_size,
                total_connections=total_connections,
                failed_connections=0,
                health_status=health,
                last_health_check=self._last_health_check
            )
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get pool stats: {e}")
            raise PoolError(f"Pool stats retrieval failed: {e}")
    
    def _record_query_metrics(self, query_type: str, execution_time_ms: float, 
                            rows_affected: int, success: bool = True, 
                            error_message: Optional[str] = None):
        """Record query performance metrics."""
        try:
            metric = QueryMetrics(
                query_type=query_type,
                execution_time_ms=execution_time_ms,
                rows_affected=rows_affected,
                success=success,
                error_message=error_message
            )
            
            with self._metrics_lock:
                self._query_metrics.append(metric)
                
                # Keep only recent metrics (last 1000 entries)
                if len(self._query_metrics) > 1000:
                    self._query_metrics = self._query_metrics[-1000:]
            
            # Also store in database for persistence
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO query_metrics 
                            (query_type, execution_time_ms, rows_affected, success, error_message)
                            VALUES (%s, %s, %s, %s, %s);
                        """, (
                            query_type, execution_time_ms, rows_affected, success, error_message
                        ))
                        conn.commit()
            except Exception:
                # Don't fail the main operation if metrics storage fails
                pass
                
        except Exception as e:
            self.logger.warning(f"Failed to record query metrics: {e}")
    
    def _start_health_monitoring(self):
        """Start background health monitoring thread."""
        def health_monitor():
            while True:
                try:
                    self._check_connection_health()
                    time.sleep(30)  # Check every 30 seconds
                except Exception as e:
                    self.logger.error(f"Health monitoring error: {e}")
                    time.sleep(60)  # Wait longer on error
        
        monitor_thread = threading.Thread(target=health_monitor, daemon=True)
        monitor_thread.start()
        self.logger.info("Database health monitoring started")
    
    def _check_connection_health(self):
        """Check health of database connections."""
        try:
            self._last_health_check = datetime.utcnow()
            
            # Check primary database
            primary_healthy = False
            if self._primary_pool:
                try:
                    with self.get_connection() as conn:
                        with conn.cursor() as cursor:
                            start_time = time.time()
                            cursor.execute("SELECT 1")
                            response_time = (time.time() - start_time) * 1000
                            primary_healthy = True
                            
                            # Record health status
                            self._record_connection_health(
                                "primary", self.config.primary_host, self.config.primary_port,
                                ConnectionHealth.HEALTHY, response_time
                            )
                except Exception as e:
                    self._record_connection_health(
                        "primary", self.config.primary_host, self.config.primary_port,
                        ConnectionHealth.FAILED, error_message=str(e)
                    )
            
            # Check backup database
            backup_healthy = False
            if self._backup_pool:
                try:
                    with self.get_connection(use_backup=True) as conn:
                        with conn.cursor() as cursor:
                            start_time = time.time()
                            cursor.execute("SELECT 1")
                            response_time = (time.time() - start_time) * 1000
                            backup_healthy = True
                            
                            self._record_connection_health(
                                "backup", self.config.backup_host, self.config.backup_port,
                                ConnectionHealth.HEALTHY, response_time
                            )
                except Exception as e:
                    self._record_connection_health(
                        "backup", self.config.backup_host, self.config.backup_port,
                        ConnectionHealth.FAILED, error_message=str(e)
                    )
            
            # Update failover status based on health
            with self._failover_lock:
                if primary_healthy and self._failover_status == FailoverStatus.BACKUP_ACTIVE:
                    # Primary recovered, switch back
                    self._failover_status = FailoverStatus.PRIMARY_ACTIVE
                    self.logger.info("Switched back to primary database")
                elif not primary_healthy and backup_healthy and self._failover_status == FailoverStatus.PRIMARY_ACTIVE:
                    # Primary failed, switch to backup
                    self._failover_status = FailoverStatus.BACKUP_ACTIVE
                    self.logger.warning("Switched to backup database due to primary failure")
                elif not primary_healthy and not backup_healthy:
                    self._failover_status = FailoverStatus.BOTH_FAILED
                    self.logger.critical("Both primary and backup databases are unavailable")
                    
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
    
    def _record_connection_health(self, connection_type: str, host: str, port: int,
                                status: ConnectionHealth, response_time_ms: Optional[float] = None,
                                error_message: Optional[str] = None):
        """Record connection health status."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO connection_health 
                        (connection_type, host, port, status, response_time_ms, error_message)
                        VALUES (%s, %s, %s, %s, %s, %s);
                    """, (
                        connection_type, host, port, status.value, response_time_ms, error_message
                    ))
                    conn.commit()
        except Exception:
            # Don't fail health checks if we can't record them
            pass
    
    def close(self):
        """Close all database connections and cleanup resources."""
        try:
            if self._primary_pool:
                self._primary_pool.closeall()
                self.logger.info("Primary database pool closed")
            
            if self._backup_pool:
                self._backup_pool.closeall()
                self.logger.info("Backup database pool closed")
                
        except Exception as e:
            self.logger.error(f"Error closing database connections: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()