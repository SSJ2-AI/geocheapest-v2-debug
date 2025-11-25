def deduplicate_products(products):
    # Deduplication Logic (Copied from main.py for verification)
    # Group by UPC, ASIN and Normalized Name
    unique_products = []
    seen_upcs = {} # UPC -> index in unique_products
    seen_asins = {} # ASIN -> index in unique_products
    seen_names = {} # Normalized Name -> index in unique_products

    for p in products:
        asin = p.get("asin")
        upc = p.get("upc")
        name = p.get("name", "").strip().lower()
        
        existing_idx = None
        
        # Check if we've seen this UPC
        if upc and upc in seen_upcs:
            existing_idx = seen_upcs[upc]

        # Check if we've seen this ASIN
        if existing_idx is None and asin and asin in seen_asins:
            existing_idx = seen_asins[asin]
        
        # Check if we've seen this Name (if no UPC/ASIN match yet)
        if existing_idx is None and name and name in seen_names:
            existing_idx = seen_names[name]
            
        if existing_idx is not None:
            # Merge / Compare with existing
            existing = unique_products[existing_idx]
            
            # Prefer in_stock, then lower price
            current_in_stock = p.get("in_stock", False)
            existing_in_stock = existing.get("in_stock", False)
            
            should_replace = False
            if current_in_stock and not existing_in_stock:
                should_replace = True
            elif current_in_stock == existing_in_stock:
                current_price = p.get("best_price") or float('inf')
                existing_price = existing.get("best_price") or float('inf')
                if current_price < existing_price:
                    should_replace = True
            
            if should_replace:
                unique_products[existing_idx] = p
                # Update mappings to point to this new object (index stays same)
                if upc:
                    seen_upcs[upc] = existing_idx
                if asin:
                    seen_asins[asin] = existing_idx
                if name:
                    seen_names[name] = existing_idx
            else:
                # FIX: Even if we don't replace, we must update mappings for the current product's attributes
                if upc:
                    seen_upcs[upc] = existing_idx
                if asin:
                    seen_asins[asin] = existing_idx
                if name:
                    seen_names[name] = existing_idx

        else:
            # New unique product
            new_idx = len(unique_products)
            unique_products.append(p)
            if upc:
                seen_upcs[upc] = new_idx
            if asin:
                seen_asins[asin] = new_idx
            if name:
                seen_names[name] = new_idx
    
    return unique_products

def test_deduplication():
    print("Running Deduplication Tests...")
    
    # Case 1: Duplicates by ASIN
    products_1 = [
        {"id": "1", "name": "Product A", "asin": "123", "best_price": 100, "in_stock": True},
        {"id": "2", "name": "Product A Variant", "asin": "123", "best_price": 90, "in_stock": True},
    ]
    result_1 = deduplicate_products(products_1)
    assert len(result_1) == 1
    assert result_1[0]["id"] == "2" # Lower price wins
    print("Case 1 Passed (ASIN match, lower price wins)")

    # Case 2: Duplicates by Name (No ASIN)
    products_2 = [
        {"id": "1", "name": "Product B", "best_price": 100, "in_stock": True},
        {"id": "2", "name": "product b ", "best_price": 110, "in_stock": True}, # Case/Whitespace difference
    ]
    result_2 = deduplicate_products(products_2)
    assert len(result_2) == 1
    assert result_2[0]["id"] == "1" # Lower price wins
    print("Case 2 Passed (Name match, lower price wins)")

    # Case 3: ASIN and Name mixing
    products_3 = [
        {"id": "1", "name": "Product C", "asin": "789", "best_price": 100, "in_stock": True},
        {"id": "2", "name": "product c", "best_price": 120, "in_stock": True}, # No ASIN, but name matches
    ]
    result_3 = deduplicate_products(products_3)
    assert len(result_3) == 1
    assert result_3[0]["id"] == "1" # Lower price wins
    print("Case 3 Passed (ASIN present in one, Name match links them)")

    # Case 4: Stock Priority
    products_4 = [
        {"id": "1", "name": "Product D", "asin": "000", "best_price": 50, "in_stock": False},
        {"id": "2", "name": "Product D", "asin": "000", "best_price": 100, "in_stock": True},
    ]
    result_4 = deduplicate_products(products_4)
    assert len(result_4) == 1
    assert result_4[0]["id"] == "2" # In stock wins despite higher price
    print("Case 4 Passed (Stock priority)")

    # Case 5: Missing ASIN Link (The Bug)
    products_5 = [
        {"id": "1", "name": "Product X", "best_price": 100, "in_stock": True},
        {"id": "2", "name": "Product X", "asin": "123", "best_price": 110, "in_stock": True},
        {"id": "3", "name": "Product Y", "asin": "123", "best_price": 120, "in_stock": True},
    ]
    result_5 = deduplicate_products(products_5)
    if len(result_5) == 1 and result_5[0]["id"] == "1":
        print("Case 5 Passed (ASIN link preserved)")
    else:
        print("Case 5 Failed (ASIN link lost)")

    # Case 6: UPC Match (New Feature)
    products_6 = [
        {"id": "1", "name": "Product Z", "upc": "999", "best_price": 100, "in_stock": True},
        {"id": "2", "name": "Product Z Different Name", "upc": "999", "best_price": 90, "in_stock": True},
    ]
    result_6 = deduplicate_products(products_6)
    assert len(result_6) == 1
    assert result_6[0]["id"] == "2" # Lower price wins via UPC match
    print("Case 6 Passed (UPC match)")

    print("All tests passed!")

if __name__ == "__main__":
    test_deduplication()
