import discord
from discord.ext import commands, tasks
import time
import asyncio
import psutil
import platform
from datetime import datetime
import json
import os
import aiohttp  # 需要安裝 aiohttp

# ===== 配置設定 =====
TOKEN = '你的 Discord Bot Token'
PING_CHANNEL_ID = 123456789          # 用於發送報告的 Discord 頻道 ID
WEBHOOK_URL = 'https://你的webhook.url/endpoint'  # 外部 Webhook 網址（可選）
WEBHOOK_ENABLED = bool(WEBHOOK_URL)  # 若未設定則自動停用

# ===== Webhook 發送器 =====
class WebhookSender:
    """非同步 Webhook 發送器"""
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
        self.session = None

    async def _get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def send(self, data, retries=3):
        """發送 JSON 數據到 Webhook"""
        if not self.webhook_url:
            return False

        session = await self._get_session()
        for attempt in range(retries):
            try:
                async with session.post(
                        self.webhook_url,
                        json=data,
                        headers={'Content-Type': 'application/json'},
                        timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status in (200, 204):
                        return True
                    else:
                        print(f"Webhook 回應錯誤: {resp.status} - {await resp.text()}")
            except Exception as e:
                print(f"Webhook 發送失敗 (嘗試 {attempt+1}/{retries}): {e}")
                await asyncio.sleep(2 ** attempt)  # 指數退避
        return False

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

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
        self.webhook = WebhookSender(WEBHOOK_URL) if WEBHOOK_ENABLED else None

    async def setup_hook(self):
        """啟動時的設定"""
        self.ping_status.start()
        self.metrics_report.start()

    async def close(self):
        """關閉時清理 Webhook session"""
        if self.webhook:
            await self.webhook.close()
        await super().close()

    async def on_ready(self):
        """機器人上線時觸發"""
        print(f'✅ 已登入為 {self.user.name}')
        print(f'✅ 機器人 ID: {self.user.id}')
        print(f'✅ 延遲: {round(self.latency * 1000)}ms')
        print(f'✅ 已連線到 {len(self.guilds)} 個伺服器')
        print(f'✅ Webhook 狀態: {"啟用" if WEBHOOK_ENABLED else "停用"}')

        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f'{len(self.guilds)} 個伺服器 | !help'
            )
        )

    @tasks.loop(seconds=30)
    async def ping_status(self):
        """每 30 秒更新狀態顯示"""
        avg_ping = round(self.latency * 1000)
        if avg_ping < 50:
            status = "🟢 極佳"
        elif avg_ping < 100:
            status = "🟡 良好"
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
        """每 5 分鐘發送效能報告（Discord 頻道 + Webhook）"""
        embed = self.create_metrics_embed()
        # 發送到 Discord 頻道
        if PING_CHANNEL_ID:
            channel = self.get_channel(PING_CHANNEL_ID)
            if channel:
                await channel.send(embed=embed)

        # 發送到 Webhook
        if self.webhook:
            report_data = self.build_webhook_payload()
            await self.webhook.send(report_data)

    def create_metrics_embed(self):
        """建立 Discord Embed 報告"""
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
            value=f"```\n延遲: {round(self.latency * 1000)}ms\n運行時間: {str(uptime).split('.')[0]}\n訊息處理: {self.message_count}\n指令執行: {self.command_count}\n```",
            inline=False
        )
        embed.add_field(
            name="💻 系統狀態",
            value=f"```\nCPU 使用率: {cpu_usage}%\n記憶體使用: {memory.percent}%\n可用記憶體: {memory.available // (1024**3)}GB\n系統: {platform.system()} {platform.release()}\n```",
            inline=False
        )
        embed.add_field(
            name="📈 伺服器統計",
            value=f"```\n伺服器數量: {len(self.guilds)}\n用戶總數: {sum(g.member_count for g in self.guilds)}\n語音頻道: {sum(len(g.voice_channels) for g in self.guilds)}\n文字頻道: {sum(len(g.text_channels) for g in self.guilds)}\n```",
            inline=False
        )
        embed.set_footer(text="Pingcord 監測系統")
        return embed

    def build_webhook_payload(self):
        """建立 Webhook 的 JSON 資料"""
        uptime = datetime.now() - self.start_time
        cpu_usage = psutil.cpu_percent()
        memory = psutil.virtual_memory()

        return {
            "timestamp": datetime.now().isoformat(),
            "bot": {
                "name": self.user.name,
                "id": self.user.id,
                "latency_ms": round(self.latency * 1000),
                "uptime_seconds": uptime.total_seconds(),
                "message_count": self.message_count,
                "command_count": self.command_count,
                "guild_count": len(self.guilds),
                "total_members": sum(g.member_count for g in self.guilds)
            },
            "system": {
                "cpu_percent": cpu_usage,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available // (1024**3),
                "platform": platform.system(),
                "release": platform.release()
            },
            "status": "online"
        }

# ===== 建立機器人實例 =====
bot = PingBot()

# ===== 基本指令（含 Webhook 可選發送） =====
@bot.command(name='ping')
async def ping(ctx):
    """檢查機器人延遲，並可選擇發送到 Webhook"""
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
    status_text = "🟢 極佳" if api_latency < 50 else "🟡 良好" if api_latency < 100 else "🟠 普通" if api_latency < 200 else "🔴 延遲"
    embed.add_field(name="📡 API 延遲", value=f"```\n{api_latency}ms\n狀態: {status_text}\n```", inline=True)
    embed.add_field(name="🔄 往返延遲", value=f"```\n{round_trip}ms\n```", inline=True)
    embed.set_footer(text=f"測量時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    await message.edit(content=None, embed=embed)
    bot.command_count += 1

    # 若 Webhook 啟用，可選擇發送 Ping 結果（此處示範）
    if bot.webhook:
        ping_data = {
            "event": "ping",
            "api_latency_ms": api_latency,
            "round_trip_ms": round_trip,
            "status": status_text,
            "user": str(ctx.author),
            "channel": str(ctx.channel),
            "timestamp": datetime.now().isoformat()
        }
        await bot.webhook.send(ping_data)

@bot.command(name='status')
async def status(ctx):
    embed = bot.create_metrics_embed()
    await ctx.send(embed=embed)
    bot.command_count += 1

@bot.command(name='servers')
async def list_servers(ctx):
    guilds = bot.guilds
    embed = discord.Embed(
        title=f"📋 伺服器列表 ({len(guilds)} 個)",
        color=discord.Color.purple(),
        timestamp=datetime.now()
    )
    for guild in guilds[:25]:
        embed.add_field(
            name=guild.name,
            value=f"```\nID: {guild.id}\n成員: {guild.member_count}\n建立: {guild.created_at.strftime('%Y-%m-%d')}\n```",
            inline=True
        )
    if len(guilds) > 25:
        embed.set_footer(text=f"還有 {len(guilds) - 25} 個伺服器未顯示")
    await ctx.send(embed=embed)
    bot.command_count += 1

@bot.command(name='uptime')
async def uptime(ctx):
    uptime = datetime.now() - bot.start_time
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    embed = discord.Embed(
        title="⏰ 運行時間",
        color=discord.Color.gold(),
        timestamp=datetime.now()
    )
    embed.add_field(
        name="📊 統計",
        value=f"```\n天數: {days} 天\n小時: {hours} 小時\n分鐘: {minutes} 分鐘\n秒數: {seconds} 秒\n```",
        inline=False
    )
    embed.add_field(
        name="📈 總計",
        value=f"```\n總秒數: {uptime.total_seconds():.0f} 秒\n總分鐘數: {uptime.total_seconds() / 60:.0f} 分鐘\n總小時數: {uptime.total_seconds() / 3600:.1f} 小時\n```",
        inline=False
    )
    await ctx.send(embed=embed)
    bot.command_count += 1

@bot.command(name='help')
async def help_command(ctx):
    embed = discord.Embed(
        title="📚 Pingcord 指令列表",
        description="以下是所有可用的指令",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    commands_info = {
        "!ping": "🏓 測量機器人延遲",
        "!status": "📊 顯示伺服器狀態報告",
        "!servers": "📋 列出所有加入的伺服器",
        "!uptime": "⏰ 顯示機器人運行時間",
        "!help": "📚 顯示這個指令列表"
    }
    for cmd, desc in commands_info.items():
        embed.add_field(name=cmd, value=desc, inline=False)
    embed.set_footer(text=f"Pingcord v1.1 | 執行指令: {bot.command_count}")
    await ctx.send(embed=embed)
    bot.command_count += 1

# ===== 事件監聽 =====
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    bot.message_count += 1
    await bot.process_commands(message)

@bot.event
async def on_guild_join(guild):
    embed = discord.Embed(
        title="🎉 加入新伺服器！",
        description=f"已加入伺服器: **{guild.name}**",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    embed.add_field(
        name="📊 伺服器資訊",
        value=f"```\nID: {guild.id}\n成員: {guild.member_count}\n所有者: {guild.owner}\n建立時間: {guild.created_at.strftime('%Y-%m-%d')}\n```",
        inline=False
    )
    if PING_CHANNEL_ID:
        channel = bot.get_channel(PING_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)
    # 發送到 Webhook
    if bot.webhook:
        await bot.webhook.send({
            "event": "guild_join",
            "guild": {
                "id": guild.id,
                "name": guild.name,
                "member_count": guild.member_count,
                "owner": str(guild.owner),
                "created_at": guild.created_at.isoformat()
            },
            "timestamp": datetime.now().isoformat()
        })

@bot.event
async def on_guild_remove(guild):
    embed = discord.Embed(
        title="👋 離開伺服器",
        description=f"已離開伺服器: **{guild.name}**",
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    if PING_CHANNEL_ID:
        channel = bot.get_channel(PING_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)
    if bot.webhook:
        await bot.webhook.send({
            "event": "guild_remove",
            "guild": {
                "id": guild.id,
                "name": guild.name
            },
            "timestamp": datetime.now().isoformat()
        })

# ===== 錯誤處理 =====
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ 找不到這個指令，請使用 `!help` 查看所有指令")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ 你沒有權限執行這個指令")
    else:
        await ctx.send(f"❌ 發生錯誤: {str(error)}")
        print(f"錯誤: {error}")

# ===== 啟動機器人 =====
if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("❌ Token 無效，請檢查你的 Bot Token")
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")