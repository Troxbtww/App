import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters
from datetime import datetime, timedelta
import pymongo
from bson import ObjectId
import random
import string
import pytz
import barcode
from barcode.writer import ImageWriter
from io import BytesIO

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants for conversation states
PICKUP_DATE, PICKUP_TIME, PICKUP_LOCATION, LISTING_PRICE = range(4)
DONATE_QUANTITY, LIST_QUANTITY, DIGEST_QUANTITY, DELETE_QUANTITY = range(4, 8)  # New states for quantity input

# Admin mode states
ADMIN_MENU, ADMIN_VIEW_REQUESTS, ADMIN_MARK_COMPLETED, ADMIN_VIEW_USER, ADMIN_SEND_MESSAGE = range(10, 15)

# Admin ID
ADMIN_ID = 1201693179

# MongoDB setup
MONGO_URI = "mongodb+srv://100067157:FvWkQrsqmihYSNFo@cluster0.boguv8r.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = pymongo.MongoClient(MONGO_URI)
db = client["qoot_bot"]
users_collection = db["users"]
items_collection = db["items"]
marketplace_collection = db["marketplace"]

# Path to barcode images
BARCODE_PATH = "barcodes/"
os.makedirs(BARCODE_PATH, exist_ok=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    user = update.effective_user
    user_id = user.id
    username = user.username if user.username else user.first_name
    
    # Check if user already exists in database
    user_data = users_collection.find_one({"user_id": user_id})
    
    if not user_data:
        # Generate a random barcode number (12 digits)
        barcode_number = ''.join(random.choices(string.digits, k=12))
        
        # Create a new user record
        user_data = {
            "user_id": user_id,
            "username": username,
            "barcode": barcode_number,
            "points": 0,
            "created_at": datetime.now(pytz.UTC)
        }
        users_collection.insert_one(user_data)
    else:
        barcode_number = user_data['barcode']
    
    # Create and send welcome message
    await update.message.reply_text(
        f"Welcome to Qoot Bot, {username}! We're on a mission to reduce food waste."
    )
    
    # Generate barcode image
    try:
        # EAN13 needs exactly 12 digits (the 13th is a check digit)
        ean = barcode.get('ean13', barcode_number, writer=ImageWriter())
        
        # Get the full 13-digit number including the check digit
        full_barcode = ean.get_fullcode()
        
        # Save the barcode to a BytesIO object
        buffer = BytesIO()
        ean.write(buffer)
        buffer.seek(0)
        
        # Create a filename for the user
        barcode_filename = f"{user_id}_barcode.png"
        barcode_path = os.path.join(BARCODE_PATH, barcode_filename)
        
        # Save to file for future reference
        with open(barcode_path, 'wb') as f:
            f.write(buffer.getvalue())
        
        # Reset buffer for sending
        buffer.seek(0)
        
        # Unpin all previous messages
        try:
            # Get chat information including pinned message
            chat_info = await context.bot.get_chat(update.effective_chat.id)
            
            # If there's a pinned message, unpin it
            if chat_info.pinned_message:
                await context.bot.unpin_all_chat_messages(chat_id=update.effective_chat.id)
                logger.info(f"Unpinned all previous messages for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to unpin previous messages: {e}")
        
        # Send the barcode image
        pinned_message = await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=buffer,
            caption=f"Your Qoot Bot Barcode: {full_barcode}\n\nShow this barcode to the cashier when making purchases."
        )
        
    except Exception as e:
        logger.error(f"Failed to generate barcode: {e}")
        # Fallback to text if image generation fails
        pinned_message = await update.message.reply_text(
            f"User Barcode: {barcode_number}\n\nShow this barcode to the cashier when making purchases."
        )
    
    # Pin the message with the barcode
    await context.bot.pin_chat_message(
        chat_id=update.effective_chat.id,
        message_id=pinned_message.message_id
    )
    
    # Create keyboard buttons - special case for admin
    if user_id == ADMIN_ID:
        keyboard = [
            [KeyboardButton("About to Expire"), KeyboardButton("Expired")],
            [KeyboardButton("Marketplace"), KeyboardButton("Rewards")],
            [KeyboardButton("⚙️ Admin Panel")]
        ]
    else:
        keyboard = [
            [KeyboardButton("About to Expire"), KeyboardButton("Expired")],
            [KeyboardButton("Marketplace"), KeyboardButton("Rewards")]
        ]
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "What would you like to do?",
        reply_markup=reply_markup
    )

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin version of the start command."""
    keyboard = [
        [KeyboardButton("👤 Users"), KeyboardButton("📦 Requests")],
        [KeyboardButton("📊 Statistics"), KeyboardButton("📝 Messages")],
        [KeyboardButton("🛒 Marketplace Admin")],
        [KeyboardButton("🔙 Return to User Mode")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"Welcome to Qoot Bot Admin Panel!\n\n"
        f"Select an option below or use the following commands:\n"
        f"/admin - Show admin menu\n"
        f"/requests - View pending requests\n"
        f"/users - View all users\n"
        f"/stats - View system statistics\n"
        f"/user <id or barcode> - View specific user details\n"
        f"/marketplace - Manage marketplace listings",
        reply_markup=reply_markup
    )

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the admin menu."""
    user_id = update.effective_user.id
    
    # Verify this is the admin
    if user_id != ADMIN_ID:
        await update.message.reply_text("Sorry, this command is only available for administrators.")
        return
    
    await admin_start(update, context)

async def admin_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show pending pickup requests."""
    user_id = update.effective_user.id
    
    # Verify this is the admin
    if user_id != ADMIN_ID:
        await update.message.reply_text("Sorry, this command is only available for administrators.")
        return
    
    # Get pending requests from database
    try:
        pending = list(db.notifications.find({"status": "pending"}).sort("requested_at", -1).limit(10))
        
        if not pending:
            await update.message.reply_text("No pending pickup requests found.")
            return
        
        await update.message.reply_text(f"Found {len(pending)} pending requests. Showing latest 10:")
        
        for request in pending:
            request_type = request.get("type", "unknown")
            item_name = request.get("item_name", "Unknown Item")
            username = request.get("username", "Unknown User")
            requester_id = request.get("user_id", None)
            pickup_date = request.get("pickup_date", "N/A")
            pickup_time = request.get("pickup_time", "N/A")
            location = request.get("pickup_location", "Not provided")
            has_location_file = request.get("has_location_file", False)
            
            # Format time slot if it's in the old format
            if pickup_time == "08:00-12:00":
                pickup_time = "08:00 AM - 12:00 PM"
            elif pickup_time == "12:00-18:00":
                pickup_time = "12:00 PM - 06:00 PM"
            
            # Check if location is in old format (without link or with wrong format)
            if has_location_file and "coordinates" in request and ("View on Map" not in location or "Coordinates:" in location):
                coords = request.get("coordinates", {})
                latitude = coords.get("latitude")
                longitude = coords.get("longitude")
                
                if latitude and longitude:
                    # Create a Google Maps link
                    maps_link = f"https://maps.google.com/maps?q={latitude},{longitude}"
                    location = f"<a href='{maps_link}'>View on Map</a>"
            
            # Create user contact link
            user_contact = f"👤 From: {username}"
            if requester_id:
                user_contact += f" - <a href='tg://user?id={requester_id}'>Contact directly</a>"
            
            message = (
                f"📦 <b>{request_type.upper()}</b> - {item_name}\n"
                f"{user_contact}\n"
                f"📅 Pickup: {pickup_date} at {pickup_time}\n"
                f"📍 Location: {location}\n\n"
                f"To mark as completed: /complete_{request['_id']}"
            )
            
            await update.message.reply_text(message, parse_mode="HTML")
    
    except Exception as e:
        logger.error(f"Error retrieving pending requests: {e}")
        await update.message.reply_text(f"Error retrieving requests: {str(e)}")

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all users."""
    user_id = update.effective_user.id
    
    # Verify this is the admin
    if user_id != ADMIN_ID:
        await update.message.reply_text("Sorry, this command is only available for administrators.")
        return
    
    # Get users from database
    try:
        users = list(users_collection.find().sort("created_at", -1).limit(10))
        
        if not users:
            await update.message.reply_text("No users found.")
            return
        
        await update.message.reply_text(f"Found {len(users)} users. Showing latest 10:")
        
        for user in users:
            username = user.get("username", "N/A")
            user_telegram_id = user.get("user_id", "N/A")
            barcode = user.get("barcode", "N/A")
            points = user.get("points", 0)
            
            message = (
                f"👤 <b>{username}</b>\n"
                f"🆔 ID: <code>{user_telegram_id}</code>\n"
                f"🔢 Barcode: <code>{barcode}</code>\n"
                f"🎯 Points: {points}\n\n"
                f"To view details: /user_{user_telegram_id}\n"
                f"To message user: /msg_{user_telegram_id}"
            )
            
            await update.message.reply_text(message, parse_mode="HTML")
    
    except Exception as e:
        logger.error(f"Error retrieving users: {e}")
        await update.message.reply_text(f"Error retrieving users: {str(e)}")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show system statistics."""
    user_id = update.effective_user.id
    
    # Verify this is the admin
    if user_id != ADMIN_ID:
        await update.message.reply_text("Sorry, this command is only available for administrators.")
        return
    
    # Collect statistics
    try:
        total_users = users_collection.count_documents({})
        total_items = db.items.count_documents({})
        total_requests = db.notifications.count_documents({})
        pending_requests = db.notifications.count_documents({"status": "pending"})
        completed_requests = db.notifications.count_documents({"status": "completed"})
        
        # Calculate about to expire and expired items
        now = datetime.now(pytz.UTC)
        two_weeks_later = now + timedelta(days=14)
        
        about_to_expire = db.items.count_documents({
            "expiration_date": {
                "$gt": now,
                "$lte": two_weeks_later
            }
        })
        
        expired = db.items.count_documents({
            "expiration_date": {"$lte": now}
        })
        
        message = (
            f"📊 <b>QOOT BOT STATISTICS</b>\n\n"
            f"👥 <b>Users:</b> {total_users}\n"
            f"📦 <b>Total Items:</b> {total_items}\n"
            f"⚠️ <b>About to Expire:</b> {about_to_expire}\n"
            f"⏰ <b>Expired:</b> {expired}\n\n"
            f"🔄 <b>Pickup Requests:</b>\n"
            f"  • Total: {total_requests}\n"
            f"  • Pending: {pending_requests}\n"
            f"  • Completed: {completed_requests}\n"
        )
        
        await update.message.reply_text(message, parse_mode="HTML")
    
    except Exception as e:
        logger.error(f"Error retrieving statistics: {e}")
        await update.message.reply_text(f"Error retrieving statistics: {str(e)}")

async def admin_user_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show details for a specific user."""
    admin_id = update.effective_user.id
    
    # Verify this is the admin
    if admin_id != ADMIN_ID:
        await update.message.reply_text("Sorry, this command is only available for administrators.")
        return
    
    # Check if user identifier was provided
    args = context.args
    
    if not args:
        # Check if command is in the format /user_123456
        command_parts = update.message.text.split('_', 1)
        if len(command_parts) == 2 and command_parts[0] == '/user':
            user_identifier = command_parts[1]
        else:
            await update.message.reply_text("Please provide a user ID or barcode.\nUsage: /user <id or barcode>")
            return
    else:
        user_identifier = args[0]
    
    # Try to find the user
    try:
        # Try by user_id first
        try:
            user_id = int(user_identifier)
            user = users_collection.find_one({"user_id": user_id})
        except ValueError:
            # If not an integer, try by barcode
            user = users_collection.find_one({"barcode": user_identifier})
        
        if not user:
            await update.message.reply_text(f"User not found with ID/barcode: {user_identifier}")
            return
        
        # Get user's items
        items = list(db.items.find({"user_id": user.get("user_id")}).limit(10))
        
        # Get user's notifications
        notifications = list(db.notifications.find({"user_id": user.get("user_id")}).limit(10))
        
        # Format user details
        username = user.get("username", "N/A")
        user_id = user.get("user_id", "N/A")
        barcode = user.get("barcode", "N/A")
        points = user.get("points", 0)
        created_at = user.get("created_at", datetime.now(pytz.UTC)).strftime("%Y-%m-%d")
        
        message = (
            f"👤 <b>USER DETAILS</b>\n\n"
            f"Name: <b>{username}</b>\n"
            f"ID: <code>{user_id}</code>\n"
            f"Barcode: <code>{barcode}</code>\n"
            f"Points: {points}\n"
            f"Joined: {created_at}\n\n"
        )
        
        if items:
            message += f"📦 <b>ITEMS ({len(items)})</b>\n"
            for i, item in enumerate(items[:5], 1):
                name = item.get("name", "Unknown")
                exp_date = item.get("expiration_date", "N/A")
                if isinstance(exp_date, datetime):
                    exp_date = exp_date.strftime("%Y-%m-%d")
                
                message += f"{i}. {name} (Expires: {exp_date})\n"
            
            if len(items) > 5:
                message += f"...and {len(items) - 5} more items.\n"
            
            message += "\n"
        
        if notifications:
            message += f"🔔 <b>PICKUP REQUESTS ({len(notifications)})</b>\n"
            for i, notif in enumerate(notifications[:5], 1):
                req_type = notif.get("type", "unknown")
                status = notif.get("status", "pending")
                created_at = notif.get("created_at", "N/A")
                if isinstance(created_at, datetime):
                    created_at = created_at.strftime("%Y-%m-%d")
                
                message += f"{i}. {req_type.upper()} - Status: {status.upper()} ({created_at})\n"
            
            if len(notifications) > 5:
                message += f"...and {len(notifications) - 5} more requests.\n"
        
        message += f"\nTo message this user: /msg_{user_id}"
        
        await update.message.reply_text(message, parse_mode="HTML")
    
    except Exception as e:
        logger.error(f"Error retrieving user details: {e}")
        await update.message.reply_text(f"Error retrieving user details: {str(e)}")

async def admin_complete_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mark a request as completed and award points to the user."""
    admin_id = update.effective_user.id
    
    # Verify this is the admin
    if admin_id != ADMIN_ID:
        await update.message.reply_text("Sorry, this command is only available for administrators.")
        return
    
    # Check if request ID was provided in the form /complete_123456
    command_parts = update.message.text.split('_', 1)
    if len(command_parts) != 2 or command_parts[0] != '/complete':
        await update.message.reply_text("Invalid command format. Use /complete_<request_id>")
        return
    
    request_id_str = command_parts[1]
    
    # Try to mark the request as completed
    try:
        from bson import ObjectId
        try:
            # Try to convert to ObjectId
            request_id = ObjectId(request_id_str)
        except:
            # If invalid ObjectId format
            await update.message.reply_text(f"Invalid request ID format: {request_id_str}")
            return
        
        # First get the request to check if points have already been awarded
        request = db.notifications.find_one({"_id": request_id})
        
        if not request:
            await update.message.reply_text(f"⚠️ Request not found: {request_id_str}")
            return
        
        # Get user information
        user_id = request.get("user_id")
        username = request.get("username", "Unknown User")
        points_amount = request.get("points_amount", 50)
        points_awarded = request.get("points_awarded", False)
        
        # Update request status
        result = db.notifications.update_one(
            {"_id": request_id},
            {"$set": {
                "status": "completed", 
                "completed_at": datetime.now(pytz.UTC),
                "completed_by": admin_id,
                "points_awarded": True
            }}
        )
        
        if result.modified_count > 0:
            status_message = f"✅ Request marked as completed: {request_id_str}"
            
            # Award points if they haven't been awarded yet
            if not points_awarded and user_id:
                # Award points to the user
                users_collection.update_one(
                    {"user_id": user_id},
                    {"$inc": {"points": points_amount}}
                )
                
                # Get updated user points
                updated_user = users_collection.find_one({"user_id": user_id})
                current_points = updated_user.get("points", points_amount) if updated_user else points_amount
                
                # Send notification to user about points
                try:
                    user_message = (
                        f"🎉 <b>Congratulations!</b>\n\n"
                        f"Your {request.get('type', 'pickup')} request has been completed.\n"
                        f"Item: {request.get('item_name', 'Unknown item')}\n\n"
                        f"<b>You've been awarded {points_amount} points!</b>\n"
                        f"Your current balance: <b>{current_points} points</b>"
                    )
                    
                    # Send message to user
                    url = f"https://api.telegram.org/bot{context.bot.token}/sendMessage"
                    data = {
                        "chat_id": user_id,
                        "text": user_message,
                        "parse_mode": "HTML"
                    }
                    
                    import requests
                    response = requests.post(url, data=data)
                    
                    if response.json().get("ok"):
                        status_message += f"\n✅ {points_amount} points awarded to {username} (ID: {user_id})"
                    else:
                        status_message += f"\n⚠️ Points awarded, but failed to notify user: {username}"
                
                except Exception as e:
                    logger.error(f"Failed to notify user about points: {e}")
                    status_message += f"\n⚠️ Points awarded, but error notifying user: {str(e)}"
            
            elif points_awarded:
                status_message += f"\nℹ️ Points were already awarded to {username}"
            
            await update.message.reply_text(status_message)
        else:
            await update.message.reply_text(f"⚠️ Request already completed or not found: {request_id_str}")
    
    except Exception as e:
        logger.error(f"Error marking request as completed: {e}")
        await update.message.reply_text(f"Error: {str(e)}")

async def admin_message_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start the process of sending a message to a user."""
    admin_id = update.effective_user.id
    
    # Verify this is the admin
    if admin_id != ADMIN_ID:
        await update.message.reply_text("Sorry, this command is only available for administrators.")
        return
    
    # Check if user ID was provided in the form /msg_123456
    command_parts = update.message.text.split('_', 1)
    if len(command_parts) == 2 and command_parts[0] == '/msg':
        user_id_str = command_parts[1]
    elif context.args:
        user_id_str = context.args[0]
    else:
        await update.message.reply_text("Please provide a user ID.\nUsage: /msg <user_id> or /msg_<user_id>")
        return
    
    # Try to find the user
    try:
        user_id = int(user_id_str)
        user = users_collection.find_one({"user_id": user_id})
        
        if not user:
            await update.message.reply_text(f"User not found with ID: {user_id}")
            return
        
        # Store user ID in context for the next step
        context.user_data['admin_msg_user_id'] = user_id
        context.user_data['admin_msg_username'] = user.get('username', 'User')
        
        await update.message.reply_text(
            f"You are about to send a message to {user.get('username', 'User')} (ID: {user_id}).\n\n"
            f"Please type your message or /cancel to abort."
        )
        
        # Set conversation state
        return ADMIN_SEND_MESSAGE
    
    except ValueError:
        await update.message.reply_text("Invalid user ID. Please provide a numeric ID.")
        return
    
    except Exception as e:
        logger.error(f"Error preparing to message user: {e}")
        await update.message.reply_text(f"Error: {str(e)}")
        return

async def admin_send_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the admin's message to send to a user."""
    if update.message.text == '/cancel':
        await update.message.reply_text("Message sending cancelled.")
        # Clear user ID from context
        if 'admin_msg_user_id' in context.user_data:
            del context.user_data['admin_msg_user_id']
        if 'admin_msg_username' in context.user_data:
            del context.user_data['admin_msg_username']
        return ConversationHandler.END
    
    user_id = context.user_data.get('admin_msg_user_id')
    username = context.user_data.get('admin_msg_username', 'User')
    message = update.message.text
    
    if not user_id:
        await update.message.reply_text("Error: User ID not found in context. Please try again.")
        return ConversationHandler.END
    
    # Send the message
    try:
        # Add admin prefix to the message
        full_message = f"<b>🔔 Message from Qoot Bot Admin:</b>\n\n{message}"
        
        # Use Telegram API directly
        url = f"https://api.telegram.org/bot{context.bot.token}/sendMessage"
        data = {
            "chat_id": user_id,
            "text": full_message,
            "parse_mode": "HTML"
        }
        
        import requests
        response = requests.post(url, data=data)
        result = response.json()
        
        if result.get("ok"):
            await update.message.reply_text(f"✅ Message sent to {username} (ID: {user_id})")
            
            # Log the message
            try:
                message_log = {
                    "user_id": user_id,
                    "username": username,
                    "message": message,
                    "sent_at": datetime.now(pytz.UTC),
                    "sent_by": "admin",
                    "admin_id": update.effective_user.id
                }
                
                if 'messages' not in db.list_collection_names():
                    db.create_collection('messages')
                
                db.messages.insert_one(message_log)
            except Exception as e:
                logger.error(f"Failed to log message: {e}")
        else:
            await update.message.reply_text(f"❌ Failed to send message: {result.get('description', 'Unknown error')}")
    
    except Exception as e:
        logger.error(f"Error sending message to user: {e}")
        await update.message.reply_text(f"❌ Error sending message: {str(e)}")
    
    return ConversationHandler.END

async def about_to_expire(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show items that are about to expire."""
    user_id = update.effective_user.id
    
    # Find items that are about to expire (within two weeks)
    two_weeks_later = datetime.now(pytz.UTC) + timedelta(days=14)
    query = {
        "user_id": user_id,
        "expiration_date": {
            "$gt": datetime.now(pytz.UTC),
            "$lte": two_weeks_later
        }
    }
    
    items = list(items_collection.find(query))
    
    # Use main menu keyboard instead of back button
    main_keyboard = [
        [KeyboardButton("About to Expire"), KeyboardButton("Expired")],
        [KeyboardButton("Marketplace"), KeyboardButton("Rewards")]
    ]
    main_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
    
    if not items:
        await update.message.reply_text(
            "You don't have any items that are about to expire.",
            reply_markup=main_markup
        )
        return
    
    await update.message.reply_text("Here are your items that are about to expire:", reply_markup=main_markup)
    
    for item in items:
        quantity = item.get('quantity', 1)
        
        keyboard = [
            [
                InlineKeyboardButton("Donate it", callback_data=f"donate_{item['_id']}"),
                InlineKeyboardButton("List in Marketplace", callback_data=f"list_{item['_id']}")
            ],
            [
                InlineKeyboardButton("Delete Item", callback_data=f"delete_{item['_id']}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Format expiration date (from YYYY-MM-DD to DD-MM-YYYY)
        exp_date = item['expiration_date'].strftime("%d-%m-%Y")
        
        await update.message.reply_text(
            f"Name: {item['name']}\n"
            f"Quantity: {quantity}\n"
            f"Unit Price: {item['price']} AED\n"
            f"Expiration Date: {exp_date}",
            reply_markup=reply_markup
        )

async def expired(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show expired items."""
    user_id = update.effective_user.id
    
    # Find expired items
    query = {
        "user_id": user_id,
        "expiration_date": {"$lte": datetime.now(pytz.UTC)}
    }
    
    items = list(items_collection.find(query))
    
    # Use main menu keyboard instead of back button
    main_keyboard = [
        [KeyboardButton("About to Expire"), KeyboardButton("Expired")],
        [KeyboardButton("Marketplace"), KeyboardButton("Rewards")]
    ]
    main_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
    
    if not items:
        await update.message.reply_text(
            "You don't have any expired items.",
            reply_markup=main_markup
        )
        return
    
    await update.message.reply_text("Here are your expired items:", reply_markup=main_markup)
    
    for item in items:
        quantity = item.get('quantity', 1)
        
        keyboard = [
            [InlineKeyboardButton("Send to anaerobic digester", callback_data=f"digest_{item['_id']}")],
            [InlineKeyboardButton("Delete Item", callback_data=f"delete_{item['_id']}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Format expiration date (from YYYY-MM-DD to DD-MM-YYYY)
        exp_date = item['expiration_date'].strftime("%d-%m-%Y")
        
        await update.message.reply_text(
            f"Name: {item['name']}\n"
            f"Quantity: {quantity}\n"
            f"Unit Price: {item['price']} AED\n"
            f"Expiration Date: {exp_date}",
            reply_markup=reply_markup
        )

async def marketplace(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show marketplace options."""
    # Use regular keyboard buttons instead of inline keyboard
    keyboard = [
        [KeyboardButton("My Listings"), KeyboardButton("Explore Marketplace")],
        [KeyboardButton("🔙 Back to Main Menu")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "Welcome to the Marketplace!",
        reply_markup=reply_markup
    )

async def rewards(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user rewards."""
    user_id = update.effective_user.id
    
    # Find user in database
    user_data = users_collection.find_one({"user_id": user_id})
    
    if not user_data:
        await update.message.reply_text("User not found. Please use /start to register.")
        return
    
    points = user_data.get('points', 0)
    
    # Create keyboard for redemption options with back button
    keyboard = [
        [KeyboardButton("Google Play Gift Card 30 AED (200 points)")],
        [KeyboardButton("Google Play Gift Card 50 AED (350 points)")],
        [KeyboardButton("Apple Gift Card 50 AED (400 points)")],
        [KeyboardButton("🔙 Back to Main Menu")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"You have {points} points.\n\nChoose a redemption option:",
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular messages."""
    text = update.message.text
    user_id = update.effective_user.id
    
    # Regular user button handlers
    if text == "About to Expire":
        await about_to_expire(update, context)
    elif text == "Expired":
        await expired(update, context)
    elif text == "Marketplace":
        await marketplace(update, context)
    elif text == "My Listings":
        await show_my_listings(update.message, context)
    elif text == "Explore Marketplace":
        await explore_marketplace(update.message, context)
    elif text == "Rewards":
        await rewards(update, context)
    elif text == "🔙 Back to Main Menu" or text == "🏠 Main Menu" or text == "🔙 Return to User Mode":
        # Handle back to main menu from keyboard buttons
        if user_id == ADMIN_ID:
            keyboard = [
                [KeyboardButton("About to Expire"), KeyboardButton("Expired")],
                [KeyboardButton("Marketplace"), KeyboardButton("Rewards")],
                [KeyboardButton("⚙️ Admin Panel")]
            ]
        else:
            keyboard = [
                [KeyboardButton("About to Expire"), KeyboardButton("Expired")],
                [KeyboardButton("Marketplace"), KeyboardButton("Rewards")]
            ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "Main Menu - What would you like to do?",
            reply_markup=reply_markup
        )
    elif text == "🔙 Back to Marketplace":
        await marketplace(update, context)
    elif text == "🔙 Back to My Listings":
        await show_my_listings(update.message, context)
    elif text == "🔙 Back to Rewards":
        await rewards(update, context)
    elif text == "Google Play Gift Card 30 AED (200 points)":
        await redeem_gift_card(update, context, "Google Play", 30, 200)
    elif text == "Google Play Gift Card 50 AED (350 points)":
        await redeem_gift_card(update, context, "Google Play", 50, 350)
    elif text == "Apple Gift Card 50 AED (400 points)":
        await redeem_gift_card(update, context, "Apple", 50, 400)
    # Admin-specific button handlers
    elif text == "⚙️ Admin Panel" and user_id == ADMIN_ID:
        await admin_start(update, context)
    elif user_id == ADMIN_ID and text in ["👤 Users", "📦 Requests", "📊 Statistics", "📝 Messages", "🛒 Marketplace Admin"]:
        if text == "👤 Users":
            await admin_users(update, context)
        elif text == "📦 Requests":
            await admin_requests(update, context)
        elif text == "📊 Statistics":
            await admin_stats(update, context)
        elif text == "📝 Messages":
            await update.message.reply_text("To send a message to a user, use /msg <user_id> or click on the message link in user details.")
        elif text == "🛒 Marketplace Admin":
            await admin_marketplace(update, context)
    else:
        await update.message.reply_text("I don't understand that command.")

async def redeem_gift_card(update: Update, context: ContextTypes.DEFAULT_TYPE, card_type, amount, required_points):
    """Redeem a gift card."""
    user_id = update.effective_user.id
    
    # Find user in database
    user_data = users_collection.find_one({"user_id": user_id})
    
    if not user_data:
        await update.message.reply_text("User not found. Please use /start to register.")
        return
    
    points = user_data.get('points', 0)
    
    if points < required_points:
        await update.message.reply_text(f"You don't have enough points. You need {required_points} points, but you only have {points}.")
        return
    
    # Deduct points
    users_collection.update_one(
        {"user_id": user_id},
        {"$inc": {"points": -required_points}}
    )
    
    # In a real application, you would generate or retrieve a real gift card code
    gift_card_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
    
    # Add a back button
    keyboard = [[KeyboardButton("🔙 Back to Rewards"), KeyboardButton("🏠 Main Menu")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"You have successfully redeemed a {card_type} Gift Card worth {amount} AED!\n\n"
        f"Your gift card code is: {gift_card_code}\n\n"
        f"You have {points - required_points} points remaining.",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    user_id = query.from_user.id
    
    logger.info(f"Button callback received: {callback_data} from user {user_id}")
    
    try:
        if callback_data.startswith("donate_"):
            item_id = callback_data[len("donate_"):]
            context.user_data['current_item'] = item_id
            context.user_data['callback_type'] = 'donate'  # Track that this is a donation
            
            # Get item to check quantity
            item = items_collection.find_one({"_id": ObjectId(item_id)})
            if item and item.get('quantity', 1) > 1:
                # Ask user to type quantity
                max_qty = item.get('quantity', 1)
                context.user_data['max_quantity'] = max_qty
                await query.message.reply_text(f"How many units of {item['name']} would you like to donate? (1-{max_qty})\n\n/cancel to cancel")
                return DONATE_QUANTITY
            else:
                # Default quantity is 1
                context.user_data['donate_quantity'] = 1
                # Show date selection keyboard
                reply_markup = get_working_day_buttons()
                await query.message.reply_text("Please select pickup date:", reply_markup=reply_markup)
                return PICKUP_DATE
        
        elif callback_data.startswith("list_"):
            item_id = callback_data[len("list_"):]
            context.user_data['current_item'] = item_id
            
            # Get item to check quantity
            item = items_collection.find_one({"_id": ObjectId(item_id)})
            if item and item.get('quantity', 1) > 1:
                # Ask user to type quantity
                max_qty = item.get('quantity', 1)
                context.user_data['max_quantity'] = max_qty
                await query.message.reply_text(f"How many units of {item['name']} would you like to list in the marketplace? (1-{max_qty})\n\n/cancel to cancel")
                return LIST_QUANTITY
            else:
                # Default quantity is 1
                context.user_data['list_quantity'] = 1
                logger.info(f"User {user_id} listing item {item_id}")
                await query.message.reply_text("Please enter the listing price in AED:\n\n/cancel to cancel")
                return LISTING_PRICE
        
        elif callback_data.startswith("digest_"):
            item_id = callback_data[len("digest_"):]
            context.user_data['current_item'] = item_id
            context.user_data['callback_type'] = 'digest'  # Track that this is for digestion
            
            # Get item to check quantity
            item = items_collection.find_one({"_id": ObjectId(item_id)})
            if item and item.get('quantity', 1) > 1:
                # Ask user to type quantity
                max_qty = item.get('quantity', 1)
                context.user_data['max_quantity'] = max_qty
                await query.message.reply_text(f"How many units of {item['name']} would you like to send for digestion? (1-{max_qty})\n\n/cancel to cancel")
                return DIGEST_QUANTITY
            else:
                # Default quantity is 1
                context.user_data['digest_quantity'] = 1
                # Show date selection keyboard
                reply_markup = get_working_day_buttons()
                await query.message.reply_text("Please select pickup date:", reply_markup=reply_markup)
                return PICKUP_DATE
        
        elif callback_data.startswith("delete_"):
            # Extract everything after "delete_" to get the proper ID
            item_id = callback_data[len("delete_"):]
            context.user_data['current_item'] = item_id
            context.user_data['callback_type'] = 'delete'  # Track that this is for deletion
            
            logger.info(f"Processing delete_ with item_id: {item_id}")
            
            # Get item to check quantity
            try:
                # Debug the item_id
                logger.info(f"DEBUG - delete_ raw item_id: '{item_id}'")
                
                # Check if item_id has "listing_" prefix erroneously
                if item_id.startswith("listing_"):
                    logger.warning(f"Item ID contains 'listing_' prefix, removing it: {item_id}")
                    item_id = item_id[len("listing_"):]
                    logger.info(f"Corrected item_id: {item_id}")
                    context.user_data['current_item'] = item_id
                
                # Make sure item_id is properly formatted for ObjectId conversion
                item_id = item_id.strip()
                logger.info(f"Attempting to find item with ObjectId: {item_id}")
                
                item = items_collection.find_one({"_id": ObjectId(item_id)})
                if item and item.get('quantity', 1) > 1:
                    # Ask user to type quantity
                    max_qty = item.get('quantity', 1)
                    context.user_data['max_quantity'] = max_qty
                    await query.message.reply_text(f"How many units of {item['name']} would you like to delete? (1-{max_qty})\n\n/cancel to cancel")
                    return DELETE_QUANTITY
                else:
                    # Default quantity is 1, just delete the item
                    items_collection.delete_one({"_id": ObjectId(item_id)})
                    if item:
                        await query.message.reply_text(f"{item['name']} has been deleted from your inventory.")
                    else:
                        await query.message.reply_text("Item has been deleted from your inventory.")
                    return ConversationHandler.END
            except Exception as e:
                error_type = type(e).__name__
                logger.error(f"Error processing delete_ with item_id {item_id}: {error_type} - {str(e)}")
                
                # Print the full exception traceback for debugging
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                # Provide a better error message to the user
                await query.message.reply_text("Error processing delete request. Please try again.")
                return ConversationHandler.END
        
        # Handle date selection from inline keyboard
        elif callback_data.startswith("date_"):
            # Extract the date from callback_data
            date_str = callback_data[len("date_"):]
            context.user_data['pickup_date'] = date_str
            # Continue to time selection with inline keyboard
            reply_markup = get_time_slot_buttons()
            await query.message.reply_text("Please select a pickup time:", reply_markup=reply_markup)
            return PICKUP_TIME
        
        # Handle cancel date selection
        elif callback_data == "cancel_date":
            # Clear any conversation-specific user data
            for key in ['current_item', 'pickup_date', 'pickup_time', 'pickup_location', 'edit_listing']:
                if key in context.user_data:
                    del context.user_data[key]
            
            # Return to main menu
            keyboard = [
                [KeyboardButton("About to Expire"), KeyboardButton("Expired")],
                [KeyboardButton("Marketplace"), KeyboardButton("Rewards")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await query.message.reply_text(
                "Operation cancelled. Back to Main Menu.",
                reply_markup=reply_markup
            )
            return ConversationHandler.END
            
        # Handle time slot selection
        elif callback_data.startswith("time_"):
            # Extract the time slot from callback_data
            time_slot = callback_data[len("time_"):]
            
            # Format the time slot to include AM/PM
            if time_slot == "08:00-12:00":
                formatted_time = "08:00 AM - 12:00 PM"
            elif time_slot == "12:00-18:00":
                formatted_time = "12:00 PM - 06:00 PM"
            else:
                formatted_time = time_slot
                
            context.user_data['pickup_time'] = formatted_time
            
            # Create keyboard button to request location
            location_keyboard = KeyboardButton(text="Share Location", request_location=True)
            reply_markup = ReplyKeyboardMarkup([[location_keyboard]], resize_keyboard=True, one_time_keyboard=True)
            
            await query.message.reply_text(
                "Please share your pickup location.\n"
                "You can either:\n"
                "- Tap the 'Share Location' button below to send your current location\n"
                "- Type an address manually\n\n"
                "/cancel to cancel", 
                reply_markup=reply_markup
            )
            return PICKUP_LOCATION
            
        # Handle cancel time selection
        elif callback_data == "cancel_time":
            # Clear any conversation-specific user data
            for key in ['current_item', 'pickup_date', 'pickup_time', 'pickup_location', 'edit_listing']:
                if key in context.user_data:
                    del context.user_data[key]
            
            # Return to main menu
            keyboard = [
                [KeyboardButton("About to Expire"), KeyboardButton("Expired")],
                [KeyboardButton("Marketplace"), KeyboardButton("Rewards")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await query.message.reply_text(
                "Operation cancelled. Back to Main Menu.",
                reply_markup=reply_markup
            )
            return ConversationHandler.END
        
        # Admin-specific button handler for removing marketplace listings
        elif callback_data.startswith("admin_remove_"):
            if user_id != ADMIN_ID:
                await query.message.reply_text("Sorry, this action is only available for administrators.")
                return ConversationHandler.END
                
            listing_id = callback_data[len("admin_remove_"):]
            logger.info(f"Admin {user_id} removing listing {listing_id}")
            await admin_remove_listing(query.message, context, listing_id)
            return ConversationHandler.END
        
        # The following callbacks are no longer needed as we're using keyboard buttons
        # But keep them for backward compatibility
        elif callback_data == "my_listings":
            logger.info(f"User {user_id} requesting their listings via inline button")
            await show_my_listings(query.message, context)
        
        elif callback_data == "explore_marketplace":
            logger.info(f"User {user_id} exploring marketplace via inline button")
            await explore_marketplace(query.message, context)
        
        elif callback_data == "back_to_marketplace":
            logger.info(f"User {user_id} returning to marketplace via inline button")
            await marketplace(query.message, context)
        
        elif callback_data == "back_to_main":
            logger.info(f"User {user_id} returning to main menu via inline button")
            # Return to main menu
            keyboard = [
                [KeyboardButton("About to Expire"), KeyboardButton("Expired")],
                [KeyboardButton("Marketplace"), KeyboardButton("Rewards")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await query.message.reply_text(
                "Main Menu - What would you like to do?",
                reply_markup=reply_markup
            )
        
        elif callback_data.startswith("buy_"):
            listing_id = callback_data[len("buy_"):]
            logger.info(f"User {user_id} buying item with listing ID {listing_id}")
            await buy_item(query.message, context, listing_id)
        
        elif callback_data.startswith("notify_"):
            listing_id = callback_data[len("notify_"):]
            logger.info(f"User {user_id} notifying seller of interest in listing {listing_id}")
            await notify_seller(query.message, context, listing_id)
        
        elif callback_data.startswith("delete_listing_"):
            # The format should be delete_listing_<objectid>
            # Extract the listing ID correctly by removing the prefix
            listing_id = callback_data[len("delete_listing_"):]  # This gets everything after the prefix
            logger.info(f"User {user_id} deleting listing {listing_id}")
            try:
                # Pass the entire query object to delete_listing function
                await delete_listing(query, context, listing_id)
            except Exception as e:
                logger.error(f"Error handling delete_listing callback: {type(e).__name__} - {str(e)}")
                # Print the full exception traceback for debugging
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                await query.message.reply_text("Error processing delete request. Please try again.")
            return ConversationHandler.END
        
        elif callback_data.startswith("edit_listing_"):
            # The format should be edit_listing_<objectid>
            # Extract the listing ID correctly by removing the prefix
            listing_id = callback_data[len("edit_listing_"):]  # This gets everything after the prefix
            logger.info(f"User {user_id} editing listing {listing_id}")
            try:
                context.user_data['edit_listing'] = listing_id
                await query.message.reply_text("Please enter the new listing price in AED:\n\n/cancel to cancel")
                return LISTING_PRICE
            except Exception as e:
                logger.error(f"Error preparing to edit listing: {e}")
                await query.message.reply_text(f"Error preparing to edit listing: {str(e)}")
            return ConversationHandler.END
        
        return ConversationHandler.END
    
    except Exception as e:
        # Catch any unexpected errors, particularly ObjectId conversion issues
        error_type = type(e).__name__
        logger.error(f"Unexpected error in button_callback: {error_type} - {str(e)}")
        
        # Handle ObjectId conversion errors specially
        if "InvalidId" in error_type:
            logger.error(f"Invalid ObjectId format in callback: {callback_data}")
            await query.message.reply_text("An error occurred processing this action. Please try again or contact support.")
        else:
            # General error handling
            await query.message.reply_text("An error occurred. Please try again.")
            
        return ConversationHandler.END

async def pickup_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle pickup date input."""
    if update.message.text == "/cancel":
        return await cancel(update, context)
    
    # For text input, show the inline keyboard instead
    reply_markup = get_working_day_buttons()
    await update.message.reply_text("Please select pickup date:", reply_markup=reply_markup)
    return PICKUP_DATE

async def pickup_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle pickup time input."""
    if update.message.text == "/cancel":
        return await cancel(update, context)
    
    # For text input, show the inline keyboard instead
    reply_markup = get_time_slot_buttons()
    await update.message.reply_text("Please select a pickup time:", reply_markup=reply_markup)
    return PICKUP_TIME

async def pickup_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle pickup location input."""
    user_id = update.effective_user.id
    item_id = context.user_data.get('current_item')
    callback_type = context.user_data.get('callback_type', 'donate')  # Default to donate
    
    # Get quantity from context
    quantity = 1
    if callback_type == 'donate':
        quantity = context.user_data.get('donate_quantity', 1)
    elif callback_type == 'digest':
        quantity = context.user_data.get('digest_quantity', 1)
    
    # Store whether this was a shared location or text
    has_location_file = False
    location_coordinates = None
    
    if update.message.location:
        # If user shared location, get coordinates
        location = update.message.location
        location_coordinates = {"latitude": location.latitude, "longitude": location.longitude}
        # Create a Google Maps link
        maps_link = f"https://maps.google.com/maps?q={location.latitude},{location.longitude}"
        pickup_location = f"<a href='{maps_link}'>View on Map</a>"
        has_location_file = True
    else:
        # Otherwise use text input
        pickup_location = update.message.text
    
    # Get the date and time from user data
    pickup_date = context.user_data.get('pickup_date', 'Not specified')
    pickup_time = context.user_data.get('pickup_time', 'Not specified')
    
    # Format the time slot to include AM/PM
    if pickup_time == "08:00-12:00":
        pickup_time = "08:00 AM - 12:00 PM"
    elif pickup_time == "12:00-18:00":
        pickup_time = "12:00 PM - 06:00 PM"
    
    logger.info(f"Pickup request from user {user_id}: {pickup_date} {pickup_time} at {pickup_location}")
    
    # Get item details
    item = items_collection.find_one({"_id": ObjectId(item_id)})
    if not item:
        await update.message.reply_text("Sorry, that item is no longer available.")
        return ConversationHandler.END
    
    item_name = item.get('name', 'unknown item')
    item_quantity = item.get('quantity', 1)
    
    # Add to notification collection
    notification = {
        "user_id": user_id,
        "item_id": item_id,
        "item_name": item_name,
        "type": callback_type,  # 'donate' or 'digest'
        "pickup_date": pickup_date,
        "pickup_time": pickup_time,
        "pickup_location": pickup_location,
        "has_location_file": has_location_file,
        "status": "pending",
        "requested_at": datetime.now(pytz.UTC),
        "quantity": quantity
    }
    
    # Add coordinates if available
    if location_coordinates:
        notification["coordinates"] = location_coordinates
    
    db.notifications.insert_one(notification)
    
    # Notify admin
    admin_notified = False
    try:
        admin_message = (
            f"🔔 <b>NEW PICKUP REQUEST</b>\n\n"
            f"Contact: <a href='tg://user?id={user_id}'>Chat with user</a>\n"
            f"Item: {item_name} (x{quantity})\n"
            f"Type: {'Donation' if callback_type == 'donate' else 'Anaerobic Digestion'}\n"
            f"Date: {pickup_date}\n"
            f"Time: {pickup_time}\n"
            f"Location: {pickup_location}\n\n"
            f"Use /requests to view all pending requests."
        )
        
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_message,
            parse_mode="HTML"
        )
        
        admin_notified = True
        logger.info(f"Admin notified about pickup request from user {user_id}")
    except Exception as e:
        logger.error(f"Failed to notify admin: {e}")
    
    # Update or remove item from user's inventory based on quantity
    if quantity >= item_quantity:
        # Remove the item entirely
        items_collection.delete_one({"_id": ObjectId(item_id)})
    else:
        # Reduce the quantity
        items_collection.update_one(
            {"_id": ObjectId(item_id)},
            {"$set": {"quantity": item_quantity - quantity}}
        )
    
    # Create keyboard for main menu
    main_keyboard = [
        [KeyboardButton("About to Expire"), KeyboardButton("Expired")],
        [KeyboardButton("Marketplace"), KeyboardButton("Rewards")]
    ]
    main_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
    
    if admin_notified:
        await update.message.reply_text(
            f"Thank you! Your request has been sent to our team for processing.\n"
            f"You will receive 50 points once your request is completed.",
            reply_markup=main_markup
        )
    else:
        await update.message.reply_text(
            f"Thank you! Your request has been recorded and our team will process it.\n"
            f"There was an error notifying the administrator, but your request has been saved.\n"
            f"You will receive 50 points once your request is completed.",
            reply_markup=main_markup
        )
    
    return ConversationHandler.END

async def listing_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle listing price input."""
    try:
        price = float(update.message.text)
        if price <= 0:
            await update.message.reply_text("Price must be greater than 0. Please enter a valid price:")
            return LISTING_PRICE
        
        # Check if we're editing an existing listing or creating a new one
        edit_listing_id = context.user_data.get('edit_listing')
        
        if edit_listing_id:
            # We're editing an existing listing
            try:
                # Find the listing by ID
                listing = marketplace_collection.find_one({"_id": ObjectId(edit_listing_id)})
                
                if not listing:
                    await update.message.reply_text("Error: Listing not found or may have been deleted.")
                    return ConversationHandler.END
                
                # Update the price
                marketplace_collection.update_one(
                    {"_id": ObjectId(edit_listing_id)},
                    {"$set": {"price": price}}
                )
                
                # Show confirmation with navigation options
                keyboard = [
                    [KeyboardButton("My Listings"), KeyboardButton("Explore Marketplace")],
                    [KeyboardButton("🏠 Main Menu")]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                
                await update.message.reply_text(
                    f"Your listing for {listing['item_name']} has been updated. New price: {price} AED.",
                    reply_markup=reply_markup
                )
                
                # Clear edit_listing from context
                if 'edit_listing' in context.user_data:
                    del context.user_data['edit_listing']
                
                return ConversationHandler.END
                
            except Exception as e:
                logger.error(f"Error updating listing price: {e}")
                await update.message.reply_text(f"Error updating listing price: {str(e)}")
                return ConversationHandler.END
        
        # If we're not editing, we're creating a new listing
        # Get the item ID and quantity from context
        item_id = context.user_data.get('current_item')
        quantity = context.user_data.get('list_quantity', 1)
        
        # Get the item from the database
        item = items_collection.find_one({"_id": ObjectId(item_id)})
        if not item:
            await update.message.reply_text("Error: Item not found.")
            return ConversationHandler.END
            
        # Get user information
        user_id = update.effective_user.id
        user = users_collection.find_one({"user_id": user_id})
        
        if not user:
            await update.message.reply_text("Error: User not found.")
            return ConversationHandler.END
            
        # Get username or first name for display
        username = update.effective_user.username
        first_name = update.effective_user.first_name
        last_name = update.effective_user.last_name or ""
        full_name = f"{first_name} {last_name}".strip()
        
        # Create listing
        listing = {
            "user_id": user_id,
            "username": username,
            "full_name": full_name,
            "item_id": str(item["_id"]),
            "item_name": item["name"],
            "price": price,
            "original_price": item["price"],
            "expiration_date": item["expiration_date"],
            "listed_at": datetime.now(pytz.UTC),
            "quantity": quantity
        }
        
        result = marketplace_collection.insert_one(listing)
        logger.info(f"New listing created with ID: {result.inserted_id}")
        
        # Update or remove item from user's inventory based on quantity
        item_quantity = item.get('quantity', 1)
        if quantity >= item_quantity:
            # Remove the item entirely
            items_collection.delete_one({"_id": ObjectId(item_id)})
        else:
            # Reduce the quantity
            items_collection.update_one(
                {"_id": ObjectId(item_id)},
                {"$set": {"quantity": item_quantity - quantity}}
            )
        
        # Show confirmation with navigation options using keyboard buttons
        keyboard = [
            [KeyboardButton("My Listings"), KeyboardButton("Explore Marketplace")],
            [KeyboardButton("🏠 Main Menu")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            f"Your item ({quantity}x {item['name']}) has been listed in the marketplace for {price} AED.",
            reply_markup=reply_markup
        )
        
        return ConversationHandler.END
    
    except ValueError:
        await update.message.reply_text("Invalid price. Please enter a number:\n\n/cancel to cancel")
        return LISTING_PRICE

async def show_my_listings(message, context):
    """Show user's marketplace listings."""
    user_id = message.chat.id
    
    logger.info(f"Looking for listings for user_id: {user_id}")
    
    # Ensure user_id is correctly typed (integer)
    if isinstance(user_id, str):
        try:
            user_id = int(user_id)
        except ValueError:
            logger.error(f"Could not convert user_id to integer: {user_id}")
    
    # Find user's listings with proper user_id
    listings = list(marketplace_collection.find({"user_id": user_id}))
    logger.info(f"Found {len(listings)} listings for user_id {user_id}")
    
    # Navigation with keyboard buttons
    nav_keyboard = [
        [KeyboardButton("🔙 Back to Marketplace"), KeyboardButton("🏠 Main Menu")]
    ]
    nav_markup = ReplyKeyboardMarkup(nav_keyboard, resize_keyboard=True)
    
    if not listings:
        await message.reply_text(
            "You don't have any listings in the marketplace.", 
            reply_markup=nav_markup
        )
        return
    
    await message.reply_text("Here are your marketplace listings:")
    
    for listing in listings:
        # Make sure the ObjectId is converted to string correctly
        listing_id = str(listing['_id'])
        logger.info(f"Creating buttons for listing: {listing_id}")
        
        # Keep inline keyboard for actions on specific listings
        keyboard = [
            [
                InlineKeyboardButton("Delete Listing", callback_data=f"delete_listing_{listing_id}"),
                InlineKeyboardButton("Edit Price", callback_data=f"edit_listing_{listing_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Format expiration date (from YYYY-MM-DD to DD-MM-YYYY)
        exp_date = listing['expiration_date'].strftime("%d-%m-%Y")
        quantity = listing.get('quantity', 1)
        
        await message.reply_text(
            f"Name: {listing['item_name']}\n"
            f"Quantity: {quantity}\n"
            f"Unit Price: {listing['price']} AED\n"
            f"Expiration Date: {exp_date}\n"
            f"Listed: {listing['listed_at'].strftime('%d-%m-%Y %H:%M')}",
            reply_markup=reply_markup
        )

async def buy_item(message, context, listing_id):
    """Contact seller about an item."""
    # Find the listing
    listing = marketplace_collection.find_one({"_id": ObjectId(listing_id)})
    
    if not listing:
        await message.reply_text("This listing is no longer available.")
        return
    
    # Get seller's information
    seller_username = listing.get('username', '')
    seller_id = listing.get('user_id')
    seller_full_name = listing.get('full_name', 'the seller')
    item_name = listing['item_name']
    
    # Get quantity
    quantity = listing.get('quantity', 1)
    
    # Navigation with keyboard buttons
    keyboard = [
        [KeyboardButton("🔙 Back to Marketplace"), KeyboardButton("🏠 Main Menu")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # Generate message based on whether seller has a username
    if seller_username and seller_username != '.':
        contact_info = f"@{seller_username}"
        seller_display_name = contact_info
        direct_contact_message = f"Please continue the conversation directly with {contact_info}."
    else:
        # Create a direct link to the user's chat using their user ID
        contact_info = f"tg://user?id={seller_id}"
        seller_display_name = seller_full_name
        direct_contact_message = f"Please <a href='{contact_info}'>click here</a> to contact {seller_full_name} directly."
    
    # Try to send a notification to the seller about a potential buyer
    try:
        buyer_username = message.chat.username or "a user" 
        buyer_name = message.chat.first_name or "Someone"
        
        seller_notification = (
            f"🛒 <b>Marketplace Notification</b>\n\n"
            f"{buyer_name} is interested in your listing:\n"
            f"Name: {item_name}\n"
            f"Quantity: {quantity}\n\n"
            f"They may contact you soon about this item."
        )
        
        # Send to seller silently
        await context.bot.send_message(
            chat_id=seller_id,
            text=seller_notification,
            parse_mode="HTML"
        )
        logger.info(f"Sent marketplace notification to seller {seller_id}")
    except Exception as e:
        logger.error(f"Failed to notify seller: {e}")
    
    await message.reply_text(
        f"I'll help you connect with {seller_display_name}.\n\n"
        f"Message sent to the seller: \"I'm interested in {item_name} (Quantity: {quantity}), is it still available?\"\n\n"
        f"{direct_contact_message}",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def delete_listing(message_or_query, context, listing_id):
    """Delete a marketplace listing."""
    # Check if message_or_query is a callback query or a message
    if hasattr(message_or_query, 'message'):
        # It's a callback query
        query = message_or_query
        # Need to answer the callback query first
        await query.answer()
        message = query.message
        # Get the user_id from the from_user attribute of the query
        current_user_id = query.from_user.id
    else:
        # It's a message
        message = message_or_query
        # Get the user_id from the chat.id attribute of the message
        current_user_id = message.chat.id

    logger.info(f"Deleting listing with ID: {listing_id}, type: {type(listing_id)}, length: {len(listing_id)}")
    logger.info(f"Request from user_id: {current_user_id}")
    
    try:
        # Debug: Print the exact string value of listing_id
        logger.info(f"DEBUG - Raw listing_id: '{listing_id}'")
        
        # Convert to ObjectId - with better error handling
        try:
            # Make sure listing_id is properly formatted
            # Trim any whitespace or unexpected characters
            cleaned_id = listing_id.strip()
            logger.info(f"DEBUG - Cleaned listing_id: '{cleaned_id}'")
            
            object_id = ObjectId(cleaned_id)
            logger.info(f"Successfully converted to ObjectId: {object_id}")
        except Exception as e:
            logger.error(f"Failed to convert listing_id to ObjectId: '{listing_id}', Error type: {type(e).__name__}, Error: {e}")
            await message.reply_text("Invalid listing ID format. Please try again.")
            return
            
        # Debug: Print the actual query that will be executed
        logger.info(f"DEBUG - DB Query: db.marketplace.find_one({{'_id': ObjectId('{cleaned_id}')}})")
        
        # Get the listing first to confirm it exists
        listing = marketplace_collection.find_one({"_id": object_id})
        
        if not listing:
            logger.warning(f"Listing with ID {listing_id} not found in database")
            await message.reply_text("This listing does not exist or may have already been deleted.")
            return
            
        logger.info(f"Found listing: {listing.get('item_name')} with price {listing.get('price')}")
        
        # Debug: Print user info from the listing
        listing_owner_id = listing.get('user_id')
        logger.info(f"DEBUG - Listing belongs to user_id: {listing_owner_id}")
        
        # Add check to ensure the user deleting is the owner of the listing
        # Skip this check for admin users
        if current_user_id != listing_owner_id and current_user_id != ADMIN_ID:
            logger.warning(f"User {current_user_id} tried to delete listing owned by {listing_owner_id}")
            await message.reply_text("You can only delete your own listings.")
            return
            
        # Delete the listing
        result = marketplace_collection.delete_one({"_id": object_id})
        
        # Navigation with keyboard buttons
        keyboard = [
            [KeyboardButton("🔙 Back to My Listings"), KeyboardButton("🏠 Main Menu")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        if result.deleted_count > 0:
            logger.info(f"Successfully deleted listing {listing_id}")
            await message.reply_text(
                "Your listing has been deleted.",
                reply_markup=reply_markup
            )
        else:
            logger.warning(f"Delete operation did not affect any documents: {listing_id}")
            await message.reply_text(
                "Failed to delete listing. It may have already been removed.",
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Error deleting listing {listing_id}: {type(e).__name__} - {str(e)}")
        # Print the full exception traceback for debugging
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Navigation with keyboard buttons
        keyboard = [
            [KeyboardButton("🔙 Back to My Listings"), KeyboardButton("🏠 Main Menu")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await message.reply_text(
            "Error processing delete request. Please try again.",
            reply_markup=reply_markup
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the current operation."""
    # Clear any conversation-specific user data
    for key in ['current_item', 'pickup_date', 'pickup_time', 'pickup_location', 'edit_listing']:
        if key in context.user_data:
            del context.user_data[key]
    
    # Return to main menu
    keyboard = [
        [KeyboardButton("About to Expire"), KeyboardButton("Expired")],
        [KeyboardButton("Marketplace"), KeyboardButton("Rewards")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "Operation cancelled. Back to Main Menu.",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

async def generate_barcode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate a specific barcode image."""
    args = context.args
    
    if not args or len(args) != 1:
        await update.message.reply_text("Please provide a barcode number.\nUsage: /barcode 123456789012")
        return
    
    barcode_number = args[0]
    
    # Validate the barcode number (should be numeric and 12 digits for EAN13)
    if not barcode_number.isdigit() or len(barcode_number) != 12:
        await update.message.reply_text("Please provide a valid 12-digit barcode number.")
        return
    
    # Generate barcode image
    try:
        # EAN13 needs exactly 12 digits (the 13th is a check digit)
        ean = barcode.get('ean13', barcode_number, writer=ImageWriter())
        
        # Get the full 13-digit number including the check digit
        full_barcode = ean.get_fullcode()
        
        # Save the barcode to a BytesIO object
        buffer = BytesIO()
        ean.write(buffer)
        buffer.seek(0)
        
        # Send the barcode image
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=buffer,
            caption=f"Generated Barcode: {full_barcode}"
        )
        
    except Exception as e:
        logger.error(f"Failed to generate barcode: {e}")
        await update.message.reply_text(f"Error generating barcode: {str(e)}")

async def specific_barcode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate the specific requested barcode image."""
    barcode_number = "661288614129"  # The specifically requested barcode
    
    # Generate barcode image
    try:
        # EAN13 needs exactly 12 digits (the 13th is a check digit)
        ean = barcode.get('ean13', barcode_number, writer=ImageWriter())
        
        # Get the full 13-digit number including the check digit
        full_barcode = ean.get_fullcode()
        
        # Save the barcode to a BytesIO object
        buffer = BytesIO()
        ean.write(buffer)
        buffer.seek(0)
        
        # Send the barcode image
        pinned_message = await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=buffer,
            caption=f"Your Qoot Bot Barcode: {full_barcode}\n\nShow this barcode to the cashier when making purchases."
        )
        
        # Pin the message with the barcode
        await context.bot.pin_chat_message(
            chat_id=update.effective_chat.id,
            message_id=pinned_message.message_id
        )
        
    except Exception as e:
        logger.error(f"Failed to generate specific barcode: {e}")
        await update.message.reply_text(f"Error generating barcode: {str(e)}")

async def notify_seller(message, context, listing_id):
    """Notify seller without requiring messaging."""
    # Find the listing
    listing = marketplace_collection.find_one({"_id": ObjectId(listing_id)})
    
    if not listing:
        await message.reply_text("This listing is no longer available.")
        return
    
    # Get seller's information
    seller_id = listing.get('user_id')
    seller_full_name = listing.get('full_name', 'the seller')
    item_name = listing['item_name']
    
    # Navigation with keyboard buttons
    keyboard = [
        [KeyboardButton("🔙 Back to Marketplace"), KeyboardButton("🏠 Main Menu")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # Try to send a notification to the seller about a potential buyer
    try:
        buyer_username = message.chat.username or "a user" 
        buyer_name = message.chat.first_name or "Someone"
        buyer_id = message.chat.id
        
        seller_notification = (
            f"🛒 <b>Marketplace Notification</b>\n\n"
            f"{buyer_name} is interested in your listing: {item_name}\n\n"
            f"They may contact you soon about this item."
        )
        
        # Send to seller with direct reply link to buyer
        tg_link = f"tg://user?id={buyer_id}"
        seller_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"Reply to {buyer_name}", url=tg_link)]
        ])
        
        await context.bot.send_message(
            chat_id=seller_id,
            text=seller_notification,
            parse_mode="HTML",
            reply_markup=seller_markup
        )
        logger.info(f"Sent marketplace notification to seller {seller_id}")
        
        # Create direct link to seller for buyer
        seller_tg_link = f"tg://user?id={seller_id}"
        buyer_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Contact Seller Directly", url=seller_tg_link)]
        ])
        
        await message.reply_text(
            f"✅ The seller has been notified of your interest in {item_name}.\n\n"
            f"They may contact you soon.",
            reply_markup=buyer_markup
        )
    except Exception as e:
        logger.error(f"Failed to notify seller: {e}")
        await message.reply_text(
            "Unable to notify the seller. Please try again later.",
            reply_markup=reply_markup
        )

async def admin_marketplace(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin function to manage marketplace listings."""
    user_id = update.effective_user.id
    
    # Verify this is the admin
    if user_id != ADMIN_ID:
        await update.message.reply_text("Sorry, this command is only available for administrators.")
        return
    
    # Get all marketplace listings
    try:
        listings = list(marketplace_collection.find().sort("listed_at", -1))
        
        if not listings:
            await update.message.reply_text("There are no listings in the marketplace.")
            return
        
        await update.message.reply_text(f"Found {len(listings)} listings in the marketplace. Showing latest items:")
        
        for listing in listings:
            seller_id = listing.get('user_id', 'Unknown')
            seller_username = listing.get('username', 'Unknown')
            seller_full_name = listing.get('full_name', 'Unknown')
            
            # Format seller display name
            if seller_username and seller_username != '.':
                seller_display = f"@{seller_username}"
            else:
                seller_display = seller_full_name
            
            # Format expiration date (from YYYY-MM-DD to DD-MM-YYYY)
            exp_date = listing['expiration_date'].strftime("%d-%m-%Y")
            
            # Format listing date
            list_date = listing['listed_at'].strftime("%d-%m-%Y %H:%M")
            
            # Get quantity
            quantity = listing.get('quantity', 1)
            
            # Create admin action buttons
            keyboard = [
                [InlineKeyboardButton("Remove Listing", callback_data=f"admin_remove_{listing['_id']}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"Name: {listing['item_name']}\n"
                f"Quantity: {quantity}\n"
                f"Unit Price: {listing['price']} AED\n"
                f"Expiration Date: {exp_date}\n"
                f"Listed: {list_date}\n"
                f"Seller: {seller_display} (ID: {seller_id})",
                reply_markup=reply_markup
            )
    
    except Exception as e:
        logger.error(f"Error retrieving marketplace listings: {e}")
        await update.message.reply_text(f"Error retrieving listings: {str(e)}")

async def admin_remove_listing(message, context, listing_id):
    """Admin function to remove a marketplace listing."""
    # Verify this is the admin
    if message.chat.id != ADMIN_ID:
        await message.reply_text("Sorry, this action is only available for administrators.")
        return
        
    # Find the listing first to get item info
    listing = marketplace_collection.find_one({"_id": ObjectId(listing_id)})
    
    if not listing:
        await message.reply_text("This listing no longer exists.")
        return
        
    item_name = listing.get('item_name', 'Unknown item')
    seller_id = listing.get('user_id', 'Unknown')
    
    # Delete the listing
    result = marketplace_collection.delete_one({"_id": ObjectId(listing_id)})
    
    if result.deleted_count > 0:
        await message.reply_text(f"Listing '{item_name}' has been removed from the marketplace.")
        
        # Notify the seller
        try:
            notification = (
                f"🛒 <b>Marketplace Notification</b>\n\n"
                f"Your listing for '{item_name}' has been removed by an administrator."
            )
            
            await context.bot.send_message(
                chat_id=seller_id,
                text=notification,
                parse_mode="HTML"
            )
            
            logger.info(f"Notified seller {seller_id} about removed listing {listing_id}")
        except Exception as e:
            logger.error(f"Failed to notify seller about removed listing: {e}")
    else:
        await message.reply_text("Failed to remove listing. It may have already been removed.")

async def explore_marketplace(message, context):
    """Show all marketplace listings."""
    # Find all listings except user's own
    user_id = message.chat.id
    
    # Ensure user_id is correctly typed (integer)
    if isinstance(user_id, str):
        try:
            user_id = int(user_id)
        except ValueError:
            logger.error(f"Could not convert user_id to integer: {user_id}")
    
    listings = list(marketplace_collection.find({"user_id": {"$ne": user_id}}))
    logger.info(f"Found {len(listings)} listings for marketplace (excluding user_id {user_id})")
    
    # Navigation with keyboard buttons
    nav_keyboard = [
        [KeyboardButton("🔙 Back to Marketplace"), KeyboardButton("🏠 Main Menu")]
    ]
    nav_markup = ReplyKeyboardMarkup(nav_keyboard, resize_keyboard=True)
    
    if not listings:
        await message.reply_text(
            "There are no listings in the marketplace.", 
            reply_markup=nav_markup
        )
        return
    
    await message.reply_text("Here are the available items in the marketplace:")
    
    for listing in listings:
        # Format listing details
        item_name = listing['item_name']
        price = listing['price']
        exp_date = listing['expiration_date'].strftime("%d-%m-%Y")
        quantity = listing.get('quantity', 1)
        
        # Get seller info
        seller_username = listing.get('username', '')
        seller_id = listing.get('user_id')
        seller_full_name = listing.get('full_name', 'Seller')
        
        # Create appropriate contact info text based on username availability
        if seller_username and seller_username != '.':
            seller_display = f"@{seller_username}"
            # Traditional contact button (will go through bot)
            keyboard = [
                [InlineKeyboardButton("Contact Seller", callback_data=f"buy_{listing['_id']}")]
            ]
        else:
            seller_display = seller_full_name
            # Direct link to seller in the button itself
            tg_link = f"tg://user?id={seller_id}"
            keyboard = [
                [InlineKeyboardButton("Contact Seller Directly", url=tg_link)]
            ]
            
            # Also add a notification button that keeps the original flow
            keyboard[0].append(InlineKeyboardButton("Notify Seller", callback_data=f"notify_{listing['_id']}"))
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(
            f"Name: {item_name}\n"
            f"Quantity: {quantity}\n"
            f"Unit Price: {price} AED\n"
            f"Expiration Date: {exp_date}\n"
            f"Seller: {seller_display}",
            reply_markup=reply_markup
        )

async def donate_quantity_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle quantity input for donation."""
    try:
        # Get the quantity from user input
        quantity = int(update.message.text.strip())
        max_quantity = context.user_data.get('max_quantity', 1)
        
        # Validate quantity
        if quantity < 1 or quantity > max_quantity:
            await update.message.reply_text(f"Please enter a valid quantity between 1 and {max_quantity}:")
            return DONATE_QUANTITY
        
        # Store quantity in context
        context.user_data['donate_quantity'] = quantity
        
        # Proceed to next step - use date selection keyboard
        reply_markup = get_working_day_buttons()
        await update.message.reply_text("Please select pickup date:", reply_markup=reply_markup)
        return PICKUP_DATE
        
    except ValueError:
        await update.message.reply_text(f"Please enter a valid number between 1 and {context.user_data.get('max_quantity', 1)}:")
        return DONATE_QUANTITY

async def list_quantity_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle quantity input for marketplace listing."""
    try:
        # Get the quantity from user input
        quantity = int(update.message.text.strip())
        max_quantity = context.user_data.get('max_quantity', 1)
        
        # Validate quantity
        if quantity < 1 or quantity > max_quantity:
            await update.message.reply_text(f"Please enter a valid quantity between 1 and {max_quantity}:")
            return LIST_QUANTITY
        
        # Store quantity in context
        context.user_data['list_quantity'] = quantity
        
        # Get the item ID
        item_id = context.user_data.get('current_item')
        
        # Log and proceed to next step
        logger.info(f"User {update.effective_user.id} listing {quantity} units of item {item_id}")
        await update.message.reply_text("Please enter the listing price in AED:\n\n/cancel to cancel")
        return LISTING_PRICE
        
    except ValueError:
        await update.message.reply_text(f"Please enter a valid number between 1 and {context.user_data.get('max_quantity', 1)}:")
        return LIST_QUANTITY

async def digest_quantity_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle quantity input for anaerobic digestion."""
    try:
        # Get the quantity from user input
        quantity = int(update.message.text.strip())
        max_quantity = context.user_data.get('max_quantity', 1)
        
        # Validate quantity
        if quantity < 1 or quantity > max_quantity:
            await update.message.reply_text(f"Please enter a valid quantity between 1 and {max_quantity}:")
            return DIGEST_QUANTITY
        
        # Store quantity in context
        context.user_data['digest_quantity'] = quantity
        
        # Proceed to next step - use date selection keyboard
        reply_markup = get_working_day_buttons()
        await update.message.reply_text("Please select pickup date:", reply_markup=reply_markup)
        return PICKUP_DATE
        
    except ValueError:
        await update.message.reply_text(f"Please enter a valid number between 1 and {context.user_data.get('max_quantity', 1)}:")
        return DIGEST_QUANTITY

async def delete_quantity_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle quantity input for item deletion."""
    try:
        # Get the quantity from user input
        quantity = int(update.message.text.strip())
        max_quantity = context.user_data.get('max_quantity', 1)
        
        # Validate quantity
        if quantity < 1 or quantity > max_quantity:
            await update.message.reply_text(f"Please enter a valid quantity between 1 and {max_quantity}:")
            return DELETE_QUANTITY
        
        # Store quantity in context
        context.user_data['delete_quantity'] = quantity
        
        # Get the item
        item_id = context.user_data.get('current_item')
        item = items_collection.find_one({"_id": ObjectId(item_id)})
        
        if not item:
            await update.message.reply_text("Sorry, that item is no longer available.")
            return ConversationHandler.END
        
        item_quantity = item.get('quantity', 1)
        
        # Delete or update the item
        if quantity >= item_quantity:
            # Remove the item entirely
            items_collection.delete_one({"_id": ObjectId(item_id)})
            await update.message.reply_text(f"All units of {item['name']} have been deleted from your inventory.")
        else:
            # Reduce the quantity
            items_collection.update_one(
                {"_id": ObjectId(item_id)},
                {"$set": {"quantity": item_quantity - quantity}}
            )
            await update.message.reply_text(f"{quantity} unit(s) of {item['name']} have been deleted. {item_quantity - quantity} unit(s) remain in your inventory.")
        
        # Return to main menu
        keyboard = [
            [KeyboardButton("About to Expire"), KeyboardButton("Expired")],
            [KeyboardButton("Marketplace"), KeyboardButton("Rewards")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "Back to Main Menu.",
            reply_markup=reply_markup
        )
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text(f"Please enter a valid number between 1 and {context.user_data.get('max_quantity', 1)}:")
        return DELETE_QUANTITY

def get_working_day_buttons():
    """Generate inline keyboard buttons for working days (Monday to Friday)."""
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    day_after_tomorrow = today + timedelta(days=2)
    
    buttons = []
    
    # Check if tomorrow is a working day (Monday-Friday)
    if 0 <= tomorrow.weekday() <= 4:
        # Format: Thursday April 30
        tomorrow_text = tomorrow.strftime("%A %B %d")
        buttons.append(InlineKeyboardButton(
            tomorrow_text, 
            callback_data=f"date_{tomorrow.strftime('%Y-%m-%d')}"
        ))
    
    # Check if day after tomorrow is a working day (Monday-Friday)
    if 0 <= day_after_tomorrow.weekday() <= 4:
        # Format: Friday May 1
        day_after_text = day_after_tomorrow.strftime("%A %B %d")
        buttons.append(InlineKeyboardButton(
            day_after_text, 
            callback_data=f"date_{day_after_tomorrow.strftime('%Y-%m-%d')}"
        ))
    
    # If none of the next two days are working days (weekend), add next working day (Monday)
    if not buttons:
        # Find next Monday
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7  # If today is Monday, go to next Monday
        next_working_day = today + timedelta(days=days_until_monday)
        next_working_text = next_working_day.strftime("%A %B %d")
        buttons.append(InlineKeyboardButton(
            next_working_text, 
            callback_data=f"date_{next_working_day.strftime('%Y-%m-%d')}"
        ))
    
    # Add a cancel button
    buttons.append(InlineKeyboardButton("Cancel", callback_data="cancel_date"))
    
    # Return buttons in rows (up to 1 button per row)
    keyboard = []
    for button in buttons:
        keyboard.append([button])
    
    return InlineKeyboardMarkup(keyboard)

def get_time_slot_buttons():
    """Generate inline keyboard buttons for pickup time slots."""
    keyboard = [
        [InlineKeyboardButton("First Shift (8:00 AM - 12:00 PM)", callback_data="time_08:00-12:00")],
        [InlineKeyboardButton("Second Shift (12:00 PM - 6:00 PM)", callback_data="time_12:00-18:00")],
        [InlineKeyboardButton("Cancel", callback_data="cancel_time")]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token("7933362470:AAEcf2GVqaxXFj2e0GF4aCXW3RHIw-6M3IM").build()

    # Set up more detailed logging
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
        level=logging.INFO
    )
    
    # Log startup information
    logger.info("Starting Qoot Bot")
    logger.info(f"MongoDB connected to {db.name}")
    logger.info(f"Collections: {db.list_collection_names()}")

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(button_callback, pattern=r"^(donate|list|digest|delete)_"),
            CallbackQueryHandler(button_callback, pattern=r"^edit_listing_"),
            CallbackQueryHandler(button_callback, pattern=r"^delete_listing_")
        ],
        states={
            DONATE_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, donate_quantity_handler)],
            LIST_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, list_quantity_handler)],
            DIGEST_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, digest_quantity_handler)],
            DELETE_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_quantity_handler)],
            PICKUP_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, pickup_date),
                CallbackQueryHandler(button_callback, pattern=r"^date_|^cancel_date")
            ],
            PICKUP_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, pickup_time),
                CallbackQueryHandler(button_callback, pattern=r"^time_|^cancel_time")
            ],
            PICKUP_LOCATION: [
                MessageHandler(filters.LOCATION, pickup_location),  # Handle location sharing
                MessageHandler(filters.TEXT & ~filters.COMMAND, pickup_location)  # Handle text input
            ],
            LISTING_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, listing_price)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Add admin message conversation handler
    admin_msg_handler = ConversationHandler(
        entry_points=[
            CommandHandler("msg", admin_message_user),
            MessageHandler(filters.Regex(r"^\/msg_\d+$"), admin_message_user)
        ],
        states={
            ADMIN_SEND_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_send_message_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(conv_handler)
    application.add_handler(admin_msg_handler)

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("barcode", generate_barcode))
    application.add_handler(CommandHandler("mybarcode", specific_barcode))
    
    # Admin command handlers
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("requests", admin_requests))
    application.add_handler(CommandHandler("users", admin_users))
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CommandHandler("user", admin_user_details))
    application.add_handler(CommandHandler("marketplace", admin_marketplace))
    
    # Special command handlers for complete_<id> pattern
    application.add_handler(MessageHandler(filters.Regex(r"^\/complete_[a-f0-9]+$"), admin_complete_request))
    application.add_handler(MessageHandler(filters.Regex(r"^\/user_\d+$"), admin_user_details))
    
    # Add marketplace callback query handler - Move this BEFORE the general callback handler
    application.add_handler(CallbackQueryHandler(button_callback, pattern=r"^(buy_|notify_|delete_listing_|edit_listing_)"))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the Bot
    application.run_polling()

if __name__ == "__main__":
    main() 