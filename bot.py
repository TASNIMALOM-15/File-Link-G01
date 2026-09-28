import os
import math
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# Environment Variables
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
BIN_CHANNEL = int(os.environ.get("BIN_CHANNEL"))
PORT = int(os.environ.get("PORT", 8080))
SERVER_URL = os.environ.get("SERVER_URL", "") # Render-এর সার্ভিস ইউআরএল

app = Client("StreamBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def humanbytes(size):
    if not size:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size, 1024)))
    p = math.pow(1024, i)
    s = round(size / p, 2)
    return f"{s} {size_name[i]}"

@app.on_message(filters.private & (filters.video | filters.document | filters.audio))
async def stream_handler(client, message):
    try:
        # ফাইলটি লগে ফরওয়ার্ড করা
        log_msg = await message.forward(chat_id=BIN_CHANNEL)
        file_id = log_msg.id
        
        # ফাইলের নাম ও সাইজ বের করা
        media = message.video or message.document or message.audio
        file_name = getattr(media, "file_name", "Video_File.mp4")
        file_size = humanbytes(getattr(media, "file_size", 0))
        
        # ডিরেক্ট লিঙ্ক জেনারেট
        base_url = SERVER_URL.rstrip('/')
        download_link = f"{base_url}/download/{file_id}"
        watch_link = f"{base_url}/watch/{file_id}"

        reply_text = (
            "Your Link Generated!\n\n"
            f"📂 File Name: {file_name}\n"
            f"📦 File Size: {file_size}\n\n"
            "Link Generated Using Sammo's Link Generator Bot"
        )

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Download 📥", url=download_link),
                InlineKeyboardButton("Watch 🎬", url=watch_link)
            ]
        ])

        await message.reply_text(reply_text, reply_markup=buttons, quote=True)

    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")

# কাস্টম এইচটিএমএল প্লেয়ার
async def watch_page(request):
    file_id = request.match_info['file_id']
    base_url = SERVER_URL.rstrip('/')
    stream_url = f"{base_url}/download/{file_id}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sammo's Web Player</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://cdn.plyr.io/3.7.8/plyr.css" />
        <style>
            body {{ background: #0f0f0f; color: white; margin: 0; padding: 20px; font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 90vh; }}
            .player-container {{ width: 100%; max-width: 900px; background: #000; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
            h2 {{ margin-bottom: 20px; font-size: 20px; text-align: center; color: #0088cc; }}
        </style>
    </head>
    <body>
        <h2>Sammo's Video Player 🍿</h2>
        <div class="player-container">
            <video id="player" playsinline controls>
                <source src="{stream_url}" type="video/mp4" />
            </video>
        </div>
        <script src="https://cdn.plyr.io/3.7.8/plyr.js"></script>
        <script>
            const player = new Plyr('#player', {{
                controls: ['play-large', 'play', 'progress', 'current-time', 'mute', 'volume', 'captions', 'settings', 'pip', 'airplay', 'fullscreen'],
                settings: ['captions', 'quality', 'speed']
            }});
        </script>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type='text/html')

async def download_handler(request):
    file_id = int(request.match_info['file_id'])
    try:
        msg = await app.get_messages(BIN_CHANNEL, file_id)
        media = msg.video or msg.document or msg.audio
        
        response = web.StreamResponse(
            status=200,
            headers={
                'Content-Type': 'video/mp4',
                'Content-Disposition': f'attachment; filename="{getattr(media, "file_name", "video.mp4")}"'
            }
        )
        await response.prepare(request)
        
        async for chunk in app.stream_media(msg):
            await response.write(chunk)
            
        return response
    except Exception as e:
        return web.Response(text=str(e), status=500)

async def start_web():
    web_app = web.Application()
    web_app.router.add_get('/watch/{file_id}', watch_page)
    web_app.router.add_get('/download/{file_id}', download_handler)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

async def main():
    await app.start()
    await start_web()
    await asyncio.Event().wait()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
