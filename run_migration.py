"""
Migration script to add unified memory architecture fields to the messages table.
Connects directly to MySQL in Docker container on port 3307
"""
import sys
import os
from sqlalchemy import create_engine, text

def main():
    try:
        # Direct connection to MySQL container on port 3307
        engine = create_engine('mysql+pymysql://rai_user:rai_password@localhost:3307/rai_chat')
        connection = engine.connect()
        
        # Check if columns already exist
        existing_columns = []
        result = connection.execute(text("SHOW COLUMNS FROM messages"))
        for row in result:
            existing_columns.append(row[0])
        
        # Add memory_status column if it doesn't exist
        if 'memory_status' not in existing_columns:
            connection.execute(text('ALTER TABLE messages ADD COLUMN memory_status VARCHAR(20) DEFAULT "contextual"'))
            print("Added memory_status column")
        
        # Add last_accessed column if it doesn't exist
        if 'last_accessed' not in existing_columns:
            connection.execute(text('ALTER TABLE messages ADD COLUMN last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP'))
            print("Added last_accessed column")
        
        # Add importance_score column if it doesn't exist
        if 'importance_score' not in existing_columns:
            connection.execute(text('ALTER TABLE messages ADD COLUMN importance_score INTEGER DEFAULT 1'))
            print("Added importance_score column")
        
        # Check if indexes exist
        existing_indexes = []
        result = connection.execute(text("SHOW INDEX FROM messages"))
        for row in result:
            existing_indexes.append(row[2])  # Index name is in position 2
        
        # Create indexes for performance if they don't exist
        if 'ix_messages_memory_status' not in existing_indexes:
            connection.execute(text('CREATE INDEX ix_messages_memory_status ON messages (memory_status)'))
            print("Created memory_status index")
            
        if 'ix_messages_last_accessed' not in existing_indexes:
            connection.execute(text('CREATE INDEX ix_messages_last_accessed ON messages (last_accessed)'))
            print("Created last_accessed index")
        
        connection.commit()
        connection.close()
        print('Migration completed successfully')
    except Exception as e:
        print(f'Migration failed: {e}')

if __name__ == "__main__":
    main()
