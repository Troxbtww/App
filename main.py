from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.uix.checkbox import CheckBox
from kivy.uix.modalview import ModalView
from kivy.uix.switch import Switch
from kivy.uix.widget import Widget
from kivy.uix.image import Image, AsyncImage
from kivy.core.window import Window
from barcode import EAN13
from barcode.writer import ImageWriter
import os
from io import BytesIO
import pymongo
from pymongo.server_api import ServerApi
from datetime import datetime, timedelta
from kivy.graphics import Color, Rectangle
from kivy.uix.camera import Camera
from kivy.clock import Clock
from pyzbar.pyzbar import decode
import cv2
import numpy as np
from cashier import BarcodeScanner
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.screenmanager import MDScreenManager
from kivy.metrics import dp
from kivymd.uix.selectioncontrol import MDSwitch
from kivymd.uix.widget import Widget as MDWidget
from kivymd.uix.button import MDIconButton
from kivy.core.image import Image as CoreImage
from kivy.lang import Builder
from kivy.uix.anchorlayout import AnchorLayout

# Register SVG provider at the start of your app
Builder.load_string('''
#:import CoreSvg kivy.core.image.img_sdl2
''')

class SettingsSidebar(ModalView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.85, 1)  # Width of the sidebar
        self.pos_hint = {'right': 1}  # Position from right
        
        # Main layout using MDCard for Material Design look
        main_card = MDCard(
            orientation='vertical',
            padding=dp(20),
            spacing=dp(10),
            elevation=10,
            size_hint=(1, 1),
            radius=[0]  # Remove rounded corners
        )
        
        # Header
        header = MDLabel(
            text='Settings',
            font_style='H5',
            size_hint_y=0.1
        )
        
        # Settings content
        content = BoxLayout(orientation='vertical', spacing=dp(15))
        
        # Account Settings Section
        account_settings = BoxLayout(orientation='vertical', spacing=dp(10))
        account_settings_label = MDLabel(
            text='Account Settings',
            font_style='H6',
            bold=True
        )
        
        edit_profile_btn = MDRaisedButton(
            text='Edit Profile',
            size_hint_x=1
        )
        
        change_password_btn = MDRaisedButton(
            text='Change Password',
            size_hint_x=1
        )
        
        account_settings.add_widget(account_settings_label)
        account_settings.add_widget(edit_profile_btn)
        account_settings.add_widget(change_password_btn)
        
        # Rate Us Section
        rate_us = MDRaisedButton(
            text='Rate Us',
            size_hint_x=1
        )
        
        # Close button
        close_btn = MDRaisedButton(
            text='Close',
            size_hint_x=1,
            on_press=self.dismiss
        )
        
        # Add all sections to content
        content.add_widget(account_settings)
        content.add_widget(rate_us)
        content.add_widget(MDWidget())  # Spacer
        content.add_widget(close_btn)
        
        # Add everything to main card
        main_card.add_widget(header)
        main_card.add_widget(content)
        
        # Add card to modal
        self.add_widget(main_card)

class BarcodeHeader(BoxLayout):
    def __init__(self, user_barcode, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = 0.15
        self.padding = [10, 5]
        
        # Get app instance and current barcode
        app = App.get_running_app()
        current_barcode = app.get_user_barcode()
        print(f"\nDebug - BarcodeHeader initialization:")
        print(f"Passed barcode: {user_barcode}")
        print(f"Current user barcode: {current_barcode}")
        
        # Generate barcode if it doesn't exist
        app.generate_barcode(current_barcode)
        
        # Create and add barcode image
        barcode_image = Image(
            source=f"barcodes/barcode_{current_barcode}.png",
            size_hint=(0.7, None),
            height=100,
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        
        # Add a centered container for the barcode
        center_layout = BoxLayout(orientation='vertical')
        center_layout.add_widget(Widget())  # Top spacer
        center_layout.add_widget(barcode_image)
        center_layout.add_widget(Widget())  # Bottom spacer
        
        self.add_widget(center_layout)

class BaseScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sidebar = None
        self._app = App.get_running_app()
    
    def show_sidebar(self, instance):
        if not self.sidebar:
            self.sidebar = SettingsSidebar()
        self.sidebar.open()
    
    def get_barcode(self):
        return self._app.get_user_barcode()

class UserTypeScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        # Add settings button to top right
        header_layout = BoxLayout(size_hint_y=0.1)
        settings_btn = Button(
            text='⚙️',  # Gear emoji as settings icon
            size_hint=(None, None),
            size=(40, 40),
            pos_hint={'right': 1},
            on_press=self.show_sidebar
        )
        header_layout.add_widget(Widget())  # Spacer
        header_layout.add_widget(settings_btn)
        
        # Title
        title = Label(
            text='How would you use the app?',
            font_size='24sp',
            size_hint_y=0.3
        )
        
        # Buttons for user type selection
        individual_btn = Button(
            text='Individual',
            size_hint=(0.8, 0.2),
            pos_hint={'center_x': 0.5},
            on_press=self.select_individual
        )
        
        business_btn = Button(
            text='Business',
            size_hint=(0.8, 0.2),
            pos_hint={'center_x': 0.5},
            on_press=self.select_business
        )
        
        # Add widgets to layout
        layout.add_widget(header_layout)
        layout.add_widget(title)
        layout.add_widget(individual_btn)
        layout.add_widget(business_btn)
        self.add_widget(layout)
    
    def select_individual(self, instance):
        app = App.get_running_app()
        app.set_user('individual')
        self.manager.current = 'all_items'
    
    def select_business(self, instance):
        app = App.get_running_app()
        app.set_user('business')
        self.manager.current = 'buy_items'

class AllItemsScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=10)
        
        # Add settings button to top right
        header_layout = BoxLayout(size_hint_y=0.1)
        settings_btn = MDIconButton(
            icon="cog",
            pos_hint={'right': 1},
            on_press=self.show_sidebar
        )
        header_layout.add_widget(Widget())
        header_layout.add_widget(settings_btn)
        
        # Add barcode header
        barcode_header = BarcodeHeader(self.get_barcode())
        
        # Header
        header = MDLabel(
            text='All Items',
            font_style='H5',
            halign='center',
            size_hint_y=0.1
        )
        
        # Scrollable content
        scroll = ScrollView()
        self.items_layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.items_layout.bind(minimum_height=self.items_layout.setter('height'))
        
        # Load user's items
        self.load_items()
        
        # Navigation buttons
        nav_layout = BoxLayout(
            size_hint_y=None,
            height=dp(60),
            spacing=dp(20),  # Increased spacing between buttons
            padding=[dp(20), 0],  # Increased padding on sides
            pos_hint={'center_x': 0.5}  # Center the layout horizontally
        )
        
        about_to_expire_btn = MDRaisedButton(
            text='About to Expire',
            size_hint_x=None,  # Remove size_hint_x
            width=dp(150),  # Set fixed width
            pos_hint={'center_x': 0.5},  # Center the button
            on_press=self.go_to_about_to_expire
        )
        
        expired_btn = MDRaisedButton(
            text='Expired Items',
            size_hint_x=None,  # Remove size_hint_x
            width=dp(150),  # Set fixed width
            pos_hint={'center_x': 0.5},  # Center the button
            on_press=self.go_to_expired
        )
        
        # Add a spacer widget at the start for centering
        nav_layout.add_widget(Widget())
        nav_layout.add_widget(about_to_expire_btn)
        nav_layout.add_widget(expired_btn)
        # Add a spacer widget at the end for centering
        nav_layout.add_widget(Widget())
        
        # Add everything to main layout
        layout.add_widget(header_layout)
        layout.add_widget(barcode_header)
        layout.add_widget(header)
        layout.add_widget(scroll)
        layout.add_widget(nav_layout)
        scroll.add_widget(self.items_layout)
        self.add_widget(layout)
    
    def load_items(self):
        # Clear existing items
        self.items_layout.clear_widgets()
        
        # Get current user's ID
        app = App.get_running_app()
        if not app.current_user:
            return
        
        # Query items belonging to the current user
        items = app.db.items.find({'user_id': app.current_user['_id']})
        
        for item in items:
            # Create item card
            item_card = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                height=100,
                padding=10,
                spacing=5
            )
            
            # Add item details
            name_label = Label(
                text=f"{item['name']} - ${item['price']:.2f}",
                size_hint_y=0.4
            )
            
            # Format expiry date and calculate days remaining
            expiry_date = item['expiry_date']
            days_remaining = (expiry_date - datetime.now()).days
            
            if days_remaining < 0:
                status_text = f"Expired {abs(days_remaining)} days ago"
                status_color = (1, 0, 0, 1)  # Red
            elif days_remaining <= 3:
                status_text = f"Expires in {days_remaining} days"
                status_color = (1, 0.65, 0, 1)  # Orange
            else:
                status_text = f"Expires in {days_remaining} days"
                status_color = (0, 0.7, 0, 1)  # Green
            
            expiry_label = Label(
                text=status_text,
                color=status_color,
                size_hint_y=0.3
            )
            
            category_label = Label(
                text=f"Category: {item['category']}",
                size_hint_y=0.3
            )
            
            item_card.add_widget(name_label)
            item_card.add_widget(expiry_label)
            item_card.add_widget(category_label)
            
            # Add separator using a BoxLayout with background color
            separator = BoxLayout(
                size_hint_y=None,
                height=1
            )
            with separator.canvas.before:
                Color(0.8, 0.8, 0.8, 1)  # Light gray
                Rectangle(pos=separator.pos, size=separator.size)
            
            # Bind the separator's position and size to its layout
            def update_separator(instance, value):
                instance.canvas.before.clear()
                with instance.canvas.before:
                    Color(0.8, 0.8, 0.8, 1)
                    Rectangle(pos=instance.pos, size=instance.size)
            
            separator.bind(pos=update_separator, size=update_separator)
            
            self.items_layout.add_widget(item_card)
            self.items_layout.add_widget(separator)
    
    def on_enter(self):
        # Reload items when screen is shown
        self.load_items()
    
    def go_to_about_to_expire(self, instance):
        self.manager.current = 'about_to_expire'
    
    def go_to_expired(self, instance):
        self.manager.current = 'expired'

class AboutToExpireScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=10)
        
        # Add settings button to top right
        header_layout = BoxLayout(size_hint_y=0.1)
        settings_btn = MDIconButton(
            icon="cog",
            pos_hint={'right': 1},
            on_press=self.show_sidebar
        )
        header_layout.add_widget(Widget())
        header_layout.add_widget(settings_btn)
        
        # Header
        header = MDLabel(
            text='Items About to Expire',
            font_style='H5',
            halign='center',
            size_hint_y=0.1
        )
        
        # Scrollable content
        scroll = ScrollView()
        self.items_layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.items_layout.bind(minimum_height=self.items_layout.setter('height'))
        
        # Load items
        self.load_items()
        
        # Action buttons
        action_layout = BoxLayout(
            size_hint_y=None,
            height=dp(60),
            spacing=dp(20),  # Increased spacing between buttons
            padding=[dp(20), 0],  # Increased padding on sides
            pos_hint={'center_x': 0.5}  # Center the layout horizontally
        )
        donate_btn = MDRaisedButton(
            text='Donate Items',
            size_hint_x=None,  # Remove size_hint_x
            width=dp(150),  # Set fixed width
            pos_hint={'center_x': 0.5}  # Center the button
        )
        sell_btn = MDRaisedButton(
            text='Sell Items',
            size_hint_x=None,  # Remove size_hint_x
            width=dp(150),  # Set fixed width
            pos_hint={'center_x': 0.5}  # Center the button
        )
        
        # Add spacer widgets for centering
        action_layout.add_widget(Widget())
        action_layout.add_widget(donate_btn)
        action_layout.add_widget(sell_btn)
        action_layout.add_widget(Widget())
        
        # Navigation buttons
        nav_layout = BoxLayout(
            size_hint_y=None,
            height=dp(60),
            spacing=dp(20),  # Increased spacing between buttons
            padding=[dp(20), 0],  # Increased padding on sides
            pos_hint={'center_x': 0.5}  # Center the layout horizontally
        )
        all_items_btn = MDRaisedButton(
            text='All Items',
            size_hint_x=None,  # Remove size_hint_x
            width=dp(150),  # Set fixed width
            pos_hint={'center_x': 0.5},  # Center the button
            on_press=self.go_to_all_items
        )
        expired_btn = MDRaisedButton(
            text='Expired Items',
            size_hint_x=None,  # Remove size_hint_x
            width=dp(150),  # Set fixed width
            pos_hint={'center_x': 0.5},  # Center the button
            on_press=self.go_to_expired
        )
        
        # Add spacer widgets for centering
        nav_layout.add_widget(Widget())
        nav_layout.add_widget(all_items_btn)
        nav_layout.add_widget(expired_btn)
        nav_layout.add_widget(Widget())
        
        # Add everything to main layout
        layout.add_widget(header_layout)
        layout.add_widget(header)
        layout.add_widget(scroll)
        layout.add_widget(action_layout)
        layout.add_widget(nav_layout)
        scroll.add_widget(self.items_layout)
        self.add_widget(layout)
    
    def load_items(self):
        # Clear existing items
        self.items_layout.clear_widgets()
        
        # Get current user's ID
        app = App.get_running_app()
        if not app.current_user:
            return
        
        # Get current date and date 3 days from now
        now = datetime.now()
        three_days_later = now + timedelta(days=3)
        
        # Query items that will expire within 3 days
        items = app.db.items.find({
            'user_id': app.current_user['_id'],
            'expiry_date': {
                '$gt': now,
                '$lte': three_days_later
            }
        })
        
        for item in items:
            # Create item card
            item_card = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                height=100,
                padding=10,
                spacing=5
            )
            
            # Add item details
            name_label = Label(
                text=f"{item['name']} - ${item['price']:.2f}",
                size_hint_y=0.4
            )
            
            # Calculate days remaining
            days_remaining = (item['expiry_date'] - now).days
            expiry_label = Label(
                text=f"Expires in {days_remaining} days",
                color=(1, 0.65, 0, 1),  # Orange
                size_hint_y=0.3
            )
            
            category_label = Label(
                text=f"Category: {item['category']}",
                size_hint_y=0.3
            )
            
            item_card.add_widget(name_label)
            item_card.add_widget(expiry_label)
            item_card.add_widget(category_label)
            
            # Add separator
            separator = BoxLayout(size_hint_y=None, height=1)
            with separator.canvas.before:
                Color(0.8, 0.8, 0.8, 1)
                Rectangle(pos=separator.pos, size=separator.size)
            
            self.items_layout.add_widget(item_card)
            self.items_layout.add_widget(separator)
    
    def on_enter(self):
        # Reload items when screen is shown
        self.load_items()
    
    def go_to_all_items(self, instance):
        self.manager.current = 'all_items'
    
    def go_to_expired(self, instance):
        self.manager.current = 'expired'

class ExpiredItemsScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=10)
        
        # Add settings button to top right
        header_layout = BoxLayout(size_hint_y=0.1)
        settings_btn = MDIconButton(
            icon="cog",
            pos_hint={'right': 1},
            on_press=self.show_sidebar
        )
        header_layout.add_widget(Widget())
        header_layout.add_widget(settings_btn)
        
        # Header
        header = MDLabel(
            text='Expired Items',
            font_style='H5',
            halign='center',
            size_hint_y=0.1
        )
        
        # Scrollable content
        scroll = ScrollView()
        self.items_layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.items_layout.bind(minimum_height=self.items_layout.setter('height'))
        
        # Load items
        self.load_items()
        
        # Action button
        action_layout = BoxLayout(
            size_hint_y=None,
            height=dp(60),
            spacing=dp(20),  # Increased spacing between buttons
            padding=[dp(20), 0],  # Increased padding on sides
            pos_hint={'center_x': 0.5}  # Center the layout horizontally
        )
        recycle_btn = MDRaisedButton(
            text='Send to a Digester',
            size_hint_x=None,  # Remove size_hint_x
            width=dp(200),  # Set fixed width, slightly wider for longer text
            pos_hint={'center_x': 0.5}  # Center the button
        )
        
        # Add spacer widgets for centering
        action_layout.add_widget(Widget())
        action_layout.add_widget(recycle_btn)
        action_layout.add_widget(Widget())
        
        # Navigation buttons
        nav_layout = BoxLayout(
            size_hint_y=None,
            height=dp(60),
            spacing=dp(20),  # Increased spacing between buttons
            padding=[dp(20), 0],  # Increased padding on sides
            pos_hint={'center_x': 0.5}  # Center the layout horizontally
        )
        all_items_btn = MDRaisedButton(
            text='All Items',
            size_hint_x=None,  # Remove size_hint_x
            width=dp(150),  # Set fixed width
            pos_hint={'center_x': 0.5},  # Center the button
            on_press=self.go_to_all_items
        )
        about_to_expire_btn = MDRaisedButton(
            text='About to Expire',
            size_hint_x=None,  # Remove size_hint_x
            width=dp(150),  # Set fixed width
            pos_hint={'center_x': 0.5},  # Center the button
            on_press=self.go_to_about_to_expire
        )
        
        # Add spacer widgets for centering
        nav_layout.add_widget(Widget())
        nav_layout.add_widget(all_items_btn)
        nav_layout.add_widget(about_to_expire_btn)
        nav_layout.add_widget(Widget())
        
        # Add everything to main layout
        layout.add_widget(header_layout)
        layout.add_widget(header)
        layout.add_widget(scroll)
        layout.add_widget(action_layout)
        layout.add_widget(nav_layout)
        scroll.add_widget(self.items_layout)
        self.add_widget(layout)
    
    def load_items(self):
        # Clear existing items
        self.items_layout.clear_widgets()
        
        # Get current user's ID
        app = App.get_running_app()
        if not app.current_user:
            return
        
        # Get current date
        now = datetime.now()
        
        # Query expired items
        items = app.db.items.find({
            'user_id': app.current_user['_id'],
            'expiry_date': {'$lt': now}
        })
        
        for item in items:
            # Create item card
            item_card = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                height=100,
                padding=10,
                spacing=5
            )
            
            # Add item details
            name_label = Label(
                text=f"{item['name']} - ${item['price']:.2f}",
                size_hint_y=0.4
            )
            
            # Calculate days expired
            days_expired = (now - item['expiry_date']).days
            expiry_label = Label(
                text=f"Expired {days_expired} days ago",
                color=(1, 0, 0, 1),  # Red
                size_hint_y=0.3
            )
            
            category_label = Label(
                text=f"Category: {item['category']}",
                size_hint_y=0.3
            )
            
            item_card.add_widget(name_label)
            item_card.add_widget(expiry_label)
            item_card.add_widget(category_label)
            
            # Add separator
            separator = BoxLayout(size_hint_y=None, height=1)
            with separator.canvas.before:
                Color(0.8, 0.8, 0.8, 1)
                Rectangle(pos=separator.pos, size=separator.size)
            
            self.items_layout.add_widget(item_card)
            self.items_layout.add_widget(separator)
    
    def on_enter(self):
        # Reload items when screen is shown
        self.load_items()
    
    def go_to_all_items(self, instance):
        self.manager.current = 'all_items'
    
    def go_to_about_to_expire(self, instance):
        self.manager.current = 'about_to_expire'

class BuyItemsScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=10)
        
        # Add settings button to top right
        header_layout = BoxLayout(size_hint_y=0.1)
        settings_btn = Button(
            text='⚙️',
            size_hint=(None, None),
            size=(40, 40),
            pos_hint={'right': 1},
            on_press=self.show_sidebar
        )
        
        # Add scan button
        scan_btn = Button(
            text='Scan Barcode',
            size_hint=(None, None),
            size=(120, 40),
            pos_hint={'center_x': 0.5},
            on_press=self.show_scanner
        )
        
        header_layout.add_widget(Widget())
        header_layout.add_widget(scan_btn)
        header_layout.add_widget(settings_btn)
        
        # Header
        header = Label(
            text='Buy Items',
            font_size='20sp',
            size_hint_y=0.1
        )
        
        # Search bar
        search_layout = BoxLayout(size_hint_y=0.1, padding=5)
        search_input = TextInput(
            hint_text='Search items...',
            multiline=False,
            size_hint_x=0.8
        )
        search_btn = Button(
            text='Search',
            size_hint_x=0.2
        )
        search_layout.add_widget(search_input)
        search_layout.add_widget(search_btn)
        
        # Items list
        scroll = ScrollView()
        items_layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
        items_layout.bind(minimum_height=items_layout.setter('height'))
        
        # Navigation
        nav_layout = BoxLayout(size_hint_y=0.1, spacing=10)
        sell_btn = Button(
            text='Sell Items',
            on_press=self.go_to_sell
        )
        preferences_btn = Button(
            text='Preferences',
            on_press=self.go_to_preferences
        )
        expired_btn = Button(
            text='Expired Items',
            on_press=self.go_to_expired
        )
        
        nav_layout.add_widget(sell_btn)
        nav_layout.add_widget(preferences_btn)
        nav_layout.add_widget(expired_btn)
        
        layout.add_widget(header_layout)
        layout.add_widget(header)
        layout.add_widget(search_layout)
        layout.add_widget(scroll)
        layout.add_widget(nav_layout)
        scroll.add_widget(items_layout)
        self.add_widget(layout)
    
    def show_scanner(self, instance):
        scanner = BarcodeScanner(on_scan_complete=self.on_barcode_scanned)
        scanner.open()

    def on_barcode_scanned(self, barcode):
        print(f"Processing scanned barcode: {barcode}")
        # Here you can add logic to process the scanned barcode
        # For example, look up the item in your database and add it to the cart
    
    def go_to_sell(self, instance):
        self.manager.current = 'sell_items'
    
    def go_to_preferences(self, instance):
        self.manager.current = 'preferences'
    
    def go_to_expired(self, instance):
        self.manager.current = 'business_expired'

class SellItemsScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=10)
        
        # Add settings button to top right
        header_layout = BoxLayout(size_hint_y=0.1)
        settings_btn = Button(
            text='⚙️',
            size_hint=(None, None),
            size=(40, 40),
            pos_hint={'right': 1},
            on_press=self.show_sidebar
        )
        header_layout.add_widget(Widget())  # Spacer
        header_layout.add_widget(settings_btn)
        
        header = Label(
            text='Sell Items',
            font_size='20sp',
            size_hint_y=0.1
        )
        
        # Add item button
        add_btn = Button(
            text='Add New Item',
            size_hint_y=0.1
        )
        
        # Items list
        scroll = ScrollView()
        items_layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
        items_layout.bind(minimum_height=items_layout.setter('height'))
        
        # Navigation
        nav_layout = BoxLayout(size_hint_y=0.1, spacing=10)
        buy_btn = Button(
            text='Buy Items',
            on_press=self.go_to_buy
        )
        preferences_btn = Button(
            text='Preferences',
            on_press=self.go_to_preferences
        )
        expired_btn = Button(
            text='Expired Items',
            on_press=self.go_to_expired
        )
        
        nav_layout.add_widget(buy_btn)
        nav_layout.add_widget(preferences_btn)
        nav_layout.add_widget(expired_btn)
        
        layout.add_widget(header_layout)
        layout.add_widget(header)
        layout.add_widget(add_btn)
        layout.add_widget(scroll)
        layout.add_widget(nav_layout)
        scroll.add_widget(items_layout)
        self.add_widget(layout)
    
    def go_to_buy(self, instance):
        self.manager.current = 'buy_items'
    
    def go_to_preferences(self, instance):
        self.manager.current = 'preferences'
    
    def go_to_expired(self, instance):
        self.manager.current = 'business_expired'

class PreferencesScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=10)
        
        # Add settings button to top right
        header_layout = BoxLayout(size_hint_y=0.1)
        settings_btn = Button(
            text='⚙️',
            size_hint=(None, None),
            size=(40, 40),
            pos_hint={'right': 1},
            on_press=self.show_sidebar
        )
        header_layout.add_widget(Widget())  # Spacer
        header_layout.add_widget(settings_btn)
        
        header = Label(
            text='Item Preferences',
            font_size='20sp',
            size_hint_y=0.1
        )
        
        # Categories scroll
        scroll = ScrollView()
        categories_layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
        categories_layout.bind(minimum_height=categories_layout.setter('height'))
        
        # Example categories (you can add more)
        categories = ['Dairy', 'Meat', 'Vegetables', 'Fruits', 'Bakery']
        for category in categories:
            category_layout = BoxLayout(size_hint_y=None, height=40)
            checkbox = CheckBox()
            label = Label(text=category)
            category_layout.add_widget(checkbox)
            category_layout.add_widget(label)
            categories_layout.add_widget(category_layout)
        
        # Navigation
        nav_layout = BoxLayout(size_hint_y=0.1, spacing=10)
        buy_btn = Button(
            text='Buy Items',
            on_press=self.go_to_buy
        )
        sell_btn = Button(
            text='Sell Items',
            on_press=self.go_to_sell
        )
        expired_btn = Button(
            text='Expired Items',
            on_press=self.go_to_expired
        )
        
        nav_layout.add_widget(buy_btn)
        nav_layout.add_widget(sell_btn)
        nav_layout.add_widget(expired_btn)
        
        layout.add_widget(header_layout)
        layout.add_widget(header)
        layout.add_widget(scroll)
        layout.add_widget(nav_layout)
        scroll.add_widget(categories_layout)
        self.add_widget(layout)
    
    def go_to_buy(self, instance):
        self.manager.current = 'buy_items'
    
    def go_to_sell(self, instance):
        self.manager.current = 'sell_items'
    
    def go_to_expired(self, instance):
        self.manager.current = 'business_expired'

class BusinessExpiredScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=10)
        
        # Add settings button to top right
        header_layout = BoxLayout(size_hint_y=0.1)
        settings_btn = Button(
            text='⚙️',
            size_hint=(None, None),
            size=(40, 40),
            pos_hint={'right': 1},
            on_press=self.show_sidebar
        )
        header_layout.add_widget(Widget())  # Spacer
        header_layout.add_widget(settings_btn)
        
        header = Label(
            text='Expired Items',
            font_size='20sp',
            size_hint_y=0.1
        )
        
        # Add expired item button
        add_btn = Button(
            text='Add Expired Item',
            size_hint_y=0.1
        )
        
        # Items list
        scroll = ScrollView()
        items_layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
        items_layout.bind(minimum_height=items_layout.setter('height'))
        
        # Recycle button
        recycle_btn = Button(
            text='Send to a Digester',
            size_hint_y=0.1
        )
        
        # Navigation
        nav_layout = BoxLayout(size_hint_y=0.1, spacing=10)
        buy_btn = Button(
            text='Buy Items',
            on_press=self.go_to_buy
        )
        sell_btn = Button(
            text='Sell Items',
            on_press=self.go_to_sell
        )
        preferences_btn = Button(
            text='Preferences',
            on_press=self.go_to_preferences
        )
        
        nav_layout.add_widget(buy_btn)
        nav_layout.add_widget(sell_btn)
        nav_layout.add_widget(preferences_btn)
        
        layout.add_widget(header_layout)
        layout.add_widget(header)
        layout.add_widget(add_btn)
        layout.add_widget(scroll)
        layout.add_widget(recycle_btn)
        layout.add_widget(nav_layout)
        scroll.add_widget(items_layout)
        self.add_widget(layout)
    
    def go_to_buy(self, instance):
        self.manager.current = 'buy_items'
    
    def go_to_sell(self, instance):
        self.manager.current = 'sell_items'
    
    def go_to_preferences(self, instance):
        self.manager.current = 'preferences'

class GreetingScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'greeting'
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        # Add logo image
        logo_layout = BoxLayout(
            orientation='vertical',
            size_hint=(1, None),
            height=dp(250),  # Increased height for better spacing
            padding=[0, dp(20)]  # Only vertical padding
        )
        
        # Add a container to center the logo
        center_box = AnchorLayout(  # Changed to AnchorLayout for better centering
            size_hint=(1, 1),
            anchor_x='center',
            anchor_y='center'
        )
        
        logo = Image(
            source='Assets/Group 1.png',
            size_hint=(None, None),
            size=(dp(200), dp(200)),
            allow_stretch=True,
            keep_ratio=True,
            mipmap=True
        )
        
        center_box.add_widget(logo)
        logo_layout.add_widget(center_box)
        
        # Welcome message
        welcome_label = Label(
            text="Discover What\nYour Food Can Do",
            halign="center",
            font_name="NunitoBlack",  # Changed from "Nunito" to "NunitoBlack"
            font_size="32sp",
            color=[0.298, 0.141, 0.114, 1],
            padding=[0, 20]
        )
        
        # Description
        description_label = MDLabel(
            text="Track all your items' expiration dates.\nExpired items? We got you.",  # Added line break
            halign="center",
            theme_text_color="Secondary",
            padding=[0, 0]  # Reduced from 20 to 0
        )
        
        # Buttons layout
        buttons_layout = BoxLayout(
            orientation='horizontal',
            spacing=dp(40),
            size_hint=(None, None),
            height=dp(100),  # Increased from 90 to 100
            width=dp(740),  # Increased to fit larger buttons (350 * 2 + 40 spacing)
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        
        # Add flexible spacer at the start
        buttons_layout.add_widget(Widget(size_hint_x=1))  # Changed width to flexible
        
        # Login button
        login_btn = MDFlatButton(
            text="Login",
            size_hint=(None, None),  # Keep this as None, None
            width=dp(350),  # Set fixed width
            height=dp(100),
            md_bg_color=[0.298, 0.141, 0.114, 1],
            text_color=[1, 1, 1, 1],
            theme_text_color="Custom",
            font_name="PoppinsSemiBold",
            ripple_color=[0, 0, 0, 0],
            _radius=dp(10),
            pos_hint={'center_y': 0.5},
            on_press=self.go_to_login
        )
        
        # Register button
        register_btn = MDFlatButton(
            text="Register",
            size_hint=(None, None),  # Keep this as None, None
            width=dp(350),  # Set fixed width
            height=dp(100),
            text_color=[0.039, 0.039, 0.039, 1],
            font_name="PoppinsSemiBold",
            ripple_color=[0, 0, 0, 0],
            pos_hint={'center_y': 0.5},
            on_press=self.go_to_register
        )
        
        # Add widgets to layout
        layout.add_widget(logo_layout)
        layout.add_widget(welcome_label)
        layout.add_widget(description_label)
        buttons_layout.add_widget(login_btn)
        buttons_layout.add_widget(register_btn)
        # Add flexible spacer at the end
        buttons_layout.add_widget(Widget(size_hint_x=1))  # Changed width to flexible
        layout.add_widget(buttons_layout)
        
        self.add_widget(layout)
    
    def go_to_login(self, instance):
        self.manager.transition.direction = 'left'
        self.manager.current = 'login'
    
    def go_to_register(self, instance):
        self.manager.transition.direction = 'left'
        self.manager.current = 'register'

class LoginScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'login'
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        # Back button
        back_btn = MDIconButton(
            icon="arrow-left",
            pos_hint={'left': 1},
            on_press=self.go_back
        )
        
        # Title
        title = Label(
            text="Login here",
            halign="center",
            font_name="NunitoBlack",
            font_size="32sp",
            color=[0.298, 0.141, 0.114, 1],
            size_hint_y=None,
            height=dp(50)  # Added fixed height to control spacing
        )
        
        # Welcome back message
        welcome_back = MDLabel(
            text="Welcome back you've\nbeen missed!",
            halign="center",
            theme_text_color="Secondary",
            font_size="14sp",
            size_hint_y=None,
            height=dp(40)  # Added fixed height to control spacing
        )
        
        # Login fields
        self.username = MDTextField(
            hint_text="Username",
            helper_text="Enter your username",
            helper_text_mode="on_error",
            size_hint_x=0.9,
            pos_hint={'center_x': 0.5},
            line_color_normal=[0.298, 0.141, 0.114, 1],  # Brown color when not focused
            line_color_focus=[0.298, 0.141, 0.114, 1],   # Brown color when focused
            text_color_focus=[0.298, 0.141, 0.114, 1]    # Brown text color when focused
        )
        
        self.password = MDTextField(
            hint_text="Password",
            helper_text="Enter your password",
            helper_text_mode="on_error",
            password=True,
            size_hint_x=0.9,
            pos_hint={'center_x': 0.5},
            line_color_normal=[0.298, 0.141, 0.114, 1],
            line_color_focus=[0.298, 0.141, 0.114, 1],
            text_color_focus=[0.298, 0.141, 0.114, 1]
        )
        
        # Login button
        login_btn = MDFlatButton(
            text="Login",
            size_hint_x=0.9,  # Changed to match input fields
            height=dp(90),
            md_bg_color=[0.298, 0.141, 0.114, 1],
            text_color=[1, 1, 1, 1],
            theme_text_color="Custom",
            font_name="PoppinsSemiBold",
            ripple_color=[0, 0, 0, 0],
            _radius=dp(10),
            pos_hint={'center_x': 0.5},
            on_press=self.login
        )
        
        # Error message label
        self.error_label = MDLabel(
            text="",
            theme_text_color="Error",
            halign="center",
            size_hint_y=0.1
        )
        
        # Add widgets to layout
        layout.add_widget(back_btn)
        layout.add_widget(title)
        layout.add_widget(welcome_back)  # Added welcome back message
        layout.add_widget(self.username)
        layout.add_widget(self.password)
        layout.add_widget(Widget())  # Spacer
        layout.add_widget(login_btn)
        layout.add_widget(self.error_label)
        
        self.add_widget(layout)
    
    def go_back(self, instance):
        self.manager.transition.direction = 'right'
        self.manager.current = 'greeting'
    
    def login(self, instance):
        username = self.username.text
        password = self.password.text
        
        if not username or not password:
            self.error_label.text = 'Please fill in all fields'
            return
        
        # Get MongoDB connection from app
        app = App.get_running_app()
        db = app.db
        
        # Check credentials
        user = db.users.find_one({
            'username': username,
            'password': password
        })
        
        if user:
            print("\nDebug - Login successful:")
            print(f"Username: {user['username']}")
            print(f"Barcode: {user.get('barcode', 'NO BARCODE')}")
            
            # Verify barcode format
            barcode = user.get('barcode')
            if barcode and len(barcode) == 13:
                # Verify check digit
                total = 0
                for i in range(12):
                    digit = int(barcode[i])
                    if i % 2 == 0:
                        total += digit
                    else:
                        total += digit * 3
                expected_check = (10 - (total % 10)) % 10
                actual_check = int(barcode[-1])
                
                if expected_check != actual_check:
                    print(f"Warning: Invalid barcode check digit. Expected {expected_check}, got {actual_check}")
                    # Optionally fix the barcode
                    fixed_barcode = barcode[:-1] + str(expected_check)
                    print(f"Fixing barcode from {barcode} to {fixed_barcode}")
                    barcode = fixed_barcode
                    # Update user in database
                    db.users.update_one(
                        {'_id': user['_id']},
                        {'$set': {'barcode': fixed_barcode}}
                    )
                    user['barcode'] = fixed_barcode
            
            # Store user info in app
            app.current_user = user
            
            # Generate barcode if user has one
            if 'barcode' in user:
                app.generate_barcode(user['barcode'])
            
            # Get current screen manager
            current_manager = self.manager
            
            # Update screens
            app.update_screens()
            
            # Restore screen manager reference
            self.manager = current_manager
            
            # Navigate based on user type
            if user.get('user_type') == 'individual':
                self.manager.current = 'all_items'
            else:
                self.manager.current = 'buy_items'
        else:
            self.error_label.text = 'Invalid username or password'

class RegisterScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'register'
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        # Back button
        back_btn = MDIconButton(
            icon="arrow-left",
            pos_hint={'left': 1},
            on_press=self.go_back
        )
        
        # Title
        title = Label(
            text="Create Account",
            halign="center",
            font_name="NunitoBlack",
            font_size="32sp",
            color=[0.298, 0.141, 0.114, 1],
            size_hint_y=None,
            height=dp(40)  # Reduced from 50 to 40
        )
        
        # Subtitle
        subtitle = Label(
            text="so you don't waste food",  # Changed text
            halign="center",
            color=[0.5, 0.5, 0.5, 1],
            font_name="PoppinsSemiBold",
            font_size="14sp",
            size_hint_y=None,
            height=dp(10)
        )
        
        # Registration fields
        self.username = MDTextField(
            hint_text="Username",
            helper_text="Enter your username",
            helper_text_mode="on_error",
            size_hint_x=0.9,
            pos_hint={'center_x': 0.5},
            line_color_normal=[0.298, 0.141, 0.114, 1],
            line_color_focus=[0.298, 0.141, 0.114, 1],
            text_color_focus=[0.298, 0.141, 0.114, 1]
        )
        
        self.password = MDTextField(
            hint_text="Password",
            helper_text="Enter your password",
            helper_text_mode="on_error",
            password=True,
            size_hint_x=0.9,
            pos_hint={'center_x': 0.5},
            line_color_normal=[0.298, 0.141, 0.114, 1],
            line_color_focus=[0.298, 0.141, 0.114, 1],
            text_color_focus=[0.298, 0.141, 0.114, 1]
        )
        
        self.confirm_password = MDTextField(
            hint_text="Confirm Password",
            helper_text="Confirm your password",
            helper_text_mode="on_error",
            password=True,
            size_hint_x=0.9,
            pos_hint={'center_x': 0.5},
            line_color_normal=[0.298, 0.141, 0.114, 1],
            line_color_focus=[0.298, 0.141, 0.114, 1],
            text_color_focus=[0.298, 0.141, 0.114, 1]
        )
        
        # User type selection
        self.user_type_btn = MDRaisedButton(
            text="User Type: Individual",
            size_hint=(0.8, None),
            height=dp(50),
            pos_hint={'center_x': 0.5},
            md_bg_color=[0.945, 0.957, 1, 1],  # Converted #F1F4FF to RGB
            text_color=[0, 0, 0, 1],  # Black text for better contrast
            on_press=self.toggle_user_type
        )
        self.current_type = 'individual'
        
        # Register button
        register_btn = MDFlatButton(
            text="Register",
            size_hint=(None, None),
            width=dp(300),
            height=dp(90),
            md_bg_color=[0.298, 0.141, 0.114, 1],
            text_color=[1, 1, 1, 1],
            theme_text_color="Custom",
            font_name="PoppinsSemiBold",
            ripple_color=[0, 0, 0, 0],
            _radius=dp(10),
            pos_hint={'center_x': 0.5},
            on_press=self.register
        )
        
        # Error message label
        self.error_label = MDLabel(
            text="",
            theme_text_color="Error",
            halign="center",
            size_hint_y=0.1
        )
        
        # Add widgets to layout
        layout.add_widget(back_btn)
        layout.add_widget(title)
        layout.add_widget(subtitle)
        layout.add_widget(self.username)
        layout.add_widget(self.password)
        layout.add_widget(self.confirm_password)
        layout.add_widget(self.user_type_btn)
        layout.add_widget(Widget())
        layout.add_widget(register_btn)
        layout.add_widget(self.error_label)
        
        self.add_widget(layout)
    
    def go_back(self, instance):
        self.manager.transition.direction = 'right'
        self.manager.current = 'greeting'
    
    def toggle_user_type(self, instance):
        self.current_type = 'business' if self.current_type == 'individual' else 'individual'
        self.user_type_btn.text = f"User Type: {self.current_type.capitalize()}"
    
    def register(self, instance):
        username = self.username.text
        password = self.password.text
        confirm_password = self.confirm_password.text
        
        if not username or not password or not confirm_password:
            self.error_label.text = 'Please fill in all fields'
            return
        
        if password != confirm_password:
            self.error_label.text = 'Passwords do not match'
            return
        
        # Get MongoDB connection from app
        db = App.get_running_app().db
        
        # Check if username already exists
        if db.users.find_one({'username': username}):
            self.error_label.text = 'Username already exists'
            return
        
        # Generate EAN-13 barcode
        import random
        while True:
            # Generate first 12 digits
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
            if not db.users.find_one({'barcode': barcode}):
                break
        
        # Create new user
        new_user = {
            'username': username,
            'password': password,  # In production, use hashed passwords!
            'user_type': self.current_type,
            'barcode': barcode,
            'created_at': datetime.utcnow()
        }
        
        try:
            result = db.users.insert_one(new_user)
            print(f"Debug - User created with barcode: {barcode}")
            
            # Verify the inserted user
            inserted_user = db.users.find_one({'_id': result.inserted_id})
            if inserted_user:
                print(f"Debug - Verified user in database:")
                print(f"Username: {inserted_user['username']}")
                print(f"Barcode: {inserted_user['barcode']}")
            
            self.go_to_login(None)
        except Exception as e:
            self.error_label.text = f'Error creating account: {str(e)}'
    
    def go_to_login(self, instance):
        self.manager.transition.direction = 'left'
        self.manager.current = 'login'

class ExpiryTrackerApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Register custom fonts
        from kivy.core.text import LabelBase
        import os
        
        # Print current directory and check if font file exists
        print("Current directory:", os.getcwd())
        font_path = "Fonts/Nunito-Black.ttf"
        print("Font exists:", os.path.exists(font_path))
        
        # Register Nunito-Black font
        LabelBase.register(
            name="NunitoBlack",  # Changed name to be more specific
            fn_regular=font_path
        )
        LabelBase.register(
            name="Poppins",
            fn_regular="Fonts/Poppins-Regular.ttf",
            fn_bold="Fonts/Poppins-Bold.ttf",
            fn_italic="Fonts/Poppins-Light.ttf"
        )
        LabelBase.register(
            name="PoppinsSemiBold",
            fn_regular="Fonts/Poppins-SemiBold.ttf"
        )
        self.current_user = None
        self.sm = None
        
        # Set window size
        Window.size = (360, 640)
        
        # Setup MongoDB connection
        connection_string = "mongodb+srv://majdsukkary472:Ny4Rtjg1bDtKzptn@cluster0.1x9tg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
        self.client = pymongo.MongoClient(connection_string, server_api=ServerApi('1'))
        self.db = self.client.expiry_tracker
    
    def get_user_barcode(self):
        if self.current_user and 'barcode' in self.current_user:
            barcode = self.current_user['barcode']
            print(f"Debug - Getting barcode for user {self.current_user['username']}: {barcode}")
            return barcode
        print("Debug - Using default barcode")
        return '123456789012'  # Default barcode
    
    def generate_barcode(self, barcode):
        if not os.path.exists(f"barcodes/barcode_{barcode}.png"):
            ean = EAN13(barcode, writer=ImageWriter())
            filename = f"barcodes/barcode_{barcode}"
            ean.save(filename)
    
    def update_screens(self):
        # Store current screen manager reference
        if not hasattr(self, 'sm'):
            return
        
        current_manager = self.sm
        current_screen = current_manager.current
        
        # Remove all screens but preserve the manager
        current_manager.clear_widgets()
        
        # Add login and register screens
        current_manager.add_widget(LoginScreen(name='login'))
        current_manager.add_widget(RegisterScreen(name='register'))
        
        # Add other screens
        current_manager.add_widget(UserTypeScreen(name='user_type'))
        current_manager.add_widget(AllItemsScreen(name='all_items'))
        current_manager.add_widget(AboutToExpireScreen(name='about_to_expire'))
        current_manager.add_widget(ExpiredItemsScreen(name='expired'))
        current_manager.add_widget(BuyItemsScreen(name='buy_items'))
        current_manager.add_widget(SellItemsScreen(name='sell_items'))
        current_manager.add_widget(PreferencesScreen(name='preferences'))
        current_manager.add_widget(BusinessExpiredScreen(name='business_expired'))
        
        # Restore current screen if possible
        if current_screen in [s.name for s in current_manager.screens]:
            current_manager.current = current_screen
    
    def set_user(self, user_type, barcode=None):
        if not self.current_user:
            print("Debug - No user logged in, cannot set user type")
            return
        
        self.current_user['user_type'] = user_type
        if barcode:
            self.current_user['barcode'] = barcode
        
        print(f"Debug - Set user type to {user_type} for {self.current_user['username']}")
        print(f"Debug - Current barcode: {self.current_user.get('barcode', 'NO BARCODE')}")
    
    def build(self):
        # Set theme and font
        self.theme_cls.primary_palette = "DeepPurple"
        self.theme_cls.theme_style = "Light"
        self.theme_cls.font_styles.update({
            "H5": ["Poppins", 24, False, 0.15],
            "H6": ["Poppins", 20, False, 0.15],
            "Subtitle1": ["Poppins", 16, False, 0.15],
            "Body1": ["Poppins", 16, False, 0.5],
            "Body2": ["Poppins", 14, False, 0.25],
            "Button": ["Poppins", 14, True, 1.25],
        })
        
        self.sm = MDScreenManager()
        
        # Add screens in new order
        self.sm.add_widget(GreetingScreen(name='greeting'))
        self.sm.add_widget(LoginScreen(name='login'))
        self.sm.add_widget(RegisterScreen(name='register'))
        self.sm.add_widget(UserTypeScreen(name='user_type'))
        self.sm.add_widget(AllItemsScreen(name='all_items'))
        self.sm.add_widget(AboutToExpireScreen(name='about_to_expire'))
        self.sm.add_widget(ExpiredItemsScreen(name='expired'))
        self.sm.add_widget(BuyItemsScreen(name='buy_items'))
        self.sm.add_widget(SellItemsScreen(name='sell_items'))
        self.sm.add_widget(PreferencesScreen(name='preferences'))
        self.sm.add_widget(BusinessExpiredScreen(name='business_expired'))
        
        return self.sm

if __name__ == '__main__':
    ExpiryTrackerApp().run()
