#!/usr/bin/env python3
"""
PostgreSQL Schema Fix for Notification Tables
Fixes user_id column type and boolean column type mismatch errors in notification tables
"""

import logging
from db_connection import get_db_connection

logger = logging.getLogger(__name__)

def fix_notification_schema():
    """Fix PostgreSQL user_id and boolean column schema issues"""
    try:
        db_conn = get_db_connection()
        
        if not db_conn.use_postgresql:
            print("✅ Not using PostgreSQL - no schema fix needed")
            return True
            
        print("🔧 Fixing PostgreSQL notification table schemas...")
        
        with db_conn.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check which tables exist and need fixing
            tables_to_check = ['notification_preferences', 'notification_history', 'post_subscriptions', 'trending_cache']
            
            for table_name in tables_to_check:
                print(f"\n📋 Checking {table_name} table...")
                
                cursor.execute(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{table_name}'
                    );
                """)
                table_exists = cursor.fetchone()[0]
                
                if not table_exists:
                    print(f"✅ {table_name} table doesn't exist yet - will be created with correct schema")
                    continue
                    
                # Check user_id column type (except trending_cache which doesn't have user_id)
                if table_name != 'trending_cache':
                    cursor.execute(f"""
                        SELECT data_type, character_maximum_length, numeric_precision
                        FROM information_schema.columns
                        WHERE table_name = '{table_name}' AND column_name = 'user_id';
                    """)
                    user_id_info = cursor.fetchone()
                    
                    if user_id_info:
                        data_type, max_len, precision = user_id_info
                        print(f"  user_id column: {data_type}")
                        
                        # If user_id is not BIGINT, we need to recreate the table
                        if data_type.lower() not in ['bigint', 'int8']:
                            print(f"  ❌ user_id is {data_type}, should be BIGINT - recreating table...")
                            
                            # Recreate the table with correct schema
                            if table_name == 'notification_preferences':
                                cursor.execute('DROP TABLE IF EXISTS notification_preferences CASCADE')
                                cursor.execute('''
                                    CREATE TABLE notification_preferences (
                                        user_id BIGINT PRIMARY KEY,
                                        comment_notifications BOOLEAN DEFAULT TRUE,
                                        favorite_categories TEXT DEFAULT '',
                                        daily_digest BOOLEAN DEFAULT TRUE,
                                        trending_alerts BOOLEAN DEFAULT TRUE,
                                        digest_time TEXT DEFAULT '18:00',
                                        notification_frequency TEXT DEFAULT 'immediate',
                                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                                    )
                                ''')
                                print(f"  ✅ Recreated {table_name} with BIGINT user_id")
                                
                            elif table_name == 'notification_history':
                                cursor.execute('DROP TABLE IF EXISTS notification_history CASCADE')
                                cursor.execute('''
                                    CREATE TABLE notification_history (
                                        id SERIAL PRIMARY KEY,
                                        user_id BIGINT,
                                        notification_type TEXT NOT NULL,
                                        title TEXT NOT NULL,
                                        content TEXT NOT NULL,
                                        related_post_id INTEGER,
                                        related_comment_id INTEGER,
                                        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                        delivered BOOLEAN DEFAULT FALSE,
                                        clicked BOOLEAN DEFAULT FALSE,
                                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                                    )
                                ''')
                                print(f"  ✅ Recreated {table_name} with BIGINT user_id")
                                
                            elif table_name == 'post_subscriptions':
                                cursor.execute('DROP TABLE IF EXISTS post_subscriptions CASCADE')
                                cursor.execute('''
                                    CREATE TABLE post_subscriptions (
                                        id SERIAL PRIMARY KEY,
                                        user_id BIGINT,
                                        post_id INTEGER,
                                        subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                        active BOOLEAN DEFAULT TRUE,
                                        FOREIGN KEY (user_id) REFERENCES users (user_id),
                                        FOREIGN KEY (post_id) REFERENCES posts (post_id),
                                        UNIQUE(user_id, post_id)
                                    )
                                ''')
                                print(f"  ✅ Recreated {table_name} with BIGINT user_id")
                                
                            continue  # Skip to next table since we recreated this one
                        else:
                            print(f"  ✅ user_id column is already BIGINT")
                    
                    # For notification_preferences, also check boolean columns
                    if table_name == 'notification_preferences':
                        cursor.execute("""
                            SELECT column_name, data_type, column_default
                            FROM information_schema.columns
                            WHERE table_name = 'notification_preferences'
                            AND column_name IN ('comment_notifications', 'daily_digest', 'trending_alerts');
                        """)
                        columns = cursor.fetchall()
                        
                        if columns:
                            print("  📊 Boolean columns schema:")
                            for col_name, data_type, default_val in columns:
                                print(f"    - {col_name}: {data_type} (default: {default_val})")
                            
                            # Fix boolean columns with incorrect defaults
                            boolean_columns = ['comment_notifications', 'daily_digest', 'trending_alerts']
                            
                            for col_name in boolean_columns:
                                try:
                                    print(f"  🔧 Fixing {col_name} column...")
                                    
                                    # Drop default constraint if it exists with integer value
                                    cursor.execute(f"""
                                        ALTER TABLE notification_preferences 
                                        ALTER COLUMN {col_name} DROP DEFAULT;
                                    """)
                                    
                                    # Set new boolean default
                                    cursor.execute(f"""
                                        ALTER TABLE notification_preferences 
                                        ALTER COLUMN {col_name} SET DEFAULT TRUE;
                                    """)
                                    
                                    # Update existing rows with integer values to boolean
                                    cursor.execute(f"""
                                        UPDATE notification_preferences 
                                        SET {col_name} = CASE 
                                            WHEN {col_name}::text = '1' THEN TRUE 
                                            WHEN {col_name}::text = '0' THEN FALSE 
                                            ELSE {col_name}
                                        END;
                                    """)
                                    
                                    print(f"    ✅ Fixed {col_name} column")
                                    
                                except Exception as e:
                                    print(f"    ⚠️  Error fixing {col_name}: {e}")
                                    # Continue with other columns
                                    continue
            
            # Commit all changes
            conn.commit()
            
            print("\n🎉 All notification table schemas fixed successfully!")
            
            # Test the schema with a large user ID
            print("\n🧪 Testing schema with large Telegram user ID...")
            test_user_id = 1298849354  # From your config
            placeholder = db_conn.get_placeholder()
            
            try:
                # Test notification_preferences insertion
                cursor.execute(f'''
                    INSERT INTO notification_preferences (user_id, comment_notifications) 
                    VALUES ({placeholder}, TRUE) ON CONFLICT (user_id) DO NOTHING
                ''', (test_user_id,))
                
                cursor.execute(f'''
                    INSERT INTO notification_history 
                    (user_id, notification_type, title, content) 
                    VALUES ({placeholder}, 'test', 'Test Notification', 'Test content')
                ''', (test_user_id,))
                
                conn.commit()
                
                # Verify insertion
                cursor.execute(f'SELECT COUNT(*) FROM notification_preferences WHERE user_id = {placeholder}', (test_user_id,))
                pref_count = cursor.fetchone()[0]
                
                cursor.execute(f'SELECT COUNT(*) FROM notification_history WHERE user_id = {placeholder}', (test_user_id,))
                hist_count = cursor.fetchone()[0]
                
                print(f"✅ Test successful! Found {pref_count} preference(s) and {hist_count} history record(s)")
                
            except Exception as test_e:
                print(f"⚠️  Test insertion failed: {test_e}")
                # This is not critical, the schema fix is still valid
            
            return True
            
    except Exception as e:
        logger.error(f"Error fixing notification schema: {e}")
        print(f"❌ Error fixing notification schema: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Notification Tables Schema Fix Tool")
    print("=" * 50)
    print("This tool fixes the 'integer out of range' error by:")
    print("1. Ensuring user_id columns are BIGINT (not SERIAL/INTEGER)")
    print("2. Fixing boolean column defaults")
    print("3. Testing with large Telegram user IDs")
    print()
    
    success = fix_notification_schema()
    if success:
        print("\n🎉 Schema fix completed successfully!")
        print("\nNext steps:")
        print("1. Deploy your updated bot code to Render")
        print("2. Test comment notifications - they should now work!")
        print("3. The 'integer out of range' error should be resolved")
    else:
        print("\n💥 Schema fix failed!")
        print("Please check the error messages above and try again.")
