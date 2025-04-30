import os
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeVideo
from PIL import Image
import asyncio

# Replace these with your own values from https://my.telegram.org
API_ID = '22421392'
API_HASH = '8fe2afed6114e6968352829dd0ebb916'
BOT_TOKEN = '7258581222:AAG5fC7AZgVhhnUgql-vStawz_oPB2m62Pg'

client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Store the last thumbnail for each user
user_thumbnails = {}

async def progress_callback(current, total, event):
    percent = round((current / total) * 100, 2)
    await event.edit(f"Processing... {percent}%")

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond('Send me a photo to set as thumbnail, then send videos to process them!')

@client.on(events.NewMessage(func=lambda e: e.photo))
async def handle_photo(event):
    user_id = event.sender_id
    
    # Download the photo
    photo = await event.download_media()
    
    # Open and save as thumbnail
    img = Image.open(photo)
    thumb_path = f'thumb_{user_id}.jpg'
    img.save(thumb_path, 'JPEG')
    
    user_thumbnails[user_id] = thumb_path
    os.remove(photo)
    
    await event.respond('Thumbnail set! Now send me videos to process.')

@client.on(events.NewMessage(func=lambda e: e.video or e.document))
async def handle_video(event):
    user_id = event.sender_id
    
    if user_id not in user_thumbnails:
        await event.respond('Please send a photo first to set as thumbnail!')
        return
    
    # Show progress while downloading
    progress_msg = await event.respond('Downloading video...')
    video = await event.download_media(
        progress_callback=lambda c, t: asyncio.create_task(
            progress_callback(c, t, progress_msg)
        )
    )
    
    try:
        # Get video metadata
        attributes = event.media.document.attributes
        for attr in attributes:
            if isinstance(attr, DocumentAttributeVideo):
                duration = attr.duration
                w = attr.w
                h = attr.h
                break
        
        # Upload with new thumbnail
        await progress_msg.edit('Uploading processed video...')
        await client.send_file(
            event.chat_id,
            file=video,
            thumb=user_thumbnails[user_id],
            caption=event.message.caption if event.message.caption else '',
            attributes=[DocumentAttributeVideo(
                duration=duration,
                w=w,
                h=h,
                supports_streaming=True
            )],
            progress_callback=lambda c, t: asyncio.create_task(
                progress_callback(c, t, progress_msg)
            )
        )
        
        await progress_msg.delete()
        os.remove(video)
        
    except Exception as e:
        await event.respond(f'Error processing video: {str(e)}')
        if os.path.exists(video):
            os.remove(video)

print("Bot started...")
client.run_until_disconnected()
