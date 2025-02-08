import pymongo
from pymongo.server_api import ServerApi
from datetime import datetime, timedelta
import sys
from kivy.uix.modalview import ModalView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from pyzbar.pyzbar import decode
import numpy as np
from kivy.app import App
from kivy.uix.label import Label
from kivy.core.window import Window
import cv2
from barcode import EAN13
from barcode.writer import ImageWriter
import random
import os
import logging
import argparse

# Disable MongoDB debug logs
logging.getLogger('mongodb').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

# Suppress ZBar warnings
os.environ['ZBAR_CFG_BINARY'] = '1'

class CashierApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cashier_system = CashierSystem()
        self.current_scanner = None
        self.transaction_view = None

    def build(self):
        layout = BoxLayout(orientation='vertical', padding=10)
        
        # Status label
        self.status_label = Label(
            text='Ready to scan customer barcode',
            size_hint_y=0.1
        )
        
        # Scan button
        scan_btn = Button(
            text='Start Scanning',
            size_hint_y=0.1,
            on_press=self.start_scanning
        )
        
        # Items list
        self.items_label = Label(
            text='No items scanned',
            size_hint_y=0.6  # Reduced to make room for buttons
        )
        
        # Total label
        self.total_label = Label(
            text='Total: $0.00',
            size_hint_y=0.1
        )
        
        # Buttons layout
        buttons_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=0.1,
            spacing=10,
            padding=[10, 0]
        )
        
        # Checkout button
        checkout_btn = Button(
            text='Checkout',
            on_press=self.checkout
        )
        
        # Clear button
        clear_btn = Button(
            text='Clear Cart',
            on_press=self.clear_cart
        )
        
        buttons_layout.add_widget(clear_btn)
        buttons_layout.add_widget(checkout_btn)
        
        layout.add_widget(self.status_label)
        layout.add_widget(scan_btn)
        layout.add_widget(self.items_label)
        layout.add_widget(self.total_label)
        layout.add_widget(buttons_layout)
        
        return layout

    def start_scanning(self, instance):
        if not self.cashier_system.current_user:
            # First scan is for user identification
            self.current_scanner = BarcodeScanner(
                on_scan_complete=self.on_user_scanned,
                scan_type='user'
            )
        else:
            # Subsequent scans are for items
            self.current_scanner = BarcodeScanner(
                on_scan_complete=self.on_item_scanned,
                scan_type='item'
            )
        self.current_scanner.open()

    def on_user_scanned(self, barcode):
        user = self.cashier_system.find_user(barcode)
        if user:
            self.cashier_system.current_user = user
            self.status_label.text = f'Customer: {user["username"]}\nScan items'
        else:
            self.status_label.text = 'Invalid user barcode. Try again.'

    def on_item_scanned(self, barcode):
        item = self.cashier_system.find_item(barcode)
        if item:
            self.cashier_system.add_item(item)
            self.update_display()
        else:
            self.status_label.text = 'Invalid item barcode. Try again.'

    def update_display(self):
        # Update items list
        items_text = 'Scanned Items:\n'
        for item in self.cashier_system.current_items:
            items_text += f"- {item['name']}: ${item['price']:.2f}\n"
        self.items_label.text = items_text

        # Update total
        total = sum(item['price'] for item in self.cashier_system.current_items)
        self.total_label.text = f'Total: ${total:.2f}'

    def checkout(self, instance):
        if not self.cashier_system.current_user:
            self.status_label.text = 'Please scan customer barcode first'
            return
        
        if not self.cashier_system.current_items:
            self.status_label.text = 'Cart is empty'
            return
        
        # Complete the transaction
        if self.cashier_system.finish_transaction():
            total = sum(item['price'] for item in self.cashier_system.current_items)
            self.status_label.text = f'Transaction complete! Total: ${total:.2f}'
            self.items_label.text = 'No items scanned'
            self.total_label.text = 'Total: $0.00'
        else:
            self.status_label.text = 'Error completing transaction'

    def clear_cart(self, instance):
        self.cashier_system.clear_transaction()
        self.status_label.text = 'Cart cleared. Ready to scan customer barcode'
        self.items_label.text = 'No items scanned'
        self.total_label.text = 'Total: $0.00'

class BarcodeScanner(ModalView):
    def __init__(self, on_scan_complete=None, scan_type='item', **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.8, 0.8)
        self.auto_dismiss = False
        self.on_scan_complete = on_scan_complete
        self.scan_type = scan_type
        self.capture = None

        layout = BoxLayout(orientation='vertical', padding=10)
        
        # Scanning label
        self.scan_label = Label(
            text=f'Initializing camera...',
            size_hint_y=0.1
        )
        
        # Camera preview
        self.image = Image(size_hint_y=0.8)
        
        # Cancel button
        cancel_btn = Button(
            text='Cancel',
            size_hint_y=0.1,
            on_press=self.dismiss
        )

        layout.add_widget(self.scan_label)
        layout.add_widget(self.image)
        layout.add_widget(cancel_btn)
        self.add_widget(layout)

        # Try to initialize camera
        Clock.schedule_once(self.initialize_camera, 0)

    def initialize_camera(self, dt):
        try:
            # Try to open the default camera (usually 0 or 1)
            self.capture = cv2.VideoCapture(0)
            if not self.capture.isOpened():
                self.capture = cv2.VideoCapture(1)  # Try another camera index
            
            if not self.capture.isOpened():
                self.scan_label.text = 'No camera available'
                return
            
            # Camera found, start updating
            self.scan_label.text = f'Scanning {self.scan_type}...'
            Clock.schedule_interval(self.update, 1.0/30.0)
            
        except Exception as e:
            print(f"Camera initialization error: {str(e)}")
            self.scan_label.text = 'Camera error: Please try again'

    def update(self, dt):
        if not self.capture:
            return

        ret, frame = self.capture.read()
        if not ret:
            return

        # Convert frame for display
        buf = cv2.flip(frame, 0)  # Flip vertically
        buf = cv2.cvtColor(buf, cv2.COLOR_BGR2RGB)
        
        # Create texture for Kivy Image
        texture = Texture.create(
            size=(frame.shape[1], frame.shape[0]), colorfmt='rgb'
        )
        texture.blit_buffer(buf.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
        self.image.texture = texture

        # Detect barcodes
        try:
            barcodes = decode(frame)
            for barcode in barcodes:
                barcode_data = barcode.data.decode('utf-8')
                print(f"Detected {self.scan_type} barcode: {barcode_data}")
                
                self.cleanup()
                if self.on_scan_complete:
                    self.on_scan_complete(barcode_data)
                self.dismiss()
                break

        except Exception as e:
            print(f"Barcode detection error: {str(e)}")
            self.scan_label.text = 'Scanner error: Please try again'
            self.cleanup()
            self.dismiss()

    def cleanup(self):
        Clock.unschedule(self.update)
        if self.capture:
            self.capture.release()

    def on_dismiss(self):
        self.cleanup()
        return super().on_dismiss()

class CashierSystem:
    def __init__(self):
        # MongoDB connection
        connection_string = "mongodb+srv://majdsukkary472:Ny4Rtjg1bDtKzptn@cluster0.1x9tg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
        try:
            self.client = pymongo.MongoClient(connection_string, server_api=ServerApi('1'))
            self.client.admin.command('ping')
            print("Successfully connected to MongoDB!")
        except Exception as e:
            print(f"Error connecting to MongoDB: {str(e)}")
            sys.exit(1)
            
        self.db = self.client.expiry_tracker
        self.users = self.db.users
        self.items = self.db.items
        self.transactions = self.db.transactions
        
        # Current transaction data
        self.current_user = None
        self.current_items = []

        # Create barcodes directory if it doesn't exist
        if not os.path.exists('barcodes'):
            os.makedirs('barcodes')

    def find_user(self, barcode):
        return self.users.find_one({'barcode': barcode})

    def find_item(self, barcode):
        return self.items.find_one({'barcode': barcode})

    def add_item(self, item):
        self.current_items.append(item)

    def finish_transaction(self):
        if not self.current_user or not self.current_items:
            return False

        try:
            total = sum(item['price'] for item in self.current_items)
            
            transaction = {
                'user_id': self.current_user['_id'],
                'items': [item['_id'] for item in self.current_items],
                'total': total,
                'timestamp': datetime.utcnow()
            }
            self.transactions.insert_one(transaction)
            
            for item in self.current_items:
                self.items.update_one(
                    {'_id': item['_id']},
                    {'$set': {
                        'user_id': self.current_user['_id'],
                        'purchase_date': datetime.utcnow()
                    }}
                )
            
            self.clear_transaction()
            return True
            
        except Exception as e:
            print(f"Error completing transaction: {str(e)}")
            return False

    def clear_transaction(self):
        self.current_user = None
        self.current_items = []

    def generate_item_barcode(self):
        """Generate a unique EAN-13 barcode for an item"""
        while True:
            # Generate first 12 digits randomly
            first_digits = ''.join([str(random.randint(0, 9)) for _ in range(12)])
            
            # Calculate check digit according to EAN-13 algorithm
            total = 0
            for i in range(12):
                digit = int(first_digits[i])
                if i % 2 == 0:
                    total += digit
                else:
                    total += digit * 3
            
            check_digit = (10 - (total % 10)) % 10
            
            # Complete barcode
            barcode = first_digits + str(check_digit)
            
            # Check if barcode already exists
            if not self.items.find_one({'barcode': barcode}):
                # Generate barcode image
                ean = EAN13(barcode, writer=ImageWriter())
                ean.save(f'barcodes/item_{barcode}')
                return barcode

    def get_expired_items(self):
        """Get items that have passed their expiry date"""
        now = datetime.utcnow()
        expired = self.items.find({
            'expiry_date': {'$lt': now},
            'user_id': {'$exists': False}  # Only show items not yet purchased
        }).sort('expiry_date', 1)  # Sort by expiry date ascending
        return list(expired)

    def get_about_to_expire_items(self, days_threshold=2):
        """Get items that will expire within the specified number of days"""
        now = datetime.utcnow()
        # Start of today
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        # End of threshold day
        threshold = (today + timedelta(days=days_threshold)).replace(hour=23, minute=59, second=59)
        
        about_to_expire = self.items.find({
            'expiry_date': {
                '$gte': today,
                '$lte': threshold
            },
            'user_id': {'$exists': False}  # Only show items not yet purchased
        }).sort('expiry_date', 1)  # Sort by expiry date ascending
        
        # Debug print
        print(f"Searching for items expiring between {today} and {threshold}")
        items = list(about_to_expire)
        print(f"Found {len(items)} items")
        for item in items:
            print(f"Item: {item['name']}, Expiry: {item['expiry_date']}")
        
        return items

    def add_new_item(self, name, price, category, expiry_date):
        """Add a new item to the database with a generated barcode"""
        try:
            barcode = self.generate_item_barcode()
            
            # Convert expiry_date to UTC if it's not already
            if isinstance(expiry_date, datetime):
                # Set time to end of day for expiry
                expiry_date = expiry_date.replace(
                    hour=23, 
                    minute=59, 
                    second=59, 
                    microsecond=999999,
                    tzinfo=None  # Remove timezone if present
                )
            
            item = {
                'name': name,
                'price': price,
                'category': category,
                'expiry_date': expiry_date,
                'barcode': barcode,
                'created_at': datetime.utcnow()
            }
            
            # Debug print
            print(f"Adding item {name} with expiry date: {expiry_date}")
            
            result = self.items.insert_one(item)
            if result.inserted_id:
                print(f"Added item: {name} with barcode: {barcode}")
                return self.items.find_one({'_id': result.inserted_id})
            return None
            
        except Exception as e:
            print(f"Error adding item: {str(e)}")
            return None

    def get_item_barcode_path(self, barcode):
        """Get the path to a barcode image"""
        return f'barcodes/item_{barcode}.png'

if __name__ == '__main__':
    # Remove the test code from here and add a flag
    parser = argparse.ArgumentParser()
    parser.add_argument('--generate-samples', action='store_true', 
                       help='Generate sample items with barcodes')
    args = parser.parse_args()

    if args.generate_samples:
        # Generate sample items
        cashier = CashierSystem()
        test_items = [
            {
                'name': 'Milk',
                'price': 3.99,
                'category': 'Dairy',
                'expiry_date': datetime.now() + timedelta(days=7)
            },
            {
                'name': 'Bread',
                'price': 2.49,
                'category': 'Bakery',
                'expiry_date': datetime.now() + timedelta(days=5)
            },
            {
                'name': 'Eggs',
                'price': 4.99,
                'category': 'Dairy',
                'expiry_date': datetime.now() + timedelta(days=14)
            }
        ]
        
        for item in test_items:
            added_item = cashier.add_new_item(
                name=item['name'],
                price=item['price'],
                category=item['category'],
                expiry_date=item['expiry_date']
            )
            if added_item:
                print(f"Generated barcode for {item['name']}: {added_item['barcode']}")
                print(f"Barcode image saved at: {cashier.get_item_barcode_path(added_item['barcode'])}")
    else:
        # Run the cashier app normally
        CashierApp().run() 