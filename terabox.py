import os
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.enums import ChatMemberStatus
from dotenv import load_dotenv
from pymongo import MongoClient
from status import format_progress_bar
from video import download_video, upload_video

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('config.env', override=True)

# Get configuration from environment variables with validation
def get_env_var(name, default=None):
    value = os.environ.get(name, default)
    if not value:
        logger.error(f"{name} environment variable is missing! Exiting now")
        exit(1)
    return value

try:
    # Required configuration
    API_ID = int(get_env_var('API_ID'))
    API_HASH = get_env_var('API_HASH')
    BOT_TOKEN = get_env_var('BOT_TOKEN')
    DUMP_CHAT_ID = int(get_env_var('DUMP_CHAT_ID'))
    FSUB_ID = int(get_env_var('FSUB_ID'))
    MONGO_URL = get_env_var('MONGO_URL')
    
    # Optional configuration with defaults
    ADMIN_ID = int(os.environ.get('ADMIN_ID', 6695586027))
    MAX_FILE_SIZE = int(os.environ.get('MAX_FILE_SIZE', 120))  # in MB
    
except ValueError as e:
    logger.error(f"Configuration error: {str(e)}")
    exit(1)

# MongoDB setup with error handling
try:
    mongo_client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    mongo_client.server_info()  # Test connection
    db = mongo_client['uphdlust']
    users_collection = db['users']
    logger.info("Successfully connected to MongoDB")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    exit(1)

def save_user(user_id: int, username: str):
    """Save user to database if not already exists"""
    try:
        if users_collection.find_one({'user_id': user_id}) is None:
            users_collection.insert_one({
                'user_id': user_id,
                'username': username,
                'join_date': datetime.utcnow()
            })
            logger.info(f"New user saved: {username} (ID: {user_id})")
    except Exception as e:
        logger.error(f"Error saving user {user_id}: {e}")

# Initialize Pyrogram client
app = Client(
    name="terabox_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=100,
    sleep_threshold=10
)

@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """Handle /start command"""
    user = message.from_user
    save_user(user.id, user.username)

    # Send sticker and delete after 2 seconds
    sticker = await message.reply_sticker("CAACAgIAAxkBAAEYonplzwrczhVu3I6HqPBzro3L2JU6YAACvAUAAj-VzAoTSKpoG9FPRjQE")
    await asyncio.sleep(2)
    await sticker.delete()

    # Create welcome message with buttons
    welcome_msg = (
        f"ᴡᴇʟᴄᴏᴍᴇ, {user.mention}.\n\n"
        "🌟 ɪ ᴀᴍ ᴀ ᴛᴇʀᴀʙᴏx ᴅᴏᴡɴʟᴏᴀᴅᴇʀ ʙᴏᴛ. "
        "sᴇɴᴅ ᴍᴇ ᴀɴʏ ᴛᴇʀᴀʙᴏx ʟɪɴᴋ ɪ ᴡɪʟʟ ᴅᴏᴡɴʟᴏᴀᴅ ᴡɪᴛʜɪɴ ғᴇᴡ sᴇᴄᴏɴᴅs ᴀɴᴅ sᴇɴᴅ ɪᴛ ᴛᴏ ʏᴏᴜ ✨."
    )
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("ᴊᴏɪɴ ❤️🚀", url="https://t.me/ultroid_official"),
            InlineKeyboardButton("ᴅᴇᴠᴇʟᴏᴘᴇʀ ⚡️", url="https://t.me/ultroidxTeam")
        ]
    ])
    
    await message.reply_text(welcome_msg, reply_markup=buttons)

async def check_membership(client: Client, user_id: int) -> bool:
    """Check if user is member of required channel"""
    try:
        member = await client.get_chat_member(FSUB_ID, user_id)
        return member.status in [
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER
        ]
    except Exception as e:
        logger.error(f"Membership check failed for {user_id}: {e}")
        return False

@app.on_message(filters.text & ~filters.command)
async def handle_terabox_link(client: Client, message: Message):
    """Process Terabox links"""
    user = message.from_user
    save_user(user.id, user.username)

    # Check channel membership
    if not await check_membership(client, user.id):
        button = InlineKeyboardButton("ᴊᴏɪɴ ❤️🚀", url="https://t.me/ultroid_official")
        await message.reply_text(
            "ʏᴏᴜ ᴍᴜsᴛ ᴊᴏɪɴ ᴍʏ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴜsᴇ ᴍᴇ.",
            reply_markup=InlineKeyboardMarkup([[button]])
        )
        return

    # Validate Terabox link
    terabox_link = message.text.strip()
    if "terabox" not in terabox_link.lower():
        await message.reply_text("ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴀ ᴠᴀʟɪᴅ ᴛᴇʀᴀʙᴏx ʟɪɴᴋ.")
        return

    # Process the download
    status_msg = await message.reply_text("sᴇɴᴅɪɴɢ ʏᴏᴜ ᴛʜᴇ ᴍᴇᴅɪᴀ...🤤")

    try:
        file_path, thumbnail_path, video_title = await download_video(
            terabox_link, 
            status_msg, 
            user.mention, 
            user.id
        )
        
        await upload_video(
            client,
            file_path,
            thumbnail_path,
            video_title,
            status_msg,
            DUMP_CHAT_ID,
            user.mention,
            user.id,
            message
        )
        
    except Exception as e:
        logger.error(f"Error processing {terabox_link}: {e}")
        await status_msg.edit_text(
            f"ғᴀɪʟᴇᴅ ᴛᴏ ᴘʀᴏᴄᴇss ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ.\n"
            f"ɪғ ʏᴏᴜʀ ғɪʟᴇ sɪᴢᴇ ɪs ᴍᴏʀᴇ ᴛʜᴀɴ {MAX_FILE_SIZE}ᴍʙ ɪᴛ ᴍɪɢʜᴛ ғᴀɪʟ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ."
        )

@app.on_message(filters.command("broadcast") & filters.user(ADMIN_ID))
async def broadcast_command(client: Client, message: Message):
    """Broadcast message to all users (admin only)"""
    if len(message.command) < 2:
        await message.reply_text("Please provide a message to broadcast.")
        return

    broadcast_msg = message.text.split(maxsplit=1)[1]
    total_users = users_collection.count_documents({})
    success = 0
    failed = 0

    status_msg = await message.reply_text(f"Broadcasting to {total_users} users...")

    async for user in users_collection.find():
        try:
            await client.send_message(user['user_id'], broadcast_msg)
            success += 1
        except Exception as e:
            logger.error(f"Failed to send to {user['user_id']}: {e}")
            failed += 1
        finally:
            if (success + failed) % 10 == 0:  # Update every 10 sends
                await status_msg.edit_text(
                    f"Broadcast progress:\n"
                    f"✅ Success: {success}\n"
                    f"❌ Failed: {failed}\n"
                    f"Total: {total_users}"
                )

    await status_msg.edit_text(
        f"Broadcast completed!\n"
        f"✅ Success: {success}\n"
        f"❌ Failed: {failed}"
    )

if __name__ == "__main__":
    logger.info("Starting bot...")
    app.run()
