import discord
from discord.ext import commands
import random

# 1. 設定 Intents (權限意圖)
# 啟用預設的 Intents 並手動打開讀取訊息內容的權限
intents = discord.Intents.default()
intents.message_content = True  # 讓機器人可以讀取訊息內容
intents.members = True          # 讓機器人可以監聽成員加入事件

# 2. 創建 Bot 實例
# 設定前綴為 '!'，這樣使用者輸入 !hello 就能觸發指令
bot = commands.Bot(command_prefix='!', intents=intents)

# ==================== 事件 (Events) ====================
# 當機器人成功啟動並連線到 Discord 時觸發
@bot.event
async def on_ready():
    print(f'已登入為 {bot.user} (ID: {bot.user.id})')
    print('------')

# 當有新成員加入伺服器時觸發
@bot.event
async def on_member_join(member):
    # 尋找名為 "general" 的頻道並發送歡迎訊息[citation:4]
    channel = discord.utils.get(member.guild.text_channels, name="general")
    if channel:
        await channel.send(f'歡迎 {member.mention} 加入伺服器！🎉')

# 監聽所有訊息（可以做為關鍵字回應，類似 MEE6 的自動回覆功能）
@bot.event
async def on_message(message):
    # 避免機器人回應自己的訊息，造成無限循環[citation:1]
    if message.author == bot.user:
        return

    # 簡單的關鍵字回應
    if '你好' in message.content:
        await message.channel.send(f'嗨 {message.author.mention}！')

    # 記得要讓 bot 處理指令（這行不能省略，否則 ! 開頭的指令會失效）
    await bot.process_commands(message)

# ==================== 指令 (Commands) ====================
# 一個簡單的 ping 指令，用來測試機器人延遲
@bot.command()
async def ping(ctx):
    """回應 Pong! 並顯示延遲毫秒數"""
    await ctx.send(f'Pong! {round(bot.latency * 1000)}ms')

# 一個擲骰子指令，格式為 NdN (例如 !roll 2d6)
@bot.command()
async def roll(ctx, dice: str):
    """擲骰子，格式為 NdN (例如: !roll 2d6)"""
    try:
        rolls, limit = map(int, dice.split('d'))
    except ValueError:
        await ctx.send('格式錯誤，請使用 NdN 格式 (例如: 2d6)')
        return

    if rolls > 20 or limit > 100:
        await ctx.send('請不要輸入太大的數字，最多 20d100')
        return

    results = [random.randint(1, limit) for _ in range(rolls)]
    await ctx.send(f'🎲 擲骰結果 ({dice})：{", ".join(map(str, results))} (總和: {sum(results)})')

# 執行機器人
if __name__ == "__main__":
    bot.run('你的機器人Token') # 請務必替換成你的 Token