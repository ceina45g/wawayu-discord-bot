import sys
import types

# Python 3.13 兼容性補丁：模擬已移除的 audioop 模組
# 必須在 import discord 之前執行
try:
    import audioop
except ImportError:
    audioop_mock = types.ModuleType("audioop")
    sys.modules["audioop"] = audioop_mock

import os
import discord
from discord.ext import commands
import random
import asyncio
import yt_dlp
import re
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

# ========== 音樂播放設定 ==========
yt_dlp_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_opts = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(yt_dlp_opts)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        
        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_opts), data=data)

# ========== 機器人設定 ==========
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# 音樂隊列
music_queues = {}
# 動態語音頻道設定
creator_channel_id = None
temporary_channels = []

def check_queue(ctx):
    if music_queues[ctx.guild.id]:
        source = music_queues[ctx.guild.id].pop(0)
        ctx.voice_client.play(source, after=lambda e: check_queue(ctx))

# ========== 啟動事件 ==========
@bot.event
async def on_ready():
    print(f"yee dragon bot logged in: {bot.user}")
    await bot.change_presence(activity=discord.Game(name="🐉 噴火中！輸入 !play 聽音樂"))

# ========== 基本回應 ==========
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    msg = message.content.lower()
    
    # 檢查是否擁有 Collab.Land 身分組 (名稱需與 Discord 伺服器中一致)
    has_collab_role = False
    if message.guild:
        has_collab_role = discord.utils.get(message.author.roles, name="Collab.Land") is not None

    if "yww式機器龍" in msg:
        if has_collab_role:
            await message.channel.send(f"🔥 **{message.author.display_name}** 召喚了 yww 式機器龍！🐉\n> 嗷嗚～～～～～")
        else:
            await message.channel.send(f"⚠️ {message.author.mention}，只有經過 Collab.Land 驗證的勇者才能召喚 yww 式機器龍！")
    elif "yee式機器幼龍" in msg:
        if has_collab_role:
            await message.channel.send(f"🐣 **{message.author.display_name}** 召喚了 yee 式機器幼龍！🦖\n> 嘰哩呱啦～～")
        else:
            await message.channel.send(f"⚠️ {message.author.mention}，只有經過 Collab.Land 驗證的勇者才能召喚 yee 式機器幼龍！")
    elif "yee" in msg:
        if has_collab_role:
            await message.channel.send(f"🔥 **{message.author.display_name}** 召喚了 yee 式機器龍！🐉\n> 吼～～～～～")
        else:
            await message.channel.send(f"⚠️ {message.author.mention}，只有經過 Collab.Land 驗證的勇者才能召喚 yee 式機器龍！")
    elif "早安" in msg or "早" in msg:
        await message.channel.send(f"🌞 早啊 {message.author.mention}，龍龍今天也想噴火！")
    elif "噴火" in msg:
        fire = random.choice(["🔥🔥🔥", "🐉💨💥", "🔥 吼！", "🔥 燒毀～～"])
        await message.channel.send(f"{fire} 龍龍對你噴火！")

    await bot.process_commands(message)

# ========== 動態語音事件 ==========
@bot.event
async def on_voice_state_update(member, before, after):
    global creator_channel_id
    
    # 1. 偵測是否進入「創建中心」
    if after.channel and after.channel.id == creator_channel_id:
        guild = member.guild
        category = after.channel.category
        
        # 創建暫時頻道
        new_channel = await guild.create_voice_channel(
            name=f"🐲 {member.display_name} 的小巢",
            category=category,
            reason="動態語音頻道創建"
        )
        
        # 將成員移入新頻道
        await member.move_to(new_channel)
        temporary_channels.append(new_channel.id)
        print(f"Done: 為 {member.display_name} 創建了動態頻道 {new_channel.id}")

    # 2. 偵測是否離開暫時頻道，若頻道空了就刪除
    if before.channel and before.channel.id in temporary_channels:
        if len(before.channel.members) == 0:
            await before.channel.delete(reason="動態語音頻道無人，自動刪除")
            temporary_channels.remove(before.channel.id)
            print(f"Done: 刪除了空的動態頻道 {before.channel.id}")

# ========== 音樂指令 ==========

@bot.command()
async def join(ctx):
    """進入語音頻道"""
    if not ctx.author.voice:
        return await ctx.send("❌ 你必須先進入一個語音頻道！")
    
    channel = ctx.author.voice.channel
    if ctx.voice_client:
        await ctx.voice_client.move_to(channel)
    else:
        await channel.connect()
    await ctx.send(f"✅ 已進入語音頻道：{channel.name}")

@bot.command()
async def play(ctx, *, search: str):
    """播放音樂 (支援 YouTube/Spotify 搜尋)"""
    if not ctx.voice_client:
        await ctx.invoke(bot.get_command('join'))

    async with ctx.typing():
        # Spotify 處理 (簡易轉向 YouTube 搜尋)
        if "open.spotify.com" in search:
            await ctx.send("🎵 偵測到 Spotify 連結，正在尋找最佳音訊源...")
            # 這裡只做簡單的字串清理，實務上可解析網址抓標題
            search = search.split('?')[0] 
        
        try:
            player = await YTDLSource.from_url(search, loop=bot.loop, stream=True)
            
            if not ctx.voice_client.is_playing():
                ctx.voice_client.play(player, after=lambda e: check_queue(ctx))
                await ctx.send(f"🔥 **正在播放：** {player.title}")
            else:
                if ctx.guild.id not in music_queues:
                    music_queues[ctx.guild.id] = []
                music_queues[ctx.guild.id].append(player)
                await ctx.send(f"✅ **已加入隊列：** {player.title}")
        except Exception as e:
            await ctx.send(f"❌ 發生錯誤: {e}")

@bot.command()
async def skip(ctx):
    """跳過當前歌曲"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ 已跳過歌曲")
    else:
        await ctx.send("❌ 目前沒有正在播放的音樂")

@bot.command()
async def stop(ctx):
    """停止播放並清除隊列"""
    if ctx.guild.id in music_queues:
        music_queues[ctx.guild.id] = []
    if ctx.voice_client:
        ctx.voice_client.stop()
    await ctx.send("⏹️ 已停止播放並清空隊列")

@bot.command()
async def leave(ctx):
    """離開語音頻道"""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        if ctx.guild.id in music_queues:
            music_queues[ctx.guild.id] = []
        await ctx.send("👋 已離開語音頻道")
    else:
        await ctx.send("❌ 我目前不在語音頻道內")

# ========== 動態語音指令 ==========

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_vc(ctx):
    """一鍵設定動態語音系統 (管理員專用)"""
    global creator_channel_id
    
    guild = ctx.guild
    
    # 創建分類
    category = await guild.create_category("🔊 動態語音系統")
    
    # 創建中心頻道
    creator_channel = await guild.create_voice_channel(
        "➕ 點我創建頻道",
        category=category,
        reason="動態語音系統初始化"
    )
    
    creator_channel_id = creator_channel.id
    await ctx.send(f"✅ 動態語音系統已完成設定！\n📌 創建中心：{creator_channel.mention}\n💡 只要進入該頻道，龍龍就會幫你開小房間喔！")

# ========== 蝦皮功能 ==========

@bot.command(name="shopee_thread", aliases=["st", "蝦皮討論"])
async def shopee_thread(ctx, *, title: str):
    """在蝦皮購物頻道建立一個新的討論串 (用法: !st [討論標題])"""
    # 檢查是否在蝦皮相關頻道
    if "蝦皮" not in ctx.channel.name:
        return await ctx.send("❌ 吼！請在「蝦皮購物」相關頻道中使用此指令，龍龍才能幫你推坑！")

    try:
        # 在發送的指令訊息下建立討論串
        thread = await ctx.message.create_thread(
            name=f"🛒 蝦皮討論：{title}",
            auto_archive_duration=1440  # 1天後自動存檔
        )
        
        # 準備 Embed 訊息
        embed = discord.Embed(
            title=f"🛍️ 龍龍推坑團：{title}",
            description=(
                f"新的討論串已經開啟！\n\n"
                f"👤 **發起人：** {ctx.author.mention}\n"
                f"📌 **主題：** {title}\n\n"
                "大家快來分享優惠連結或心得吧！吼～～～ 🐉🔥"
            ),
            color=discord.Color.orange()
        )
        
        # 嘗試設置機器人頭像作為小圖
        if bot.user.display_avatar:
            embed.set_thumbnail(url=bot.user.display_avatar.url)
            
        embed.set_footer(text="yee式機器龍 · 蝦皮特派員")
        
        # 在討論串內發送歡迎訊息
        await thread.send(embed=embed)
        
        # 在原頻道確認建立成功
        await ctx.send(f"✅ 成功建立討論串：{thread.mention}，大家快進去討論！")
        
    except Exception as e:
        await ctx.send(f"❌ 建立討論串失敗了吼：{e}")

@bot.command(name="shopee_invite", aliases=["si", "蝦皮邀請"])
async def shopee_invite(ctx, max_uses: int = 0, max_age: int = 0):
    """生成蝦皮購物頻道的邀請連結 (用法: !si [次數] [秒數])"""
    # 尋找名稱包含「蝦皮」的頻道
    target_channel = None
    for channel in ctx.guild.text_channels:
        if "蝦皮" in channel.name:
            target_channel = channel
            break
    
    if not target_channel:
        target_channel = ctx.channel
        await ctx.send("⚠️ 找不到名稱包含「蝦皮」的頻道，將改為當前頻道生成邀請。")

    try:
        invite = await target_channel.create_invite(
            max_uses=max_uses,
            max_age=max_age,
            unique=True,
            reason=f"蝦皮特派員 {ctx.author.name} 要求生成"
        )

        embed = discord.Embed(
            title="🧡 蝦皮購物文字頻道 - 邀請函 🧡",
            description=f"快來加入蝦皮購物討論區！這裡有最新優惠與推坑心得！吼～～ 🐉",
            color=0xEE4D2D # 蝦皮橘
        )
        embed.add_field(name="🔗 專屬連結", value=f"[點擊進入頻道]({invite.url})", inline=False)
        embed.add_field(name="📢 目標頻道", value=target_channel.mention, inline=True)
        embed.add_field(name="🔢 限制/期限", value=f"{'無限' if max_uses == 0 else max_uses}次 / {'永久' if max_age == 0 else max_age}秒", inline=True)
        
        embed.set_thumbnail(url="https://cf.shopee.tw/file/a47738096f30d09995c7cf1b3769c27f")
        embed.set_footer(text=f"龍龍強力推薦 · 由 {ctx.author.display_name} 發起", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ 生成邀請失敗了吼：{e}")

# ========== 其他指令 ==========
@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong！延遲：{round(bot.latency * 1000)}ms")

# ========== 啟動機器人 ==========
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("錯誤：找不到 DISCORD_TOKEN，請檢查 .env 檔案。")
