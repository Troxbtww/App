import pymongo
import sys
from datetime import datetime
import pytz
import requests

# MongoDB setup
MONGO_URI = "mongodb+srv://100067157:FvWkQrsqmihYSNFo@cluster0.boguv8r.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = pymongo.MongoClient(MONGO_URI)
db = client["qoot_bot"]
notifications_collection = db.get_collection("notifications")
users_collection = db["users"]

# Bot token for Telegram
BOT_TOKEN = "7933362470:AAEcf2GVqaxXFj2e0GF4aCXW3RHIw-6M3IM"

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
            print(f"Message sent to user {user_id}")
            return True
        else:
            print(f"Failed to send message: {result.get('description')}")
            return False
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

def display_menu():
    """Display the main menu options."""
    print("\n===== QOOT BOT ADMIN PANEL =====")
    print("1. View pending pickup requests")
    print("2. Mark request as completed")
    print("3. View all users")
    print("4. View user details")
    print("5. Send message to user")
    print("6. Exit")
    print("=" * 32)

def view_pending_requests():
    """View all pending pickup requests."""
    pending = list(notifications_collection.find({"status": "pending"}).sort("created_at", -1))
    
    if not pending:
        print("\nNo pending pickup requests found.")
        return
    
    print(f"\nFound {len(pending)} pending pickup requests:")
    print("-" * 80)
    
    for i, request in enumerate(pending, 1):
        request_type = request.get("type", "unknown")
        item_name = request.get("item_name", "Unknown Item")
        username = request.get("username", "Unknown User")
        pickup_date = request.get("pickup_date", "N/A")
        pickup_time = request.get("pickup_time", "N/A")
        created_at = request.get("created_at", datetime.now(pytz.UTC)).strftime("%Y-%m-%d %H:%M")
        
        print(f"{i}. {request_type.upper()} - {item_name}")
        print(f"   From: {username}")
        print(f"   Pickup: {pickup_date} at {pickup_time}")
        print(f"   Requested: {created_at}")
        print(f"   ID: {request['_id']}")
        
        # Show location details
        location = request.get("pickup_location", "Not provided")
        print(f"   Location: {location}")
        
        if "coordinates" in request:
            coords = request.get("coordinates", {})
            lat = coords.get("latitude", "N/A")
            lng = coords.get("longitude", "N/A")
            print(f"   GPS: {lat}, {lng}")
            print(f"   Maps Link: https://maps.google.com/?q={lat},{lng}")
        
        print("-" * 80)

def mark_request_completed():
    """Mark a pickup request as completed."""
    request_id = input("Enter the Request ID to mark as completed: ")
    
    try:
        # Try to convert to ObjectId if it's in that format
        from bson import ObjectId
        try:
            request_id_obj = ObjectId(request_id)
        except:
            # If not a valid ObjectId, use as string
            request_id_obj = request_id
        
        result = notifications_collection.update_one(
            {"_id": request_id_obj},
            {"$set": {"status": "completed", "completed_at": datetime.now(pytz.UTC)}}
        )
        
        if result.modified_count > 0:
            print(f"Request {request_id} marked as completed.")
        else:
            print(f"Request {request_id} not found or already completed.")
    except Exception as e:
        print(f"Error updating request: {e}")

def view_all_users():
    """View all registered users."""
    users = list(users_collection.find().sort("created_at", -1))
    
    if not users:
        print("\nNo users found.")
        return
    
    print(f"\nFound {len(users)} registered users:")
    print("-" * 80)
    
    for i, user in enumerate(users, 1):
        user_id = user.get("user_id", "N/A")
        username = user.get("username", "N/A")
        barcode = user.get("barcode", "N/A")
        points = user.get("points", 0)
        created_at = user.get("created_at", datetime.now(pytz.UTC)).strftime("%Y-%m-%d")
        
        print(f"{i}. {username}")
        print(f"   User ID: {user_id}")
        print(f"   Barcode: {barcode}")
        print(f"   Points: {points}")
        print(f"   Joined: {created_at}")
        print("-" * 80)

def view_user_details():
    """View detailed information about a specific user."""
    user_identifier = input("Enter User ID or barcode: ")
    
    # Try to find by user_id first
    try:
        user_id = int(user_identifier)
        user = users_collection.find_one({"user_id": user_id})
    except ValueError:
        # If not an integer, try finding by barcode
        user = users_collection.find_one({"barcode": user_identifier})
    
    if not user:
        print("User not found.")
        return
    
    print("\n===== USER DETAILS =====")
    print(f"Username: {user.get('username', 'N/A')}")
    print(f"User ID: {user.get('user_id', 'N/A')}")
    print(f"Barcode: {user.get('barcode', 'N/A')}")
    print(f"Points: {user.get('points', 0)}")
    print(f"Joined: {user.get('created_at', 'N/A')}")
    
    # Get user's items
    from bson import ObjectId
    items = list(db.items.find({"user_id": user.get("user_id")}))
    
    if items:
        print(f"\nUser has {len(items)} items:")
        for i, item in enumerate(items, 1):
            name = item.get("name", "Unknown Item")
            price = item.get("price", 0)
            exp_date = item.get("expiration_date", "N/A")
            if isinstance(exp_date, datetime):
                exp_date = exp_date.strftime("%Y-%m-%d")
            
            print(f"{i}. {name} - {price} AED (Expires: {exp_date})")
    else:
        print("\nUser has no items.")
    
    # Get user's notifications
    notifications = list(notifications_collection.find({"user_id": user.get("user_id")}))
    
    if notifications:
        print(f"\nUser has {len(notifications)} pickup requests:")
        for i, notif in enumerate(notifications, 1):
            req_type = notif.get("type", "unknown")
            item_name = notif.get("item_name", "Unknown Item")
            status = notif.get("status", "pending")
            created_at = notif.get("created_at", "N/A")
            if isinstance(created_at, datetime):
                created_at = created_at.strftime("%Y-%m-%d %H:%M")
            
            print(f"{i}. {req_type.upper()} - {item_name} - Status: {status.upper()} ({created_at})")
    else:
        print("\nUser has no pickup requests.")

def send_message_to_user():
    """Send a direct message to a user via Telegram."""
    user_identifier = input("Enter User ID or barcode: ")
    
    # Try to find by user_id first
    try:
        user_id = int(user_identifier)
        user = users_collection.find_one({"user_id": user_id})
    except ValueError:
        # If not an integer, try finding by barcode
        user = users_collection.find_one({"barcode": user_identifier})
    
    if not user:
        print("User not found.")
        return
    
    print(f"\nSending message to: {user.get('username', 'Unknown User')} (ID: {user.get('user_id')})")
    message = input("Enter your message: ")
    
    if not message:
        print("Message cannot be empty. Operation cancelled.")
        return
    
    # Add formatting options
    print("\nFormatting options:")
    print("1. Send as plain text")
    print("2. Send as HTML (bold, italic, etc.)")
    format_choice = input("Choose formatting (1-2): ")
    
    if format_choice == "2":
        print("\nHTML formatting examples:")
        print("- Bold: <b>text</b>")
        print("- Italic: <i>text</i>")
        print("- Underline: <u>text</u>")
        print("- Code: <code>text</code>")
        message = input("Enter your HTML-formatted message: ")
    
    # Confirm before sending
    print(f"\nMessage to be sent:\n{message}")
    confirm = input("Send this message? (y/n): ")
    
    if confirm.lower() != "y":
        print("Message sending cancelled.")
        return
    
    # Send the message
    success = send_telegram_message(user.get('user_id'), message)
    
    if success:
        print(f"Message successfully sent to {user.get('username', 'user')}.")
        
        # Log the message in the database
        try:
            message_log = {
                "user_id": user.get('user_id'),
                "username": user.get('username'),
                "message": message,
                "sent_at": datetime.now(pytz.UTC),
                "sent_by": "admin"
            }
            
            if 'messages' not in db.list_collection_names():
                db.create_collection('messages')
            
            db.messages.insert_one(message_log)
        except Exception as e:
            print(f"Warning: Failed to log message in database: {e}")
    else:
        print(f"Failed to send message to {user.get('username', 'user')}.")

def main():
    """Main function to run the admin panel."""
    print("Welcome to the Qoot Bot Admin Panel!")
    
    while True:
        display_menu()
        choice = input("Enter your choice (1-6): ")
        
        if choice == "1":
            view_pending_requests()
        elif choice == "2":
            mark_request_completed()
        elif choice == "3":
            view_all_users()
        elif choice == "4":
            view_user_details()
        elif choice == "5":
            send_message_to_user()
        elif choice == "6":
            print("Exiting admin panel. Goodbye!")
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 6.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAdmin panel closed.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Close MongoDB connection
        client.close() 