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
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

# --- 1. 設定機器人 ---
# '!' 是觸發機器人指令的前綴 (Prefix)
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

# --- 2. 當機器人準備好時，在終端機顯示訊息 ---
@bot.event
async def on_ready():
    print(f'機器人已登入為 {bot.user}')

# --- 3. 定義一個 'play' 指令 ---
@bot.command()
async def play(ctx, *, search: str):
    """
    當使用者輸入 !play 歌曲名稱 時，機器人會請 FredBoat 播放音樂。
    """
    # 檢查指令是否在文字頻道中發出
    if isinstance(ctx.channel, discord.TextChannel):
        # 建構要傳送給 FredBoat 的指令
        # 注意：FredBoat 的預設前綴是 ';;'[reference:5]，但更建議使用斜線指令 '/play'[reference:6]
        # 這裡使用 ';;play' 作為範例
        command_to_send = f';;play {search}'

        # 讓你的機器人在同一個頻道發送訊息，以控制 FredBoat
        await ctx.send(command_to_send)
        print(f"已傳送指令: {command_to_send}")

# --- 4. 定義一個 'yee' 指令來操作 Yee 式機器龍 ---
@bot.command()
async def yee(ctx, *, search: str):
    """
    當使用者輸入 !yee 歌曲名稱 時，機器人會叫 Yee 式機器龍播放音樂。
    """
    if isinstance(ctx.channel, discord.TextChannel):
        # Yee 式機器龍的預設前綴通常是 'y!'
        command_to_send = f'y!play {search}'

        await ctx.send(command_to_send)
        print(f"已傳送 Yee 指令: {command_to_send}")

# --- 5. 執行程式 ---
token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("錯誤：找不到 DISCORD_TOKEN，請檢查 .env 檔案。")
