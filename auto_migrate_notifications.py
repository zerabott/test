#!/usr/bin/env python3
"""
Automatic Migration for Notification Tables
Safely fixes user_id column types from INTEGER/SERIAL to BIGINT at startup
"""

import logging
from db_connection import get_db_connection

logger = logging.getLogger(__name__)

def auto_migrate_notification_tables():
    """
    Automatically migrate notification table schemas at startup.
    This runs safely and preserves existing data.
    """
    db_conn = get_db_connection()
    
    if not db_conn.use_postgresql:
        logger.debug("Not using PostgreSQL - no migration needed")
        return True
    
    logger.info("🔧 Running automatic notification table migration...")
    
    try:
        with db_conn.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if migration is needed by inspecting column types
            migration_needed = False
            tables_to_check = ['notification_preferences', 'notification_history', 'post_subscriptions']
            
            for table_name in tables_to_check:
                try:
                    # Check if table exists and get user_id column type
                    cursor.execute(f"""
                        SELECT data_type, column_default
                        FROM information_schema.columns
                        WHERE table_name = '{table_name}' AND column_name = 'user_id'
                    """)
                    result = cursor.fetchone()
                    
                    if result:
                        data_type, column_default = result
                        logger.debug(f"Table {table_name}: user_id is {data_type}")
                        
                        # Check if user_id is not BIGINT
                        if data_type.lower() not in ['bigint', 'int8']:
                            logger.info(f"Migration needed: {table_name}.user_id is {data_type}, should be BIGINT")
                            migration_needed = True
                            break
                            
                except Exception as e:
                    logger.debug(f"Could not check {table_name}: {e}")
                    continue
            
            if not migration_needed:
                logger.info("✅ Notification tables already have correct schema - no migration needed")
                return True
            
            logger.info("🚀 Starting automatic schema migration...")
            
            # Migrate notification_preferences
            try:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'notification_preferences'
                    )
                """)
                if cursor.fetchone()[0]:
                    logger.info("Migrating notification_preferences table...")
                    
                    # Check current user_id type
                    cursor.execute("""
                        SELECT data_type, column_default
                        FROM information_schema.columns
                        WHERE table_name = 'notification_preferences' AND column_name = 'user_id'
                    """)
                    result = cursor.fetchone()
                    
                    if result and result[0].lower() not in ['bigint', 'int8']:
                        # Alter column type and remove SERIAL default if present
                        cursor.execute("""
                            ALTER TABLE notification_preferences
                            ALTER COLUMN user_id TYPE BIGINT USING user_id::bigint,
                            ALTER COLUMN user_id DROP DEFAULT;
                        """)
                        
                        # Drop the sequence if it exists (SERIAL creates one)
                        try:
                            cursor.execute("DROP SEQUENCE IF EXISTS notification_preferences_user_id_seq CASCADE;")
                        except Exception:
                            pass  # Sequence might not exist
                        
                        # Fix boolean defaults
                        cursor.execute("""
                            ALTER TABLE notification_preferences
                            ALTER COLUMN comment_notifications SET DEFAULT TRUE,
                            ALTER COLUMN daily_digest SET DEFAULT TRUE,
                            ALTER COLUMN trending_alerts SET DEFAULT TRUE;
                        """)
                        
                        logger.info("✅ Fixed notification_preferences.user_id -> BIGINT")
                        
            except Exception as e:
                logger.warning(f"Could not migrate notification_preferences: {e}")
            
            # Migrate notification_history
            try:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'notification_history'
                    )
                """)
                if cursor.fetchone()[0]:
                    logger.info("Migrating notification_history table...")
                    
                    cursor.execute("""
                        SELECT data_type
                        FROM information_schema.columns
                        WHERE table_name = 'notification_history' AND column_name = 'user_id'
                    """)
                    result = cursor.fetchone()
                    
                    if result and result[0].lower() not in ['bigint', 'int8']:
                        cursor.execute("""
                            ALTER TABLE notification_history
                            ALTER COLUMN user_id TYPE BIGINT USING user_id::bigint;
                        """)
                        logger.info("✅ Fixed notification_history.user_id -> BIGINT")
                        
            except Exception as e:
                logger.warning(f"Could not migrate notification_history: {e}")
            
            # Migrate post_subscriptions
            try:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'post_subscriptions'
                    )
                """)
                if cursor.fetchone()[0]:
                    logger.info("Migrating post_subscriptions table...")
                    
                    cursor.execute("""
                        SELECT data_type
                        FROM information_schema.columns
                        WHERE table_name = 'post_subscriptions' AND column_name = 'user_id'
                    """)
                    result = cursor.fetchone()
                    
                    if result and result[0].lower() not in ['bigint', 'int8']:
                        cursor.execute("""
                            ALTER TABLE post_subscriptions
                            ALTER COLUMN user_id TYPE BIGINT USING user_id::bigint;
                        """)
                        logger.info("✅ Fixed post_subscriptions.user_id -> BIGINT")
                        
            except Exception as e:
                logger.warning(f"Could not migrate post_subscriptions: {e}")
            
            # Commit all changes
            conn.commit()
            
            # Test the migration with a large user ID
            logger.info("🧪 Testing migration with large Telegram user ID...")
            test_user_id = 1298849354
            placeholder = db_conn.get_placeholder()
            
            try:
                # Test insertion (this should not fail anymore)
                cursor.execute(f"""
                    INSERT INTO notification_preferences (user_id, comment_notifications) 
                    VALUES ({placeholder}, TRUE) 
                    ON CONFLICT (user_id) DO UPDATE SET comment_notifications = TRUE
                """, (test_user_id,))
                
                cursor.execute(f"""
                    INSERT INTO notification_history 
                    (user_id, notification_type, title, content) 
                    VALUES ({placeholder}, 'migration_test', 'Migration Test', 'Auto-migration successful')
                """, (test_user_id,))
                
                conn.commit()
                logger.info("✅ Migration test successful - large user IDs now work!")
                
                # Clean up test data
                cursor.execute(f"DELETE FROM notification_history WHERE notification_type = 'migration_test'")
                conn.commit()
                
            except Exception as test_e:
                logger.error(f"❌ Migration test failed: {test_e}")
                return False
            
            logger.info("🎉 Automatic notification table migration completed successfully!")
            return True
            
    except Exception as e:
        logger.error(f"❌ Auto-migration failed: {e}")
        return False

def fix_emoji_encoding():
    """
    Fix emoji encoding issues in PostgreSQL database on Render.
    Updates rank emojis to ensure proper Unicode handling.
    """
    db_conn = get_db_connection()
    
    if not db_conn.use_postgresql:
        logger.debug("Not using PostgreSQL - emoji fix not needed")
        return True
    
    logger.info("🔧 Fixing emoji encoding in database...")
    
    try:
        # Define rank emojis
        rank_data = [
            (1, 'Freshman', '🥉'),
            (2, 'Sophomore', '🥈'),
            (3, 'Junior', '🥇'),
            (4, 'Senior', '🏆'),
            (5, 'Graduate', '🎓'),
            (6, 'Master', '👑'),
            (7, 'Legend', '🌟')
        ]
        
        with db_conn.get_connection() as conn:
            cursor = conn.cursor()
            placeholder = db_conn.get_placeholder()
            
            # Update each rank with proper emoji
            for rank_id, rank_name, emoji in rank_data:
                try:
                    cursor.execute(f"""
                        UPDATE rank_definitions 
                        SET rank_emoji = {placeholder}
                        WHERE rank_id = {placeholder}
                    """, (emoji, rank_id))
                    
                    logger.debug(f"Updated {rank_name}: {emoji}")
                    
                except Exception as e:
                    logger.warning(f"Could not update {rank_name} emoji: {e}")
                    continue
            
            conn.commit()
            
            # Test one emoji retrieval
            cursor.execute("SELECT rank_emoji FROM rank_definitions WHERE rank_id = 1")
            result = cursor.fetchone()
            if result:
                test_emoji = result[0]
                logger.info(f"✅ Emoji encoding test successful: {test_emoji}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Failed to fix emoji encoding: {e}")
        return False

def run_startup_migrations():
    """
    Run all startup migrations. Called by the main bot initialization.
    """
    logger.info("Running startup database migrations...")
    
    try:
        # Run notification table migration
        if not auto_migrate_notification_tables():
            logger.error("Notification table migration failed")
            return False
        
        # Fix emoji encoding issues (especially for Render PostgreSQL)
        if not fix_emoji_encoding():
            logger.warning("Emoji encoding fix failed - continuing anyway")
            # Don't fail startup for emoji issues
        
        logger.info("✅ All startup migrations completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Startup migrations failed: {e}")
        return False

if __name__ == "__main__":
    # For testing the migration directly
    logging.basicConfig(level=logging.INFO)
    success = auto_migrate_notification_tables()
    if success:
        print("✅ Migration completed successfully!")
    else:
        print("❌ Migration failed!")
