import discord
import yt_dlp
import asyncio
import random
import os
import subprocess
import sys

# ── Install ffmpeg if not present (Replit auto-handles this via replit.nix) ──
# ── Config ───────────────────────────────────────────────────────────────────
TOKEN = os.environ.get("DiscordBot")  # Set this in Replit Secrets

# Drake songs to randomly pick from
DRAKE_SONGS = [
    "Drake God's Plan",
    "Drake Hotline Bling",
    "Drake Started From The Bottom",
    "Drake One Dance",
    "Drake Passionfruit",
    "Drake Laugh Now Cry Later",
    "Drake Toosie Slide",
    "Drake Hold On We're Going Home",
    "Drake Nonstop",
    "Drake In My Feelings",
    "Drake Forever",
    "Drake Best I Ever Had",
    "Drake Marvins Room",
    "Drake HYFR",
    "Drake Headlines",
    "Drake Take Care",
    "Drake Crew Love",
    "Drake Wu-Tang Forever",
    "Drake 0 to 100",
    "Drake Energy",
    "Drake Gyalchester",
    "Drake Portland",
    "Drake Sacrifices",
    "Drake Nice For What",
    "Drake Emotionless",
    "Drake Mob Ties",
    "Drake Elevate",
    "Drake Sandra's Rose",
    "Drake Summer Games",
    "Drake Jaded",
    "Drake After Dark",
    "Drake Chicago Freestyle",
    "Drake When To Say When",
    "Drake Wants and Needs",
    "Drake What's Next",
    "Drake Knife Talk",
    "Drake Way 2 Sexy",
    "Drake TSU",
    "Drake Champagne Poetry",
    "Drake Falling Back",
]

# Drake fraud meme images
FRAUD_IMAGES = [
    "https://i.kym-cdn.com/photos/images/newsfeed/001/877/329/7b5.jpg",
    "https://i.imgflip.com/65939r.jpg",
    "https://i.imgur.com/Qv8ZPeJ.jpeg",
    "https://i.kym-cdn.com/entries/icons/original/000/039/027/cover2.jpg",
    "https://i.imgflip.com/4/3lmzyx.jpg",
]

# ── Bot Setup ─────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = discord.Client(intents=intents)

YDL_OPTS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


# ── Helpers ───────────────────────────────────────────────────────────────────
async def get_audio_url(song_query: str):
    loop = asyncio.get_event_loop()

    def _search():
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(f"ytsearch1:{song_query}", download=False)
            if info and "entries" in info and info["entries"]:
                entry = info["entries"][0]
                formats = entry.get("formats", [])
                audio_formats = [
                    f for f in formats
                    if f.get("acodec") != "none" and f.get("vcodec") == "none"
                ]
                if audio_formats:
                    return audio_formats[-1]["url"], entry.get("title", song_query)
                return entry.get("url"), entry.get("title", song_query)
        return None, None

    return await loop.run_in_executor(None, _search)


# ── Events ────────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Hatem is online as {bot.user}")


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    content = message.content.lower()

    # ── "Ouu Hatem" → play Drake in voice ──
    if "ouu hatem" in content:
        if not message.author.voice or not message.author.voice.channel:
            await message.channel.send("🎤 Get in a voice channel first bro")
            return

        voice_channel = message.author.voice.channel
        song = random.choice(DRAKE_SONGS)

        status_msg = await message.channel.send(f"🔍 Loading **{song}**...")

        try:
            audio_url, title = await get_audio_url(song)
            if not audio_url:
                await status_msg.edit(content="❌ Couldn't find that one, try again")
                return

            voice_client = message.guild.voice_client
            if voice_client:
                if voice_client.channel != voice_channel:
                    await voice_client.move_to(voice_channel)
            else:
                voice_client = await voice_channel.connect()

            if voice_client.is_playing():
                voice_client.stop()

            source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
            voice_client.play(source)

            await status_msg.edit(content=f"🎵 Now playing: **{title}**")

        except Exception as e:
            await status_msg.edit(content=f"❌ Error: {e}")

    # ── "Fraud" → send Drake meme ──
    elif "fraud" in content:
        image_url = random.choice(FRAUD_IMAGES)
        embed = discord.Embed(color=discord.Color.red())
        embed.set_image(url=image_url)
        embed.set_footer(text="🚨 FRAUD DETECTED 🚨")
        await message.channel.send(embed=embed)


# ── Run ───────────────────────────────────────────────────────────────────────
bot.run(TOKEN)
