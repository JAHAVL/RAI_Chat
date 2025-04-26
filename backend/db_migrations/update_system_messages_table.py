"""
Migration script to update the system_messages table structure
"""

import pymysql
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database connection parameters
DB_HOST = os.environ.get('MYSQL_HOST', 'mysql')
DB_PORT = int(os.environ.get('MYSQL_PORT', 3306))
DB_USER = os.environ.get('MYSQL_USER', 'rai_user')
DB_PASS = os.environ.get('MYSQL_PASSWORD', 'rai_password')
DB_NAME = os.environ.get('MYSQL_DATABASE', 'rai_chat')

def run_migration():
    """Execute the migration to update system_messages table"""
    logger.info("Starting system_messages table migration")
    
    try:
        # Connect to the database
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            db=DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        logger.info("Connected to database")
        
        with conn.cursor() as cursor:
            # First, back up existing data
            logger.info("Backing up existing system messages data")
            cursor.execute("CREATE TABLE system_messages_backup LIKE system_messages")
            cursor.execute("INSERT INTO system_messages_backup SELECT * FROM system_messages")
            
            # Add the user_id column
            logger.info("Adding user_id column")
            cursor.execute("ALTER TABLE system_messages ADD COLUMN user_id VARCHAR(36) AFTER timestamp")
            
            # Make the session_id column nullable
            logger.info("Making session_id column nullable")
            cursor.execute("ALTER TABLE system_messages MODIFY COLUMN session_id VARCHAR(36) NULL")
            
            # Rename timestamp to created_at
            logger.info("Renaming timestamp column to created_at")
            cursor.execute("ALTER TABLE system_messages CHANGE COLUMN timestamp created_at DATETIME")
            
            # Add foreign key constraint for user_id
            logger.info("Adding foreign key constraint for user_id")
            cursor.execute("""
                ALTER TABLE system_messages
                ADD CONSTRAINT fk_system_messages_user
                FOREIGN KEY (user_id) REFERENCES users(id)
            """)
            
            # Update indexes
            logger.info("Updating indexes")
            cursor.execute("CREATE INDEX idx_system_messages_user_id ON system_messages(user_id)")
            
            # Set a default user_id for existing messages (use the first user in the system)
            logger.info("Setting default user_id for existing records")
            cursor.execute("SELECT id FROM users LIMIT 1")
            result = cursor.fetchone()
            if result:
                default_user_id = result['id']
                cursor.execute(f"UPDATE system_messages SET user_id = '{default_user_id}'")
                cursor.execute("ALTER TABLE system_messages MODIFY COLUMN user_id VARCHAR(36) NOT NULL")
            else:
                logger.warning("No users found to set as default for system messages")
            
            # Commit the changes
            conn.commit()
            logger.info("Migration completed successfully")
            
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        # If something goes wrong, try to restore from backup
        try:
            if conn:
                with conn.cursor() as cursor:
                    logger.info("Attempting to restore from backup")
                    cursor.execute("DROP TABLE system_messages")
                    cursor.execute("RENAME TABLE system_messages_backup TO system_messages")
                    conn.commit()
                    logger.info("Restored from backup")
        except Exception as restore_error:
            logger.error(f"Error during backup restoration: {str(restore_error)}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    run_migration()
