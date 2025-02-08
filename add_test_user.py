from cashier import CashierSystem
from datetime import datetime

def add_test_user():
    cashier = CashierSystem()
    
    # Generate a simple test user barcode
    test_user = {
        'username': 'Test Customer',
        'barcode': '2990000000001',  # Simple test barcode
        'created_at': datetime.utcnow()
    }
    
    # Remove existing test user if any
    cashier.users.delete_many({'username': 'Test Customer'})
    
    # Add the test user
    result = cashier.users.insert_one(test_user)
    if result.inserted_id:
        print("\nTest User Created:")
        print("-" * 50)
        print(f"Username: {test_user['username']}")
        print(f"Barcode: {test_user['barcode']}")
        print("-" * 50)

if __name__ == "__main__":
    add_test_user() 