import json
import os
import sys
from datetime import datetime
import pymongo
import pytz
import requests
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
from PIL import Image, ImageTk
import threading
import barcode
from barcode.writer import ImageWriter
from io import BytesIO

# Check if the product catalog exists
PRODUCT_BARCODES_DIR = "product_barcodes"
CATALOG_FILE = f"{PRODUCT_BARCODES_DIR}/product_catalog.json"

# MongoDB setup
MONGO_URI = "mongodb+srv://100067157:FvWkQrsqmihYSNFo@cluster0.boguv8r.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = pymongo.MongoClient(MONGO_URI)
db = client["qoot_bot"]
users_collection = db["users"]
items_collection = db["items"]

# Bot token for Telegram
BOT_TOKEN = "7933362470:AAEcf2GVqaxXFj2e0GF4aCXW3RHIw-6M3IM"

class Logger:
    """Simple logger class that writes to both console and a tkinter text widget."""
    
    def __init__(self, text_widget=None):
        self.text_widget = text_widget
    
    def set_text_widget(self, text_widget):
        self.text_widget = text_widget
    
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {level}: {message}"
        print(formatted_message)
        
        if self.text_widget:
            self.text_widget.configure(state="normal")
            self.text_widget.insert(tk.END, formatted_message + "\n")
            self.text_widget.see(tk.END)
            self.text_widget.configure(state="disabled")

# Create a global logger
logger = Logger()

def send_telegram_message(user_id, message):
    """Send a message to a user via Telegram bot API."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": user_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, data=data)
        result = response.json()
        if result.get("ok"):
            logger.log(f"Message sent to user {user_id}")
        else:
            logger.log(f"Failed to send message: {result.get('description')}", "ERROR")
        return result
    except Exception as e:
        logger.log(f"Error sending message: {e}", "ERROR")
        return None

def find_user_by_barcode(barcode):
    """Find a user by their barcode."""
    # If it's a 13-digit barcode (with check digit), extract the first 12 digits
    if len(barcode) == 13 and barcode.isdigit():
        barcode = barcode[:12]
    
    user = users_collection.find_one({"barcode": barcode})
    return user

def add_item_to_user(user_id, item_data):
    """Add an item to a user's inventory in MongoDB."""
    # Convert expiration date string to datetime
    exp_date = datetime.strptime(item_data["expiration_date"], "%Y-%m-%d")
    exp_date = pytz.UTC.localize(exp_date) if exp_date.tzinfo is None else exp_date
    
    # Check if the item with the same name and expiration date already exists
    existing_item = items_collection.find_one({
        "user_id": user_id,
        "name": item_data["name"],
        "expiration_date": exp_date
    })
    
    if existing_item:
        # Increment quantity if item already exists
        quantity = existing_item.get("quantity", 1) + 1
        result = items_collection.update_one(
            {"_id": existing_item["_id"]},
            {"$set": {"quantity": quantity}}
        )
        return existing_item["_id"]
    else:
        # Create new item with quantity = 1
        item = {
            "user_id": user_id,
            "name": item_data["name"],
            "price": float(item_data["price"]),
            "expiration_date": exp_date,
            "added_at": datetime.now(pytz.UTC),
            "quantity": 1
        }
        
        result = items_collection.insert_one(item)
        return result.inserted_id

def load_product_catalog():
    """Load the product catalog from JSON file."""
    if not os.path.exists(CATALOG_FILE):
        logger.log(f"Error: Product catalog not found at {CATALOG_FILE}", "ERROR")
        messagebox.showerror("Error", f"Product catalog not found at {CATALOG_FILE}\nPlease run generate_test_barcodes.py first.")
        return {}
    
    with open(CATALOG_FILE, "r") as f:
        catalog = json.load(f)
    
    # Index products by barcode for quick lookup
    barcode_to_product = {product["barcode"]: product for product in catalog}
    return barcode_to_product

class QootScannerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Qoot Bot Product Scanner")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # Set theme and style
        self.style = ttk.Style()
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TLabel", background="#f0f0f0", font=("Arial", 11))
        self.style.configure("TButton", font=("Arial", 11))
        self.style.configure("Header.TLabel", font=("Arial", 16, "bold"))
        self.style.configure("SubHeader.TLabel", font=("Arial", 13, "bold"))
        
        # Load product catalog
        self.catalog = load_product_catalog()
        
        # Setup variables
        self.current_user = None
        self.cart = []
        
        # Create main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create and configure UI components
        self._create_header()
        self._create_user_section()
        self._create_product_section()
        self._create_cart_section()
        self._create_log_section()
        
        # Update the logger
        logger.set_text_widget(self.log_text)
        
        # Log startup
        logger.log(f"Application started. Loaded {len(self.catalog)} products from catalog.")
        
        # Setup key binding for barcode entry
        self.root.bind('<Return>', self._on_barcode_enter)
        
        # Set initial focus to customer barcode entry
        self.customer_barcode_entry.focus_set()
        
        # Make sure MongoDB connection is closed when app is closed
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_header(self):
        """Create the header section with title and logo."""
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Title label
        title_label = ttk.Label(header_frame, text="Qoot Bot Product Scanner", style="Header.TLabel")
        title_label.pack(side=tk.LEFT, padx=5)
        
        # Version info
        version_label = ttk.Label(header_frame, text="v1.0")
        version_label.pack(side=tk.RIGHT, padx=5)
    
    def _create_user_section(self):
        """Create the user identification section."""
        user_frame = ttk.LabelFrame(self.main_frame, text="Customer Identification", padding="10")
        user_frame.pack(fill=tk.X, pady=(0, 10))
        
        # User barcode entry
        ttk.Label(user_frame, text="Scan Customer Barcode:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.customer_barcode_var = tk.StringVar()
        self.customer_barcode_entry = ttk.Entry(user_frame, textvariable=self.customer_barcode_var, width=20)
        self.customer_barcode_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(user_frame, text="Connect", command=self._connect_user).grid(row=0, column=2, padx=5, pady=5)
        
        # User info display
        self.user_info_var = tk.StringVar(value="No user connected")
        user_info_label = ttk.Label(user_frame, textvariable=self.user_info_var)
        user_info_label.grid(row=1, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)
    
    def _create_product_section(self):
        """Create the product scanning section."""
        product_frame = ttk.LabelFrame(self.main_frame, text="Product Scanning", padding="10")
        product_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Product barcode entry
        ttk.Label(product_frame, text="Scan Product Barcode:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.barcode_var = tk.StringVar()
        self.barcode_entry = ttk.Entry(product_frame, textvariable=self.barcode_var, width=20)
        self.barcode_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Scan button
        ttk.Button(product_frame, text="Add to Cart", command=self._scan_product).grid(row=0, column=2, padx=5, pady=5)
        
        # Product catalog button
        ttk.Button(product_frame, text="Show Product Catalog", command=self._show_catalog).grid(row=0, column=3, padx=5, pady=5)
    
    def _create_cart_section(self):
        """Create the shopping cart section."""
        cart_frame = ttk.LabelFrame(self.main_frame, text="Shopping Cart", padding="10")
        cart_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create Treeview for cart items
        columns = ("Product", "Price", "Quantity", "Expiry Date", "Status")
        self.cart_tree = ttk.Treeview(cart_frame, columns=columns, show="headings", height=10)
        
        # Set column headings
        for col in columns:
            self.cart_tree.heading(col, text=col)
            self.cart_tree.column(col, width=100)
        
        # Better column widths
        self.cart_tree.column("Product", width=300)
        self.cart_tree.column("Quantity", width=70)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(cart_frame, orient=tk.VERTICAL, command=self.cart_tree.yview)
        self.cart_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack tree and scrollbar
        self.cart_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Buttons frame
        buttons_frame = ttk.Frame(self.main_frame)
        buttons_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Cart buttons
        ttk.Button(buttons_frame, text="Remove Selected", command=self._remove_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Clear Cart", command=self._clear_cart).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Update Quantity", command=self._update_quantity).pack(side=tk.LEFT, padx=5)
        
        # Total price label
        self.total_var = tk.StringVar(value="Total: 0.00 AED")
        total_label = ttk.Label(buttons_frame, textvariable=self.total_var, style="SubHeader.TLabel")
        total_label.pack(side=tk.RIGHT, padx=5)
        
        # Checkout button
        ttk.Button(buttons_frame, text="Checkout", command=self._checkout).pack(side=tk.RIGHT, padx=5)
    
    def _create_log_section(self):
        """Create the log section."""
        log_frame = ttk.LabelFrame(self.main_frame, text="Activity Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # Log text area
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.configure(state="disabled")
    
    def _connect_user(self):
        """Connect to a user by barcode."""
        barcode = self.customer_barcode_var.get().strip()
        
        if not barcode:
            messagebox.showwarning("Warning", "Please enter a barcode.")
            return
        
        user = find_user_by_barcode(barcode)
        
        if not user:
            logger.log(f"User not found for barcode: {barcode}", "ERROR")
            messagebox.showerror("Error", "User not found. Please check the barcode.")
            return
        
        self.current_user = user
        username = user.get('username', 'Unknown')
        user_id = user.get('user_id', 'Unknown')
        
        # Update UI
        self.user_info_var.set(f"Connected to: {username} (ID: {user_id})")
        logger.log(f"Connected to user: {username} (ID: {user_id})")
        
        # Clear cart when changing users
        self._clear_cart()
        
        # Focus on product barcode entry
        self.barcode_entry.focus_set()
    
    def _scan_product(self):
        """Scan a product and add it to the cart."""
        if not self.current_user:
            messagebox.showwarning("Warning", "Please connect to a user first.")
            return
        
        barcode = self.barcode_var.get().strip()
        
        if not barcode:
            messagebox.showwarning("Warning", "Please enter a barcode.")
            return
        
        # Find product by barcode
        product = self.catalog.get(barcode)
        
        if not product:
            logger.log(f"Product not found for barcode: {barcode}", "ERROR")
            messagebox.showerror("Error", "Product not found. Please check the barcode.")
            return
        
        # Check if product is already in cart
        for idx, item in enumerate(self.cart):
            if item['barcode'] == barcode:
                # Increment quantity
                if 'quantity' not in item:
                    item['quantity'] = 1
                item['quantity'] += 1
                
                # Update the treeview
                self.cart_tree.item(str(idx), values=(
                    item['name'],
                    f"{item['price']} AED",
                    item['quantity'],
                    self._format_date(item['expiration_date']),
                    "Expired" if item['expired'] else ("Expiring Soon" if self._is_expiring_soon(item['expiration_date']) else "Good")
                ))
                
                logger.log(f"Increased quantity for {item['name']} to {item['quantity']}")
                self.barcode_var.set("")  # Clear the barcode entry
                self._update_total()
                self.barcode_entry.focus_set()
                return
                
        # Clone product to add to cart
        cart_item = product.copy()
        cart_item['quantity'] = 1
        self.cart.append(cart_item)
        
        # Determine status based on expiration date
        status = "Expired" if cart_item['expired'] else ("Expiring Soon" if self._is_expiring_soon(cart_item['expiration_date']) else "Good")
        
        # Add product to the treeview
        self.cart_tree.insert("", tk.END, iid=str(len(self.cart)-1), values=(
            cart_item['name'],
            f"{cart_item['price']} AED",
            cart_item['quantity'],
            self._format_date(cart_item['expiration_date']),
            status
        ))
        
        logger.log(f"Added to cart: {cart_item['name']} - {cart_item['price']} AED (Expires: {cart_item['expiration_date']})")
        
        # Clear the barcode entry and update total
        self.barcode_var.set("")
        self._update_total()
        self.barcode_entry.focus_set()
    
    def _show_catalog(self):
        """Show the product catalog in a new window."""
        catalog_window = tk.Toplevel(self.root)
        catalog_window.title("Product Catalog")
        catalog_window.geometry("800x600")
        
        # Catalog frame
        frame = ttk.Frame(catalog_window, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Create Treeview
        columns = ("Barcode", "Product", "Price", "Expiration Date", "Status")
        catalog_tree = ttk.Treeview(frame, columns=columns, show="headings", height=20)
        
        # Set column headings
        for col in columns:
            catalog_tree.heading(col, text=col)
            catalog_tree.column(col, width=100)
        
        # Better column widths
        catalog_tree.column("Barcode", width=150)
        catalog_tree.column("Product", width=200)
        
        # Populate with catalog data
        for barcode, product in self.catalog.items():
            # Determine if product is expired
            exp_date = datetime.strptime(product["expiration_date"], "%Y-%m-%d")
            is_expired = exp_date.date() < datetime.now().date()
            status = "EXPIRED" if is_expired else "OK"
            
            values = (
                barcode,
                product["name"],
                f"{product['price']} AED",
                self._format_date(product["expiration_date"]),
                status
            )
            catalog_tree.insert("", tk.END, values=values)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=catalog_tree.yview)
        catalog_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack tree and scrollbar
        catalog_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Double-click to select product
        def on_double_click(event):
            item = catalog_tree.selection()[0]
            barcode = catalog_tree.item(item, "values")[0]
            self.barcode_var.set(barcode)
            catalog_window.destroy()
            self._scan_product()
        
        catalog_tree.bind("<Double-1>", on_double_click)
        
        # Add button to close window
        ttk.Button(
            catalog_window, 
            text="Close", 
            command=catalog_window.destroy
        ).pack(pady=10)
    
    def _update_total(self):
        """Update the total price based on cart items."""
        total = 0.0
        for item in self.cart:
            quantity = item.get('quantity', 1)
            total += float(item['price']) * quantity
        
        self.total_var.set(f"Total: {total:.2f} AED")
    
    def _remove_selected(self):
        """Remove selected item from cart."""
        selected_items = self.cart_tree.selection()
        
        if not selected_items:
            messagebox.showinfo("Info", "Please select an item to remove.")
            return
        
        # Get the indices of selected items
        indices = []
        for item_id in selected_items:
            item_index = self.cart_tree.index(item_id)
            indices.append(item_index)
        
        # Remove from cart (in reverse order to avoid index shifting)
        for index in sorted(indices, reverse=True):
            del self.cart[index]
        
        # Remove from treeview
        for item_id in selected_items:
            self.cart_tree.delete(item_id)
        
        # Update total
        self._update_total()
        logger.log("Removed selected items from cart")
    
    def _clear_cart(self):
        """Clear the shopping cart."""
        self.cart = []
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)
        self._update_total()
        logger.log("Cart cleared")
    
    def _checkout(self):
        """Process checkout and add items to user's account."""
        if not self.current_user:
            messagebox.showwarning("Warning", "Please connect to a user first.")
            return
        
        if not self.cart:
            messagebox.showinfo("Info", "Cart is empty.")
            return
        
        # Confirm checkout
        user_id = self.current_user["user_id"]
        username = self.current_user.get('username', 'Unknown')
        
        # Calculate total properly considering quantities
        total = 0
        item_count = 0
        for item in self.cart:
            quantity = item.get('quantity', 1)
            total += float(item['price']) * quantity
            item_count += quantity
        
        message = f"Add {item_count} items to {username}'s account?\nTotal: {total:.2f} AED"
        confirm = messagebox.askyesno("Confirm Checkout", message)
        
        if not confirm:
            return
        
        # Process checkout in a separate thread to keep UI responsive
        threading.Thread(target=self._process_checkout, daemon=True).start()
    
    def _process_checkout(self):
        """Process checkout in background thread."""
        user_id = self.current_user["user_id"]
        
        # Log start of checkout
        logger.log(f"Processing checkout for user {user_id}...")
        
        # Prepare a single message with all items
        total = 0
        items_text = []
        
        # Add items to user's account and build the message
        for item in self.cart:
            try:
                # Get quantity (default to 1 if not specified)
                quantity = item.get('quantity', 1)
                
                # Add to MongoDB - repeat for each quantity to handle consolidation logic
                for _ in range(quantity):
                    item_id = add_item_to_user(user_id, item)
                
                # Add item info to the message
                price = float(item['price'])
                total += price * quantity
                
                # Format expiration date
                exp_date = self._format_date(item['expiration_date'])
                
                # Format the item entry
                item_text = (
                    f"• <b>{item['name']}</b>\n"
                    f"  Quantity: {quantity}\n"
                    f"  Unit Price: {price} AED (Total: {price * quantity:.2f} AED)\n"
                    f"  Expiration Date: {exp_date}"
                )
                items_text.append(item_text)
                
                logger.log(f"Added: {item['name']} x{quantity} (ID: {item_id})")
            except Exception as e:
                logger.log(f"Error adding item: {e}", "ERROR")
        
        # Send a single Telegram notification with all items
        if items_text:
            message = (
                f"<b>🛒 New Items Added to Your Inventory</b>\n\n"
                f"{len(items_text)} items have been added:\n\n"
                f"{chr(10).join(items_text)}\n\n"
                f"<b>Total: {total:.2f} AED</b>"
            )
            
            send_telegram_message(user_id, message)
            logger.log(f"Sent notification with {len(items_text)} items")
        
        # Clear cart
        self.root.after(0, self._clear_cart_after_checkout)
    
    def _clear_cart_after_checkout(self):
        """Clear cart after checkout (called from main thread)."""
        self._clear_cart()
        messagebox.showinfo("Checkout Complete", "Items have been added to user's account.\nCheck Telegram bot for notifications.")
    
    def _on_barcode_enter(self, event):
        """Handle Return key press in barcode entry."""
        if event.widget == self.customer_barcode_entry:
            self._connect_user()
        elif event.widget == self.barcode_entry:
            self._scan_product()
    
    def _on_closing(self):
        """Handle window closing."""
        try:
            client.close()
            logger.log("MongoDB connection closed")
        except:
            pass
        self.root.destroy()

    def _is_expiring_soon(self, date_str):
        """Check if a product is expiring soon (within 14 days)."""
        try:
            exp_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            today = datetime.now().date()
            return (exp_date - today).days <= 14 and (exp_date - today).days >= 0
        except:
            return False
            
    def _update_quantity(self):
        """Update the quantity of a selected item."""
        selected = self.cart_tree.selection()
        if not selected:
            messagebox.showinfo("Information", "Please select an item to update its quantity.")
            return
            
        # Get the selected item
        item_id = selected[0]
        item_index = int(item_id)
        
        # Get current quantity
        current_qty = self.cart[item_index].get('quantity', 1)
        
        # Ask for new quantity
        new_qty = tk.simpledialog.askinteger("Update Quantity", 
                                            f"Current quantity: {current_qty}\nEnter new quantity:",
                                            initialvalue=current_qty,
                                            minvalue=1)
        
        if new_qty is None:  # User canceled
            return
            
        # Update quantity
        self.cart[item_index]['quantity'] = new_qty
        
        # Update treeview
        values = list(self.cart_tree.item(item_id, 'values'))
        values[2] = new_qty  # Update quantity column
        self.cart_tree.item(item_id, values=values)
        
        logger.log(f"Updated quantity for {self.cart[item_index]['name']} to {new_qty}")
        self._update_total()

    def _format_date(self, date_str):
        """Format date from YYYY-MM-DD to DD-MM-YYYY."""
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.strftime("%d-%m-%Y")
        except:
            return date_str

def main():
    """Main function to start the GUI application."""
    try:
        root = tk.Tk()
        app = QootScannerGUI(root)
        root.mainloop()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Ensure MongoDB connection is closed
        client.close()

if __name__ == "__main__":
    main() 