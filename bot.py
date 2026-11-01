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
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

intents = discord.Intents.all()
# 同時支援 $、% 與 ! 前綴
bot = commands.Bot(command_prefix = ["$", "%", "!"], intents = intents)

# 當機器人完成啟動時
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Done: 目前登入身份 --> {bot.user}")
        print(f"Done: 已同步 {len(synced)} 個斜線指令")
    except Exception as e:
        print(f"Error: 斜線指令同步失敗: {e}")

# 載入指令程式檔案
@bot.command()
async def load(ctx, extension):
    await bot.load_extension(f"cogs.{extension}")
    await ctx.send(f"Loaded {extension} done.")

# 卸載指令檔案
@bot.command()
async def unload(ctx, extension):
    await bot.unload_extension(f"cogs.{extension}")
    await ctx.send(f"UnLoaded {extension} done.")

# 重新載入程式檔案
@bot.command()
async def reload(ctx, extension):
    await bot.reload_extension(f"cogs.{extension}")
    await ctx.send(f"ReLoaded {extension} done.")

# 一開始bot開機需載入全部程式檔案
async def load_extensions():
    if not os.path.exists("./cogs"):
        os.makedirs("./cogs")
        
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"成功載入擴展: {filename}")
            except Exception as e:
                print(f"擴展載入失敗 {filename}: {e}")

async def main():
    async with bot:
        await load_extensions()
        # 從環境變數讀取 Token
        token = os.getenv("DISCORD_TOKEN")
        if token:
            await bot.start(token)
        else:
            print("錯誤：找不到 DISCORD_TOKEN，請檢查 .env 檔案。")

# 確定執行此py檔才會執行
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
