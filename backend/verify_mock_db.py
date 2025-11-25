import asyncio
import os
from database import db, PRODUCTS

async def test_mock_db():
    print("Testing Mock DB...")
    
    # Ensure we are using Mock DB (or Real if configured, but we assume Mock for this test if env vars missing)
    # We can force it by checking type(db._ensure_client())
    
    client = db._ensure_client()
    print(f"Client type: {type(client)}")
    
    # 1. Test Set
    print("Testing Set...")
    ref = db.collection(PRODUCTS).document("test_doc")
    await ref.set({"name": "Test Product", "category": "Test"})
    
    # 2. Test Get
    print("Testing Get...")
    doc = await ref.get()
    if doc.exists and doc.to_dict()["name"] == "Test Product":
        print("Get Passed")
    else:
        print("Get Failed")
        
    # 3. Test Update
    print("Testing Update...")
    await ref.update({"price": 100})
    doc = await ref.get()
    if doc.to_dict().get("price") == 100:
        print("Update Passed")
    else:
        print("Update Failed")
        
    # 4. Test Stream with Filter (Async)
    print("Testing Async Stream with Filter...")
    # Add another doc
    await db.collection(PRODUCTS).document("test_doc_2").set({"name": "Test Product 2", "category": "Test"})
    await db.collection(PRODUCTS).document("other_doc").set({"name": "Other", "category": "Other"})
    
    query = db.collection(PRODUCTS).where("category", "==", "Test")
    count = 0
    async for d in query.stream():
        count += 1
        print(f"Found: {d.to_dict()['name']}")
        
    if count == 2:
        print("Async Stream Passed")
    else:
        print(f"Async Stream Failed. Expected 2, got {count}")

    # 5. Test Sync Stream (if supported by Mock)
    print("Testing Sync Stream...")
    count_sync = 0
    for d in query.stream():
        count_sync += 1
        
    if count_sync == 2:
        print("Sync Stream Passed")
    else:
        print(f"Sync Stream Failed. Expected 2, got {count_sync}")

    print("All DB Tests Finished")

if __name__ == "__main__":
    asyncio.run(test_mock_db())
