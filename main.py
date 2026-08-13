import discord
import yt_dlp
import asyncio
import random
import os

# ── Config ───────────────────────────────────────────────────────────────────
TOKEN = os.environ.get("DISCORD_TOKEN")

CLIP_SECONDS = 25  # length of the Drake clip to send

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
    # From Iceman (2026)
    "Drake Make Them Cry",
    "Drake Dust",
    "Drake Whisper My Name",
    "Drake Janice STFU",
    "Drake Ran To Atlanta",
    "Drake Shabang",
    "Drake Make Them Pay",
    "Drake Burning Bridges",
    "Drake National Treasures",
    "Drake B's On The Table",
    "Drake What Did I Miss",
    "Drake Plot Twist",
    "Drake 2 Hard 4 The Radio",
    "Drake Make Them Remember",
    "Drake Little Birdie",
    "Drake Don't Worry",
    "Drake Firm Friends",
    "Drake Make Them Know",
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
    "outtmpl": "/tmp/hatem_%(id)s.%(ext)s",
}


# ── Helpers ───────────────────────────────────────────────────────────────────
async def download_song(song_query: str):
    """Downloads the full song audio to /tmp and returns (filepath, title, duration)."""
    loop = asyncio.get_event_loop()

    def _download():
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(f"ytsearch1:{song_query}", download=True)
            if "entries" in info:
                info = info["entries"][0]
            filepath = ydl.prepare_filename(info)
            return filepath, info.get("title", song_query), int(info.get("duration") or 180)

    return await loop.run_in_executor(None, _download)


async def trim_clip(input_path: str, output_path: str, start: int, duration: int):
    """Uses ffmpeg to cut a short clip and export it as mp3."""
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start), "-t", str(duration),
        "-i", input_path,
        "-vn", "-acodec", "libmp3lame", "-ab", "128k",
        output_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
    )
    await proc.wait()


async def cleanup_files(*paths, delay: int = 30):
    await asyncio.sleep(delay)
    for p in paths:
        try:
            os.remove(p)
        except OSError:
            pass


# ── Events ────────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Hatem is online as {bot.user}")


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    content = message.content.lower()

    # ── "Ouu Hatem" → send a Drake clip as a playable audio message in chat ──
    if "ouu hatem" in content:
        song = random.choice(DRAKE_SONGS)
        status_msg = await message.channel.send(f"🎙️ Pulling a clip from **{song}**...")

        try:
            filepath, title, duration = await download_song(song)

            # pick a random start point so it's not always the intro
            max_start = max(0, duration - CLIP_SECONDS - 5)
            start = random.randint(0, max_start) if max_start > 0 else 0

            clip_path = filepath.rsplit(".", 1)[0] + "_clip.mp3"
            await trim_clip(filepath, clip_path, start, CLIP_SECONDS)

            await status_msg.edit(content=f"🎙️ **{title}**")
            await message.channel.send(file=discord.File(clip_path, filename="hatem_clip.mp3"))

            # if the person is also in a voice channel, play it live there too
            if message.author.voice and message.author.voice.channel:
                voice_channel = message.author.voice.channel
                voice_client = message.guild.voice_client
                if voice_client:
                    if voice_client.channel != voice_channel:
                        await voice_client.move_to(voice_channel)
                else:
                    voice_client = await voice_channel.connect()

                if voice_client.is_playing():
                    voice_client.stop()

                source = discord.FFmpegPCMAudio(clip_path)
                voice_client.play(source)

            asyncio.create_task(cleanup_files(filepath, clip_path))

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
if not TOKEN:
    raise SystemExit("❌ DISCORD_TOKEN environment variable is not set")

bot.run(TOKEN)
