from cashier import CashierSystem
from datetime import datetime, timedelta

def generate_test_items():
    cashier = CashierSystem()
    
    # Clear existing items (optional)
    cashier.db.items.delete_many({})
    
    # Get current date at start of day
    now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    test_items = [
        # Regular items
        {
            'name': 'Fresh Milk',
            'price': 3.99,
            'category': 'Dairy',
            'expiry_date': now + timedelta(days=7)
        },
        {
            'name': 'Whole Wheat Bread',
            'price': 2.49,
            'category': 'Bakery',
            'expiry_date': now + timedelta(days=5)
        },
        # About to expire items (1-2 days left)
        {
            'name': 'Yogurt',
            'price': 2.99,
            'category': 'Dairy',
            'expiry_date': now + timedelta(days=2)
        },
        {
            'name': 'Fresh Fish',
            'price': 8.99,
            'category': 'Seafood',
            'expiry_date': now + timedelta(days=1)
        },
        # Already expired items
        {
            'name': 'Old Cheese',
            'price': 5.99,
            'category': 'Dairy',
            'expiry_date': now - timedelta(days=1)
        },
        {
            'name': 'Expired Meat',
            'price': 7.99,
            'category': 'Meat',
            'expiry_date': now - timedelta(days=2)
        }
    ]
    
    print("\nGenerating Test Items:")
    print("-" * 70)
    print(f"{'Item Name':<20} {'Price':>8} {'Barcode':>15} {'Expiry Date':>20}")
    print("-" * 70)
    
    for item in test_items:
        added_item = cashier.add_new_item(
            name=item['name'],
            price=item['price'],
            category=item['category'],
            expiry_date=item['expiry_date']
        )
        if added_item:
            expiry_str = added_item['expiry_date'].strftime('%Y-%m-%d %H:%M:%S')
            print(f"{added_item['name']:<20} ${added_item['price']:>7.2f} {added_item['barcode']:>15} {expiry_str:>20}")
            print(f"Barcode image saved at: {cashier.get_item_barcode_path(added_item['barcode'])}")

if __name__ == "__main__":
    generate_test_items() 