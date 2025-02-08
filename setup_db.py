import pymongo
from pymongo.server_api import ServerApi
from datetime import datetime, timedelta

# Connect to MongoDB
connection_string = "mongodb+srv://majdsukkary472:Ny4Rtjg1bDtKzptn@cluster0.1x9tg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
try:
    client = pymongo.MongoClient(connection_string, server_api=ServerApi('1'))
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")
except Exception as e:
    print(f"Error connecting to MongoDB: {str(e)}")
    exit(1)

db = client.expiry_tracker

# Create and insert sample items
sample_items = [
    # Dairy Products
    {
        'name': 'Milk 1L',
        'barcode': '5901234123457',
        'price': 3.99,
        'expiry_date': datetime.now() + timedelta(days=7),
        'category': 'Dairy',
        'user_id': None,
        'purchase_date': None
    },
    {
        'name': 'Yogurt Pack',
        'barcode': '5901234123458',
        'price': 4.99,
        'expiry_date': datetime.now() + timedelta(days=14),
        'category': 'Dairy',
        'user_id': None,
        'purchase_date': None
    },
    
    # About to Expire (within 3 days)
    {
        'name': 'Fresh Bread',
        'barcode': '5901234123459',
        'price': 2.49,
        'expiry_date': datetime.now() + timedelta(days=2),
        'category': 'Bakery',
        'user_id': None,
        'purchase_date': None
    },
    {
        'name': 'Chicken Breast',
        'barcode': '5901234123460',
        'price': 8.99,
        'expiry_date': datetime.now() + timedelta(days=3),
        'category': 'Meat',
        'user_id': None,
        'purchase_date': None
    },
    
    # Already Expired
    {
        'name': 'Old Cheese',
        'barcode': '5901234123461',
        'price': 5.99,
        'expiry_date': datetime.now() - timedelta(days=1),
        'category': 'Dairy',
        'user_id': None,
        'purchase_date': None
    },
    {
        'name': 'Expired Eggs',
        'barcode': '5901234123462',
        'price': 3.49,
        'expiry_date': datetime.now() - timedelta(days=2),
        'category': 'Dairy',
        'user_id': None,
        'purchase_date': None
    },
    
    # Long Shelf Life
    {
        'name': 'Canned Soup',
        'barcode': '5901234123463',
        'price': 2.99,
        'expiry_date': datetime.now() + timedelta(days=365),
        'category': 'Canned',
        'user_id': None,
        'purchase_date': None
    },
    {
        'name': 'Pasta Pack',
        'barcode': '5901234123464',
        'price': 1.99,
        'expiry_date': datetime.now() + timedelta(days=180),
        'category': 'Dry Goods',
        'user_id': None,
        'purchase_date': None
    }
]

# Insert items
print("\nSetting up items database...")
try:
    # Drop existing items collection if it exists
    if 'items' in db.list_collection_names():
        db.items.drop()
    
    # Create new items collection
    db.create_collection('items')
    db.items.create_index('barcode', unique=True)
    result = db.items.insert_many(sample_items)
    print(f"Successfully inserted {len(result.inserted_ids)} items")
    
    # Print all items for testing
    print("\nAvailable items for testing:")
    print("=" * 50)
    for item in db.items.find():
        print(f"Name: {item['name']}")
        print(f"Barcode: {item['barcode']}")
        print(f"Price: ${item['price']:.2f}")
        print(f"Expires: {item['expiry_date'].strftime('%Y-%m-%d')}")
        print(f"Category: {item['category']}")
        print("-" * 30)
except Exception as e:
    print(f"Error inserting items: {str(e)}")

print("\nDatabase setup complete!") 