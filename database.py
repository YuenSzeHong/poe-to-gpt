import logging
from typing import Optional
import uuid
import psycopg2
from psycopg2 import pool
from urllib.parse import urlparse
from config import config

# Database Configuration
db_url = config.get("db_url", "")  # PostgreSQL database URL

if not db_url:
    raise ValueError("Please set the db_url in config.toml")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global connection pool
_pool = None

def init_db():
    """Initialize the database connection pool."""
    global _pool
    try:
        # Parse the database URL
        result = urlparse(db_url)
        
        # Create connection pool
        _pool = pool.SimpleConnectionPool(
            # Adjust based on your needs
            minconn=config.get('pool_minconn', 1),
            # Adjust based on your needs
            maxconn=config.get('pool_maxconn', 20),
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            sslmode='require' if result.query == 'sslmode=require' else 'disable'
        )
        
        # Test the connection
        with _pool.getconn() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT 1')
            _pool.putconn(conn)
            
        logger.info("Successfully initialized database connection pool")
        create_table()
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {e}")
        return False

def close_db():
    """Close the connection pool."""
    global _pool
    if _pool:
        _pool.closeall()
        _pool = None
        logger.info("Database connection pool closed")

def get_db():
    """Get a connection from the pool with proper error handling."""
    if not _pool:
        logger.error("Database pool not initialized")
        raise Exception("Database pool not initialized")

    try:
        conn = _pool.getconn()
        logger.debug("Acquired connection from pool")
        return conn
    except Exception as e:
        logger.error(f"Failed to get connection from pool: {e}")
        raise

def put_db(conn):
    """Return a connection to the pool with proper error handling."""
    if _pool and conn:
        try:
            _pool.putconn(conn)
            logger.debug("Released connection back to pool")
        except Exception as e:
            logger.error(f"Failed to return connection to pool: {e}")
            # Try to close connection if we can't return it
            try:
                conn.close()
                logger.debug(
                    "Closed connection that couldn't be returned to pool")
            except Exception as close_error:
                logger.error(f"Failed to close connection: {close_error}")

def db_transaction(func):
    """
    Decorator to ensure proper database connection handling.
    Each operation will:
    1. Get a fresh connection from the pool
    2. Execute the operation
    3. Commit/rollback the transaction
    4. Return the connection to the pool
    """
    def wrapper(*args, **kwargs):
        conn = None
        try:
            # Get fresh connection from pool
            conn = get_db()
            if not conn:
                raise Exception("Failed to get database connection")

            # Execute operation in a transaction
            with conn:  # Handles commit/rollback
                with conn.cursor() as cur:
                    return func(cur, *args, **kwargs)

        except Exception as e:
            logger.error(f"Database error in {func.__name__}: {e}")
            raise

        finally:
            # Always return connection to pool
            if conn:
                try:
                    put_db(conn)
                except Exception as e:
                    logger.error(
                        f"Error returning connection to pool in {func.__name__}: {e}")

    return wrapper

# Make these functions available for import
__all__ = ['init_db', 'get_db', 'close_db', 'get_user', 'create_user', 
           'is_admin', 'reset_api_key', 'get_all_users', 
           'disable_user', 'enable_user', 'update_linuxdo_token']

@db_transaction
def create_table(cur):
    """Create a table in the PostgreSQL database."""
    try:
        sql_create_users_table = """
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            api_key TEXT UNIQUE NOT NULL,
            username TEXT,
            linuxdo_token TEXT,
            enabled BOOLEAN DEFAULT TRUE,
            disable_reason TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP WITHOUT TIME ZONE,
            is_admin BOOLEAN DEFAULT FALSE
        );
        """
        cur.execute(sql_create_users_table)
        logger.info("Users table created successfully")
    except psycopg2.Error as e:
        logger.error(f"Error creating table: {e}")

@db_transaction
def get_user(cur, user_id: Optional[int] = None, api_key: Optional[str] = None):
    """Get a user from the database by user_id or api_key."""
    if user_id:
        cur.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
    elif api_key:
        cur.execute("SELECT * FROM users WHERE api_key=%s", (api_key,))
    else:
        return None
    return cur.fetchone()

@db_transaction
def create_user(cur, user_id, api_key: str, username: str, linuxdo_token: str):
    """Create a new user in the database."""
    sql = '''INSERT INTO users(user_id, api_key, username, linuxdo_token, created_at)
             VALUES(%s, %s, %s, %s, CURRENT_TIMESTAMP)'''
    cur.execute(sql, (user_id, api_key, username, linuxdo_token))
    return cur.lastrowid

@db_transaction
def reset_api_key(cur, user_id: int) -> Optional[str]:
    """Reset a user's API key."""
    try:
        new_api_key = f"sk-yn-{uuid.uuid4()}"
        cur.execute("UPDATE users SET api_key=%s WHERE user_id=%s", (new_api_key, int(user_id)),)
        return new_api_key
    except psycopg2.Error as e:
        logger.error(f"Error resetting API key: {e}")
        return None

@db_transaction
def get_all_users(cur):
    """Get all users from database."""
    try:
        cur.execute("SELECT * FROM users ORDER BY created_at DESC")
        return cur.fetchall()
    except psycopg2.Error as e:
        logger.error(f"Error getting users: {e}")
        return []

@db_transaction
def disable_user(cur, user_id: int, reason: str) -> bool:
    """Disable a user's access."""
    try:
        cur.execute("UPDATE users SET enabled=FALSE, disable_reason=%s WHERE user_id=%s", (reason, int(user_id)),)
        return True
    except psycopg2.Error as e:
        logger.error(f"Error disabling user: {e}")
        return False

@db_transaction
def enable_user(cur, user_id: int) -> bool:
    """Re-enable a user's access."""
    try:
        cur.execute("UPDATE users SET enabled=TRUE, disable_reason=NULL WHERE user_id=%s", (int(user_id),))
        return True
    except psycopg2.Error as e:
        logger.error(f"Error enabling user: {e}")
        return False

@db_transaction
def is_admin(cur, api_key: str) -> bool:
    """Check if a user is an admin."""
    try:
        cur.execute("SELECT is_admin FROM users WHERE api_key=%s", (api_key,))
        user = cur.fetchone()
        if user:
            # Return the boolean value directly from the database
            return bool(user[0])
        return False
    except psycopg2.Error as e:
        logger.error(f"Error checking admin status: {e}")
        return False

@db_transaction
def is_admin(cur, oauth_token: str) -> bool:
    """Check if a user is an admin by their OAuth token."""
    try:
        cur.execute("SELECT is_admin FROM users WHERE linuxdo_token = %s", (oauth_token,))
        user = cur.fetchone()
        if user:
            return bool(user[0])
        return False
    except psycopg2.Error as e:
        logger.error(f"Error checking admin status: {e}")
        return False

@db_transaction
def get_linuxdo_token(cur, api_key: str) -> Optional[str]:
    """Get the linuxdo_token for a user."""
    try:
        cur.execute("SELECT linuxdo_token FROM users WHERE api_key=%s", (api_key,))
        user = cur.fetchone()
        if user:
            return user[0]
        return None
    except psycopg2.Error as e:
        logger.error(f"Error getting linuxdo_token: {e}")
        return None

@db_transaction
def update_linuxdo_token(cur, user_id: int, linuxdo_token: str) -> bool:
    """Update a user's LinuxDO token."""
    try:
        cur.execute("UPDATE users SET linuxdo_token=%s WHERE user_id=%s", (linuxdo_token, int(user_id)))
        logger.info(f"User linuxdo_token updated successfully: {user_id}")
        return True
    except psycopg2.Error as e:
        logger.error(f"Error updating linuxdo_token: {e}")
        return False

@db_transaction
def update_last_used(cur, api_key: str) -> bool:
    """Update the last_used timestamp for a user"""
    try:
        cur.execute("""
            UPDATE users 
            SET last_used_at = CURRENT_TIMESTAMP 
            WHERE api_key = %s
        """, (api_key,))
        return True
    except Exception as e:
        logger.error(f"Error updating last_used: {e}")
        return False
