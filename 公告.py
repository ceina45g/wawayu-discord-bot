# bot.py
import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta
import json
import os
from typing import Optional, Dict, Any

# 設定機器人權限
intents = discord.Intents.default()
intents.message_content = True
intents.administrator = True

bot = commands.Bot(command_prefix='!', intents=intents)

# 儲存排程公告的檔案
SCHEDULE_FILE = 'scheduled_announcements.json'

class AnnouncementBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scheduled_announcements = {}
        self.load_schedules()
        self.check_scheduled_announcements.start()

    def load_schedules(self):
        """載入排程公告"""
        if os.path.exists(SCHEDULE_FILE):
            with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
                self.scheduled_announcements = json.load(f)
        else:
            self.scheduled_announcements = {}

    def save_schedules(self):
        """儲存排程公告"""
        with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.scheduled_announcements, f, ensure_ascii=False, indent=2)

    @commands.command(name='公告')
    @commands.has_permissions(administrator=True)
    async def announce(self, ctx, channel: discord.TextChannel = None, *, message: str = None):
        """發布公告
        使用方法：!公告 #頻道 公告內容
        或：!公告 公告內容 (在當前頻道發布)"""
        if not message:
            await ctx.send("❌ 請輸入公告內容！\n使用方法：`!公告 #頻道 公告內容` 或 `!公告 公告內容`")
            return

        try:
            target_channel = channel or ctx.channel

            # 創建漂亮的公告嵌入
            embed = discord.Embed(
                title="📢 伺服器公告",
                description=message,
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            embed.set_footer(
                text=f"由 {ctx.author.display_name} 發布",
                icon_url=ctx.author.display_avatar.url
            )
            embed.set_author(
                name=ctx.guild.name,
                icon_url=ctx.guild.icon.url if ctx.guild.icon else None
            )

            # 發送公告
            await target_channel.send(embed=embed)
            await ctx.send(f"✅ 公告已發送到 {target_channel.mention}！")

        except discord.Forbidden:
            await ctx.send("❌ 我沒有權限在該頻道發送訊息！")
        except Exception as e:
            await ctx.send(f"❌ 發送公告時發生錯誤：{str(e)}")

    @commands.command(name='排程公告')
    @commands.has_permissions(administrator=True)
    async def schedule_announce(self, ctx, channel: discord.TextChannel,
                                date: str, time: str, *, message: str):
        """排程公告
        使用方法：!排程公告 #頻道 YYYY-MM-DD HH:MM 公告內容
        範例：!排程公告 #公告 2026-12-25 18:00 聖誕節快樂！"""
        try:
            # 解析日期時間
            scheduled_time = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")

            if scheduled_time < datetime.now():
                await ctx.send("❌ 排程時間必須在未來！")
                return

            # 生成唯一ID
            schedule_id = str(int(datetime.now().timestamp()))

            # 儲存排程
            self.scheduled_announcements[schedule_id] = {
                'channel_id': str(channel.id),
                'guild_id': str(ctx.guild.id),
                'message': message,
                'scheduled_time': scheduled_time.isoformat(),
                'author_id': str(ctx.author.id),
                'author_name': ctx.author.display_name
            }
            self.save_schedules()

            # 計算剩餘時間
            time_remaining = scheduled_time - datetime.now()
            hours, remainder = divmod(time_remaining.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)

            await ctx.send(
                f"✅ 排程公告已設定！\n"
                f"📅 將於 {scheduled_time.strftime('%Y-%m-%d %H:%M')} 發送到 {channel.mention}\n"
                f"⏰ 剩餘時間：{int(hours)}小時 {int(minutes)}分鐘"
            )

        except ValueError:
            await ctx.send("❌ 日期格式錯誤！請使用：YYYY-MM-DD HH:MM")
        except Exception as e:
            await ctx.send(f"❌ 設定排程時發生錯誤：{str(e)}")

    @commands.command(name='取消排程')
    @commands.has_permissions(administrator=True)
    async def cancel_schedule(self, ctx, schedule_id: str = None):
        """取消排程公告
        使用方法：!取消排程 排程ID
        或：!取消排程 (顯示所有排程列表)"""
        if not self.scheduled_announcements:
            await ctx.send("📭 目前沒有任何排程公告。")
            return

        if not schedule_id:
            # 顯示所有排程
            embed = discord.Embed(
                title="📋 排程公告列表",
                color=discord.Color.blue()
            )
            for sid, info in self.scheduled_announcements.items():
                scheduled_time = datetime.fromisoformat(info['scheduled_time'])
                embed.add_field(
                    name=f"ID: {sid}",
                    value=f"📅 {scheduled_time.strftime('%Y-%m-%d %H:%M')}\n"
                          f"📝 {info['message'][:50]}...\n"
                          f"👤 {info['author_name']}",
                    inline=False
                )
            await ctx.send(embed=embed)
            return

        if schedule_id in self.scheduled_announcements:
            del self.scheduled_announcements[schedule_id]
            self.save_schedules()
            await ctx.send(f"✅ 已取消排程 ID：{schedule_id}")
        else:
            await ctx.send(f"❌ 找不到排程 ID：{schedule_id}")

    @tasks.loop(seconds=60)
    async def check_scheduled_announcements(self):
        """檢查並執行排程公告"""
        now = datetime.now()
        to_remove = []

        for schedule_id, info in self.scheduled_announcements.items():
            scheduled_time = datetime.fromisoformat(info['scheduled_time'])

            if now >= scheduled_time:
                try:
                    # 獲取頻道
                    guild = self.bot.get_guild(int(info['guild_id']))
                    if not guild:
                        continue

                    channel = guild.get_channel(int(info['channel_id']))
                    if not channel:
                        continue

                    # 獲取發布者資訊
                    author = guild.get_member(int(info['author_id']))
                    author_name = author.display_name if author else info['author_name']

                    # 發布公告
                    embed = discord.Embed(
                        title="📢 排程公告",
                        description=info['message'],
                        color=discord.Color.green(),
                        timestamp=scheduled_time
                    )
                    embed.set_footer(
                        text=f"由 {author_name} 排程發布",
                        icon_url=author.display_avatar.url if author else None
                    )
                    embed.set_author(
                        name=guild.name,
                        icon_url=guild.icon.url if guild.icon else None
                    )

                    await channel.send(embed=embed)

                    # 標記為已完成
                    to_remove.append(schedule_id)

                except Exception as e:
                    print(f"執行排程公告時發生錯誤：{str(e)}")

        # 移除已執行的排程
        for schedule_id in to_remove:
            del self.scheduled_announcements[schedule_id]

        if to_remove:
            self.save_schedules()

    @check_scheduled_announcements.before_loop
    async def before_check_schedules(self):
        """等待機器人啟動完成"""
        await self.bot.wait_until_ready()

    @commands.command(name='公告模板')
    @commands.has_permissions(administrator=True)
    async def announcement_template(self, ctx):
        """顯示公告模板"""
        embed = discord.Embed(
            title="📝 公告模板",
            description="使用以下格式來發布公告：",
            color=discord.Color.purple()
        )
        embed.add_field(
            name="一般公告",
            value="`!公告 #頻道 您的公告內容`\n或\n`!公告 您的公告內容`",
            inline=False
        )
        embed.add_field(
            name="排程公告",
            value="`!排程公告 #頻道 YYYY-MM-DD HH:MM 公告內容`\n範例：`!排程公告 #公告 2026-12-25 18:00 聖誕快樂！`",
            inline=False
        )
        embed.add_field(
            name="其他指令",
            value="`!取消排程` - 查看所有排程\n`!取消排程 ID` - 取消特定排程\n`!公告模板` - 顯示此訊息",
            inline=False
        )
        embed.set_footer(text="所有指令僅限管理員使用")
        await ctx.send(embed=embed)

# 錯誤處理
@bot.event
async def on_ready():
    print(f'🤖 {bot.user} 已上線！')
    print(f'📊 已連線到 {len(bot.guilds)} 個伺服器')
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="!公告模板 | 管理員專用"
        )
    )

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ 你沒有權限使用此指令！")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ 缺少必要參數！請使用 `!公告模板` 查看正確用法。")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ 參數格式錯誤！請檢查輸入。")
    else:
        await ctx.send(f"❌ 發生錯誤：{str(error)}")

# 啟動機器人
if __name__ == "__main__":
    # 請將 'YOUR_BOT_TOKEN' 替換為你的機器人 Token
    TOKEN = 'YOUR_BOT_TOKEN'

    # 載入 Cog
    asyncio.run(bot.add_cog(AnnouncementBot(bot)))
    bot.run(TOKEN)