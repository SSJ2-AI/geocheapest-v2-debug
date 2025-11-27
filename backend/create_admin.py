import asyncio
import os
from datetime import datetime
from database import db, USERS
from security import get_password_hash

import sys

async def create_admin():
    if len(sys.argv) > 2:
        email = sys.argv[1]
        password = sys.argv[2]
        print(f"DEBUG: Received email='{email}', password='{password}'")
    else:
        email = input("Enter Admin Email: ").strip()
        password = input("Enter Admin Password: ").strip()
    
    if not email or not password:
        print("Email and password are required.")
        return

    print(f"Creating admin user: {email}")
    
    # Check if exists
    users_ref = db.collection(USERS)
    query = users_ref.where("email", "==", email).limit(1)
    docs = query.stream()
    
    exists = False
    async for doc in docs:
        exists = True
        print("User already exists. Updating to admin...")
        await doc.reference.update({
            "is_superuser": True,
            "is_active": True,
            "hashed_password": get_password_hash(password),
            "updated_at": datetime.utcnow()
        })
        print("User updated successfully.")
        break
    
    if not exists:
        new_user_ref = users_ref.document()
        user_data = {
            "email": email,
            "hashed_password": get_password_hash(password),
            "full_name": "System Admin",
            "is_active": True,
            "is_superuser": True,
            "is_vendor": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        await new_user_ref.set(user_data)
        print(f"Admin user created with ID: {new_user_ref.id}")

if __name__ == "__main__":
    asyncio.run(create_admin())
