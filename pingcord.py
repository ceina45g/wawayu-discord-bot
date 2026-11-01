import sys
import types

# Python 3.13 兼容性補丁：模擬已移除的 audioop 模組
# 必須在 import discord 之前執行
try:
    import audioop
except ImportError:
    audioop_mock = types.ModuleType("audioop")
    sys.modules["audioop"] = audioop_mock

import discord
from discord.ext import commands, tasks
import time
import asyncio
import psutil
import platform
from datetime import datetime
import json
import os
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

# ===== 配置設定 =====
TOKEN = os.getenv("DISCORD_TOKEN")
PING_CHANNEL_ID = 123456789  # 請替換為你的頻道 ID

# ===== 權限檢查器 =====
def is_page_auditor():
    async def predicate(ctx):
        # 允許管理員或擁有管理員權限的使用者直接通過
        if ctx.guild and ctx.author.guild_permissions.administrator:
            return True

        # 檢查是否有「頁面審核員」身分組
        role = discord.utils.get(ctx.author.roles, name="頁面審核員")
        if role:
            return True
        
        # 如果沒有，發送提示並回傳 False
        await ctx.send("❌ 您需要至少擔任「**頁面審核員**」或具有管理員權限才能使用此功能！")
        return False
    return commands.check(predicate)

# ===== 定義機器人類別 =====
class PingBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )

        self.start_time = datetime.now()
        self.message_count = 0
        self.command_count = 0

    async def setup_hook(self):
        """啟動時的設定"""
        self.ping_status.start()
        self.metrics_report.start()

    async def on_ready(self):
        """機器人上線時觸發"""
        print(f'Pingcord bot {self.user.name} is online!')
        
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f'{len(self.guilds)} 個伺服器 | !help'
            )
        )

    @tasks.loop(seconds=30)
    async def ping_status(self):
        """每 30 秒更新一次狀態顯示"""
        if self.latency is None or str(self.latency) == "nan":
            return
            
        avg_ping = round(self.latency * 1000)

        # 根據延遲顯示不同狀態
        if avg_ping < 50:
            status = "🟢 極佳"
        elif avg_ping < 100:
            status = "良好"
        elif avg_ping < 200:
            status = "🟠 普通"
        else:
            status = "🔴 延遲"

        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f'Ping: {avg_ping}ms | {status}'
            )
        )

    @tasks.loop(minutes=5)
    async def metrics_report(self):
        """每 5 分鐘發送一次效能報告到指定頻道"""
        if PING_CHANNEL_ID and PING_CHANNEL_ID != 123456789:
            channel = self.get_channel(PING_CHANNEL_ID)
            if channel:
                embed = self.create_metrics_embed()
                await channel.send(embed=embed)

    def create_metrics_embed(self):
        """建立效能報告 Embed"""
        uptime = datetime.now() - self.start_time
        cpu_usage = psutil.cpu_percent()
        memory = psutil.virtual_memory()

        embed = discord.Embed(
            title="📊 伺服器效能報告",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )

        embed.add_field(
            name="🤖 機器人狀態",
            value=f"```\n"
                  f"延遲: {round(self.latency * 1000)}ms\n"
                  f"運行時間: {str(uptime).split('.')[0]}\n"
                  f"訊息處理: {self.message_count}\n"
                  f"指令執行: {self.command_count}\n"
                  f"```",
            inline=False
        )

        embed.add_field(
            name="💻 系統狀態",
            value=f"```\n"
                  f"CPU 使用率: {cpu_usage}%\n"
                  f"記憶體使用: {memory.percent}%\n"
                  f"可用記憶體: {memory.available // (1024**3)}GB\n"
                  f"系統: {platform.system()} {platform.release()}\n"
                  f"```",
            inline=False
        )

        embed.add_field(
            name="📈 伺服器統計",
            value=f"```\n"
                  f"伺服器數量: {len(self.guilds)}\n"
                  f"用戶總數: {sum(g.member_count for g in self.guilds)}\n"
                  f"語音頻道: {sum(len(g.voice_channels) for g in self.guilds)}\n"
                  f"文字頻道: {sum(len(g.text_channels) for g in self.guilds)}\n"
                  f"```",
            inline=False
        )

        embed.set_footer(text=f"Pingcord 監測系統")

        return embed

# ===== 建立機器人實例 =====
bot = PingBot()

# ===== 指令區 =====

@bot.command(name='ping')
async def ping(ctx):
    """檢查機器人延遲"""
    api_latency = round(bot.latency * 1000)
    start_time = time.perf_counter()
    message = await ctx.send("🏓 測量延遲中...")
    end_time = time.perf_counter()
    round_trip = round((end_time - start_time) * 1000)

    embed = discord.Embed(
        title="🏓 Ping 測量結果",
        color=discord.Color.green() if api_latency < 100 else discord.Color.orange(),
        timestamp=datetime.now()
    )

    embed.add_field(
        name="📡 API 延遲",
        value=f"```\n{api_latency}ms\n```",
        inline=True
    )

    embed.add_field(
        name="🔄 往返延遲",
        value=f"```\n{round_trip}ms\n```",
        inline=True
    )

    await message.edit(content=None, embed=embed)
    bot.command_count += 1

@bot.command(name='status')
@is_page_auditor()
async def status(ctx):
    """顯示伺服器狀態（限頁面審核員）"""
    embed = bot.create_metrics_embed()
    await ctx.send(embed=embed)
    bot.command_count += 1

@bot.command(name='add_page')
@is_page_auditor()
async def add_page(ctx, *, page_name: str):
    """新增頁面功能示範（限頁面審核員）"""
    await ctx.send(f"✅ 頁面審核員 {ctx.author.mention} 已成功新增頁面：**{page_name}**")
    bot.command_count += 1

@bot.command(name='help')
async def help_command(ctx):
    """顯示指令列表"""
    embed = discord.Embed(
        title="📚 Pingcord 指令列表",
        color=discord.Color.blue()
    )
    embed.add_field(name="!ping", value="🏓 測試延遲", inline=False)
    embed.add_field(name="!status", value="📊 查看效能報告 (限頁面審核員)", inline=False)
    embed.add_field(name="!add_page <名稱>", value="➕ 新增監測頁面 (限頁面審核員)", inline=False)
    await ctx.send(embed=embed)

# ===== 錯誤處理 =====
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        # 這裡的錯誤訊息已在 is_page_auditor 中發送，故不再重複
        pass
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ 找不到指令")
    else:
        await ctx.send(f"❌ 發生錯誤: {error}")

# ===== 啟動機器人 =====
if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("錯誤：找不到 DISCORD_TOKEN，請檢查 .env 檔案。")
