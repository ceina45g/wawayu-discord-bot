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

# --- 設定區域 ---
# 啟用必要的意圖 (Intents)，才能讀取成員列表
intents = discord.Intents.default()
intents.members = True
# 如果要追蹤訊息數量，需啟用 message_content 意圖
intents.message_content = True
# --- 設定結束 ---

bot = commands.Bot(command_prefix="!", intents=intents)

# 簡易訊息計數器（存在記憶體中，重啟會歸零）
# 進階用法可改用 sqlite3 或 JSON 檔案儲存
message_counts = {}

@bot.event
async def on_ready():
    print(f"serverstats bot {bot.user} is online!")

@bot.event
async def on_message(message):
    # 忽略機器人自己的訊息
    if message.author.bot:
        return

    # 記錄該伺服器的訊息數量
    if message.guild:
        guild_id = message.guild.id
        message_counts[guild_id] = message_counts.get(guild_id, 0) + 1

    # 讓指令可以被觸發
    await bot.process_commands(message)

@bot.command(name="serverstats")
async def server_stats(ctx):
    """顯示當前 Discord 伺服器的詳細統計數據"""
    guild = ctx.guild

    # 1. 統計成員數量（包含人類與機器人）
    total_members = guild.member_count
    humans = sum(1 for m in guild.members if not m.bot)
    bots = total_members - humans

    # 2. 統計頻道數量
    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)
    categories = len(guild.categories)
    total_channels = len(guild.channels)

    # 3. 統計身分組與表情符號
    roles = len(guild.roles) - 1  # 扣掉 @everyone
    emojis = len(guild.emojis)

    # 4. 統計在線狀態（需啟用 Presence Intent）
    online = sum(1 for m in guild.members if m.status != discord.Status.offline)

    # 5. 獲取訊息數量（從簡易計數器讀取）
    msg_count = message_counts.get(guild.id, 0)

    # 建立嵌入訊息
    embed = discord.Embed(
        title=f"📊 {guild.name} 伺服器統計",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )

    # 加入統計欄位
    embed.add_field(name="👥 成員", value=f"總計：{total_members}\n人類：{humans}\n機器人：{bots}", inline=True)
    embed.add_field(name="💬 頻道", value=f"總計：{total_channels}\n文字：{text_channels}\n語音：{voice_channels}\n分類：{categories}", inline=True)
    embed.add_field(name="🛡️ 其他", value=f"身分組：{roles}\n表情符號：{emojis}", inline=True)
    embed.add_field(name="🟢 在線", value=f"{online} / {total_members} 人", inline=True)
    embed.add_field(name="✉️ 訊息數", value=f"已記錄 {msg_count} 則訊息", inline=True)

    embed.set_footer(text=f"伺服器 ID：{guild.id}")

    await ctx.send(embed=embed)

# 啟動機器人
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("錯誤：找不到 DISCORD_TOKEN，請檢查 .env 檔案。")
