#!/usr/bin/env python3
"""
Simple script to add hashed passwords to existing users in the database.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.session import SessionLocal
from src.db.user_operations import update_user_password
from src.models.user import User

# Default password for all users
DEFAULT_PASSWORD = "Lumen@2025"

def add_passwords_to_existing_users():
    """Add hashed passwords to all existing users"""
    db = SessionLocal()
    
    try:
        # Get all users without passwords
        users = db.query(User).filter(User.password_hash.is_(None)).all()
        
        if not users:
            print("No users found without passwords.")
            return
        
        print(f"Found {len(users)} users without passwords. Adding default password...")
        
        for user in users:
            success = update_user_password(db, str(user.id), DEFAULT_PASSWORD)
            if success:
                print(f"✅ Added password for user: {user.name} ({user.email})")
            else:
                print(f"❌ Failed to add password for user: {user.name} ({user.email})")
        
        print(f"\n✅ Successfully updated {len(users)} users with default password: '{DEFAULT_PASSWORD}'")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

def list_users_with_passwords():
    """List all users and their password status"""
    db = SessionLocal()
    
    try:
        users = db.query(User).all()
        
        print(f"\n📋 User Password Status ({len(users)} total users):")
        print("-" * 80)
        
        for user in users:
            has_password = user.password_hash is not None
            status = "✅ Has Password" if has_password else "❌ No Password"
            print(f"{user.name:<30} {user.email:<35} {status}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("🔐 User Password Management Script")
    print("=" * 50)
    
    # List current status
    list_users_with_passwords()
    
    # Add passwords automatically
    add_passwords_to_existing_users()
    
    print("\n📋 Final user status:")
    list_users_with_passwords()
