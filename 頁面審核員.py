import discord
from discord.ext import commands
import re

# 機器人權限設定
intents = discord.Intents.default()
intents.message_content = True  # 務必開啟，才能讀取訊息內容[reference:3]

bot = commands.Bot(command_prefix='!', intents=intents)

# 網域黑名單（可自行新增）
BLACKLISTED_DOMAINS = ['bad-site.com', 'phishing-link.net', 'nsfw-ads.org']

# 當機器人準備好時
@bot.event
async def on_ready():
    print(f'已登入為 {bot.user}')

# 監聽每一則訊息
@bot.event
async def on_message(message):
    if message.author == bot.user:  # 避免機器人審核自己
        return

    # 1. 檢查訊息中是否包含連結
    urls = re.findall(r'(https?://[^\s]+)', message.content)
    if urls:
        for url in urls:
            # 2. 檢查連結是否包含黑名單網域
            for domain in BLACKLISTED_DOMAINS:
                if domain in url:
                    # 3. 執行審核動作：刪除訊息並警告
                    await message.delete()
                    await message.channel.send(
                        f'{message.author.mention}，你的訊息包含被封鎖的連結：{domain}',
                        delete_after=5
                    )
                    print(f'已刪除 {message.author} 的訊息，原因：黑名單網域 {domain}')
                    return  # 處理完畢後跳出

    # 讓機器人也能處理其他命令（如果有）
    await bot.process_commands(message)

# 啟動機器人（請替換為你的 Token）
bot.run('YOUR_BOT_TOKEN')