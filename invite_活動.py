import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
import json
import os
from typing import Optional

# 機器人設定
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

# 活動資料儲存
ACTIVITIES_FILE = 'activities.json'

class ActivityManager:
    def __init__(self):
        self.activities = {}
        self.load_activities()

    def load_activities(self):
        """載入活動資料"""
        if os.path.exists(ACTIVITIES_FILE):
            with open(ACTIVITIES_FILE, 'r', encoding='utf-8') as f:
                self.activities = json.load(f)

    def save_activities(self):
        """儲存活動資料"""
        with open(ACTIVITIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.activities, f, ensure_ascii=False, indent=2)

    def create_activity(self, activity_id, name, description, host, time, max_participants):
        """建立活動"""
        self.activities[activity_id] = {
            'name': name,
            'description': description,
            'host': host,
            'time': time,
            'max_participants': max_participants,
            'participants': [],
            'created_at': datetime.now().isoformat()
        }
        self.save_activities()
        return True

    def join_activity(self, activity_id, user_id, user_name):
        """參加活動"""
        if activity_id not in self.activities:
            return False, "活動不存在"

        activity = self.activities[activity_id]
        if len(activity['participants']) >= activity['max_participants']:
            return False, "活動已額滿"

        if user_id in [p['id'] for p in activity['participants']]:
            return False, "你已經參加此活動了"

        activity['participants'].append({
            'id': user_id,
            'name': user_name,
            'joined_at': datetime.now().isoformat()
        })
        self.save_activities()
        return True, "成功參加活動！"

    def leave_activity(self, activity_id, user_id):
        """退出活動"""
        if activity_id not in self.activities:
            return False, "活動不存在"

        activity = self.activities[activity_id]
        participants = [p for p in activity['participants'] if p['id'] != user_id]

        if len(participants) == len(activity['participants']):
            return False, "你尚未參加此活動"

        activity['participants'] = participants
        self.save_activities()
        return True, "已退出活動"

    def get_activity_info(self, activity_id):
        """獲取活動資訊"""
        if activity_id not in self.activities:
            return None
        return self.activities[activity_id]

    def get_all_activities(self):
        """獲取所有活動"""
        return self.activities

activity_manager = ActivityManager()

@bot.event
async def on_ready():
    print(f'機器人已登入：{bot.user}')
    print(f'已連線到 {len(bot.guilds)} 個伺服器')
    try:
        synced = await bot.tree.sync()
        print(f"已同步 {len(synced)} 個斜線指令")
    except Exception as e:
        print(f"同步指令時發生錯誤：{e}")

    # 啟動自動提醒任務
    check_activities.start()

@bot.event
async def on_member_join(member):
    """新成員加入時的歡迎訊息"""
    channel = member.guild.system_channel
    if channel:
        embed = discord.Embed(
            title=f"歡迎 {member.name}！",
            description=f"歡迎來到 {member.guild.name}！\n"
                        f"使用 `/活動列表` 查看目前的活動",
            color=discord.Color.green()
        )
        await channel.send(embed=embed)

# 斜線指令：建立活動
@bot.tree.command(name="建立活動", description="建立一個新的活動")
@app_commands.describe(
    name="活動名稱",
    description="活動描述",
    time="活動時間 (格式：YYYY-MM-DD HH:MM)",
    max_participants="最大參與人數"
)
async def create_activity(interaction: discord.Interaction,
                          name: str,
                          description: str,
                          time: str,
                          max_participants: int):
    # 檢查時間格式
    try:
        activity_time = datetime.strptime(time, "%Y-%m-%d %H:%M")
        if activity_time < datetime.now():
            await interaction.response.send_message("❌ 活動時間不能是過去時間！", ephemeral=True)
            return
    except ValueError:
        await interaction.response.send_message("❌ 時間格式錯誤！請使用：YYYY-MM-DD HH:MM", ephemeral=True)
        return

    # 生成活動ID
    activity_id = f"{interaction.guild.id}_{datetime.now().timestamp()}"

    # 建立活動
    activity_manager.create_activity(
        activity_id,
        name,
        description,
        interaction.user.id,
        time,
        max_participants
    )

    # 建立活動資訊嵌入訊息
    embed = discord.Embed(
        title=f"🎉 {name}",
        description=description,
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    embed.add_field(name="👤 主辦人", value=f"<@{interaction.user.id}>", inline=True)
    embed.add_field(name="⏰ 時間", value=time, inline=True)
    embed.add_field(name="👥 人數限制", value=f"{max_participants} 人", inline=True)
    embed.add_field(name="📋 活動ID", value=activity_id, inline=False)
    embed.set_footer(text="使用 /參加活動 [活動ID] 來參加此活動！")

    await interaction.response.send_message(embed=embed)

# 斜線指令：參加活動
@bot.tree.command(name="參加活動", description="參加指定的活動")
@app_commands.describe(activity_id="活動ID")
async def join_activity(interaction: discord.Interaction, activity_id: str):
    user = interaction.user

    # 檢查活動是否存在
    activity = activity_manager.get_activity_info(activity_id)
    if not activity:
        await interaction.response.send_message("❌ 找不到此活動！", ephemeral=True)
        return

    # 參加活動
    success, message = activity_manager.join_activity(
        activity_id,
        str(user.id),
        user.name
    )

    if success:
        # 更新活動資訊
        activity = activity_manager.get_activity_info(activity_id)
        embed = discord.Embed(
            title=f"✅ {user.name} 已參加活動！",
            description=f"已成功參加 **{activity['name']}**",
            color=discord.Color.green()
        )
        embed.add_field(name="👥 目前人數",
                        value=f"{len(activity['participants'])}/{activity['max_participants']}",
                        inline=True)
        await interaction.response.send_message(embed=embed)

        # 發送通知給主辦人
        host = await bot.fetch_user(int(activity['host']))
        if host:
            try:
                await host.send(f"📢 {user.name} 已參加你的活動：**{activity['name']}**")
            except:
                pass
    else:
        await interaction.response.send_message(f"❌ {message}", ephemeral=True)

# 斜線指令：退出活動
@bot.tree.command(name="退出活動", description="退出已參加的活動")
@app_commands.describe(activity_id="活動ID")
async def leave_activity(interaction: discord.Interaction, activity_id: str):
    success, message = activity_manager.leave_activity(activity_id, str(interaction.user.id))

    if success:
        await interaction.response.send_message(f"✅ {message}", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ {message}", ephemeral=True)

# 斜線指令：活動列表
@bot.tree.command(name="活動列表", description="查看所有活動")
async def list_activities(interaction: discord.Interaction):
    activities = activity_manager.get_all_activities()

    if not activities:
        await interaction.response.send_message("📭 目前沒有任何活動！", ephemeral=True)
        return

    embed = discord.Embed(
        title="📋 活動列表",
        color=discord.Color.gold(),
        timestamp=datetime.now()
    )

    for aid, activity in activities.items():
        participants_count = len(activity['participants'])
        status = "✅ 進行中" if participants_count < activity['max_participants'] else "❌ 已額滿"

        embed.add_field(
            name=f"🎯 {activity['name']}",
            value=f"ID: `{aid}`\n"
                  f"👤 主辦：<@{activity['host']}>\n"
                  f"⏰ {activity['time']}\n"
                  f"👥 {participants_count}/{activity['max_participants']}\n"
                  f"狀態：{status}",
            inline=False
        )

    await interaction.response.send_message(embed=embed)

# 斜線指令：活動詳情
@bot.tree.command(name="活動詳情", description="查看指定活動的詳細資訊")
@app_commands.describe(activity_id="活動ID")
async def activity_detail(interaction: discord.Interaction, activity_id: str):
    activity = activity_manager.get_activity_info(activity_id)

    if not activity:
        await interaction.response.send_message("❌ 找不到此活動！", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"📋 {activity['name']}",
        description=activity['description'],
        color=discord.Color.purple()
    )
    embed.add_field(name="👤 主辦人", value=f"<@{activity['host']}>", inline=True)
    embed.add_field(name="⏰ 時間", value=activity['time'], inline=True)
    embed.add_field(name="👥 人數",
                    value=f"{len(activity['participants'])}/{activity['max_participants']}",
                    inline=True)

    # 顯示參與者名單
    if activity['participants']:
        participants_list = "\n".join([f"• {p['name']}" for p in activity['participants']])
        embed.add_field(name="📋 參與者", value=participants_list, inline=False)
    else:
        embed.add_field(name="📋 參與者", value="目前尚無參與者", inline=False)

    await interaction.response.send_message(embed=embed)

# 斜線指令：成員統計
@bot.tree.command(name="成員統計", description="查看伺服器成員統計資訊")
async def member_stats(interaction: discord.Interaction):
    guild = interaction.guild

    # 計算各種成員數量
    total_members = guild.member_count
    online_members = len([m for m in guild.members if m.status != discord.Status.offline])
    bots = len([m for m in guild.members if m.bot])
    humans = total_members - bots

    embed = discord.Embed(
        title=f"📊 {guild.name} 成員統計",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    embed.add_field(name="👥 總人數", value=total_members, inline=True)
    embed.add_field(name="🟢 線上", value=online_members, inline=True)
    embed.add_field(name="🤖 機器人", value=bots, inline=True)
    embed.add_field(name="👤 真人", value=humans, inline=True)

    # 顯示在線狀態分布
    status_counts = {
        "🟢 線上": len([m for m in guild.members if m.status == discord.Status.online]),
        "🟡 閒置": len([m for m in guild.members if m.status == discord.Status.idle]),
        "🔴 勿擾": len([m for m in guild.members if m.status == discord.Status.dnd]),
        "⚫ 離線": len([m for m in guild.members if m.status == discord.Status.offline])
    }

    status_text = "\n".join([f"{k}: {v}" for k, v in status_counts.items()])
    embed.add_field(name="📊 狀態分布", value=status_text, inline=False)

    await interaction.response.send_message(embed=embed)

# 斜線指令：隨機聊天話題
@bot.tree.command(name="話題", description="生成一個隨機聊天話題")
async def random_topic(interaction: discord.Interaction):
    topics = [
        "如果你可以擁有任何一種超能力，你會選擇什麼？為什麼？",
        "你最近看過最好的電影或影集是什麼？",
        "如果你有機會去任何地方旅行，你會去哪裡？",
        "你覺得未來的世界會變成什麼樣子？",
        "你最喜歡的書是什麼？為什麼推薦它？",
        "如果可以回到過去，你會改變什麼？",
        "你認為人生中最重要的是什麼？",
        "分享一個你最近學到的新事物",
        "如果你可以跟任何歷史人物共進晚餐，你會選誰？",
        "你覺得什麼是真正的幸福？",
        "你最近有什麼有趣的經歷可以分享？",
        "如果你可以設計一個新的節日，會是什麼節日？",
        "你認為科技對人類的影響是正面還是負面？",
        "你最喜歡的回憶是什麼？",
        "如果可以選擇，你會想成為什麼動物？為什麼？"
    ]

    import random
    topic = random.choice(topics)

    embed = discord.Embed(
        title="💭 今日話題",
        description=topic,
        color=discord.Color.magenta()
    )
    embed.set_footer(text="快來和大家分享你的想法吧！")

    await interaction.response.send_message(embed=embed)

# 後台任務：活動提醒
@tasks.loop(minutes=5)
async def check_activities():
    """檢查即將開始的活動並發送提醒"""
    now = datetime.now()
    activities = activity_manager.get_all_activities()

    for activity_id, activity in activities.items():
        try:
            activity_time = datetime.strptime(activity['time'], "%Y-%m-%d %H:%M")
            time_diff = activity_time - now

            # 在活動開始前30分鐘提醒
            if timedelta(minutes=30) <= time_diff <= timedelta(minutes=32):
                # 通知所有參與者
                for participant in activity['participants']:
                    try:
                        user = await bot.fetch_user(int(participant['id']))
                        if user:
                            await user.send(f"⏰ 提醒：活動 **{activity['name']}** 將在30分鐘後開始！")
                    except:
                        pass
        except:
            continue

# 文字指令：幫助
@bot.command(name='help_activity')
async def help_activity(ctx):
    """顯示機器人指令幫助"""
    embed = discord.Embed(
        title="🤖 活動機器人 - 使用說明",
        description="以下是指令列表：",
        color=discord.Color.blue()
    )

    commands_list = [
        ("/建立活動", "建立一個新的活動"),
        ("/參加活動 [活動ID]", "參加指定的活動"),
        ("/退出活動 [活動ID]", "退出已參加的活動"),
        ("/活動列表", "查看所有活動"),
        ("/活動詳情 [活動ID]", "查看活動詳細資訊"),
        ("/成員統計", "查看伺服器成員統計"),
        ("/話題", "生成隨機聊天話題"),
        ("!help_activity", "顯示此幫助訊息")
    ]

    for cmd, desc in commands_list:
        embed.add_field(name=cmd, value=desc, inline=False)

    await ctx.send(embed=embed)

# 啟動機器人
if __name__ == "__main__":
    # 請替換為你的 Discord Bot Token
    TOKEN = "YOUR_DISCORD_BOT_TOKEN_HERE"
    bot.run(TOKEN)