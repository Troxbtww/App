from cashier import CashierSystem
from datetime import datetime, timedelta

def check_expiry_status():
    cashier = CashierSystem()
    
    # Get expired and about-to-expire items using the new methods
    expired_items = cashier.get_expired_items()
    about_to_expire = cashier.get_about_to_expire_items()
    
    print("\nExpired Items:")
    print("-" * 60)
    if not expired_items:
        print("No expired items found")
    else:
        for item in expired_items:
            days_expired = (datetime.utcnow() - item['expiry_date']).days
            print(f"{item['name']:<20} ${item['price']:>7.2f} Expired {days_expired} days ago")
    
    print("\nItems About to Expire:")
    print("-" * 60)
    if not about_to_expire:
        print("No items about to expire")
    else:
        for item in about_to_expire:
            days_left = (item['expiry_date'] - datetime.utcnow()).days
            print(f"{item['name']:<20} ${item['price']:>7.2f} Expires in {days_left} days")

if __name__ == "__main__":
    check_expiry_status() 