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
import random
import asyncio
import json
import os
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

# 設定檔
CONFIG_FILE = 'giveaways.json'

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# 載入抽獎資料
def load_giveaways():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_giveaways(data):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# 載入進行中的抽獎
active_giveaways = load_giveaways()

@bot.event
async def on_ready():
    print(f'giveaway bot logged in: {bot.user}')
    print(f'Loaded {len(active_giveaways)} active giveaways')
    check_giveaways.start()

@bot.command()
@commands.has_permissions(administrator=True)
async def giveaway(ctx, duration: int, winners: int = 1, *, prize):
    """
    開始抽獎
    用法：!giveaway 持續時間(秒) 得獎人數 獎品
    範例：!giveaway 60 2 Minecraft 序號
    """

    if winners < 1:
        await ctx.send("❌ 得獎人數至少為 1 人！")
        return

    embed = discord.Embed(
        title="🎉 抽獎活動開始！",
        description=f"獎品：**{prize}**\n得獎人數：**{winners} 人**\n點擊 🎉 參加抽獎！",
        color=discord.Color.gold()
    )
    embed.add_field(name="👥 參加人數", value="0", inline=True)
    embed.add_field(name="⏰ 結束時間", value=f"<t:{int(ctx.message.created_at.timestamp()) + duration}:R>", inline=True)
    embed.add_field(name="🏆 得獎人數", value=winners, inline=True)
    embed.set_footer(text=f"主辦人：{ctx.author.name} | 抽獎ID：{ctx.message.id}")

    message = await ctx.send(embed=embed)
    await message.add_reaction("🎉")

    # 儲存抽獎資訊
    giveaway_data = {
        'channel_id': ctx.channel.id,
        'guild_id': ctx.guild.id,
        'prize': prize,
        'winners': winners,
        'participants': [],
        'end_time': ctx.message.created_at.timestamp() + duration,
        'host': ctx.author.id,
        'message_id': message.id,
        'ended': False
    }

    active_giveaways[str(message.id)] = giveaway_data
    save_giveaways(active_giveaways)

@bot.command()
async def reroll(ctx, message_id: int):
    """重新抽獎 - 用法：!reroll 訊息ID"""

    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ 你需要管理員權限！")
        return

    giveaway_data = active_giveaways.get(str(message_id))
    if not giveaway_data:
        await ctx.send("❌ 找不到此抽獎活動！")
        return

    if not giveaway_data['participants']:
        await ctx.send("❌ 沒有參加者可以重新抽獎！")
        return

    participants = giveaway_data['participants']
    winners_count = giveaway_data['winners']

    if len(participants) < winners_count:
        winners_count = len(participants)

    winners = random.sample(participants, winners_count)
    winner_mentions = ', '.join([f'<@{w}>' for w in winners])

    await ctx.send(f"🎊 重新抽獎！得獎者是：{winner_mentions} 獲得 **{giveaway_data['prize']}**！")

@bot.command()
@commands.has_permissions(administrator=True)
async def endgiveaway(ctx, message_id: int):
    """提前結束抽獎 - 用法：!endgiveaway 訊息ID"""

    giveaway_data = active_giveaways.get(str(message_id))
    if not giveaway_data:
        await ctx.send("❌ 找不到此抽獎活動！")
        return

    await end_giveaway(ctx, message_id)

async def end_giveaway(ctx, message_id):
    """結束抽獎的內部函數"""

    giveaway_data = active_giveaways[str(message_id)]
    participants = giveaway_data['participants']
    winners_count = giveaway_data['winners']

    # 取得原始訊息
    try:
        channel = bot.get_channel(giveaway_data['channel_id'])
        message = await channel.fetch_message(message_id)
    except:
        message = None

    if not participants:
        result_msg = f"😢 沒有人參加抽獎：**{giveaway_data['prize']}**"
        winners = []
    else:
        # 抽出得獎者
        if len(participants) < winners_count:
            winners_count = len(participants)
        winners = random.sample(participants, winners_count)
        winner_mentions = ', '.join([f'<@{w}>' for w in winners])
        result_msg = f"🎊 恭喜 {winner_mentions} 贏得 **{giveaway_data['prize']}**！"

    await ctx.send(result_msg)

    # 更新嵌入訊息
    if message:
        embed = discord.Embed(
            title="🏁 抽獎已結束！",
            description=f"獎品：**{giveaway_data['prize']}**\n得獎者：{'無' if not winners else ', '.join([f'<@{w}>' for w in winners])}",
            color=discord.Color.red()
        )
        embed.add_field(name="👥 總參加人數", value=len(participants), inline=True)
        await message.edit(embed=embed)

    # 標記為已結束
    giveaway_data['ended'] = True
    save_giveaways(active_giveaways)

@tasks.loop(seconds=10)
async def check_giveaways():
    """定時檢查過期的抽獎"""

    current_time = datetime.now().timestamp()
    to_remove = []

    for msg_id, data in active_giveaways.items():
        if data['ended']:
            continue

        if current_time >= data['end_time']:
            channel = bot.get_channel(data['channel_id'])
            if channel:
                try:
                    ctx = await bot.get_context(await channel.fetch_message(int(msg_id)))
                    await end_giveaway(ctx, int(msg_id))
                except:
                    pass
            to_remove.append(msg_id)

    # 清理已結束的抽獎（保留一段時間以便查詢）
    for msg_id in to_remove:
        if msg_id in active_giveaways:
            active_giveaways[msg_id]['ended'] = True

    if to_remove:
        save_giveaways(active_giveaways)

@bot.event
async def on_reaction_add(reaction, user):
    """記錄參加者"""
    if user.bot:
        return

    msg_id = str(reaction.message.id)
    if msg_id in active_giveaways:
        if str(reaction.emoji) == "🎉":
            giveaway_data = active_giveaways[msg_id]
            if not giveaway_data['ended']:
                if user.id not in giveaway_data['participants']:
                    giveaway_data['participants'].append(user.id)
                    save_giveaways(active_giveaways)

                    # 更新參加人數
                    await update_participants_count(reaction.message)

@bot.event
async def on_reaction_remove(reaction, user):
    """移除參加者"""
    if user.bot:
        return

    msg_id = str(reaction.message.id)
    if msg_id in active_giveaways:
        if str(reaction.emoji) == "🎉":
            giveaway_data = active_giveaways[msg_id]
            if not giveaway_data['ended']:
                if user.id in giveaway_data['participants']:
                    giveaway_data['participants'].remove(user.id)
                    save_giveaways(active_giveaways)

                    # 更新參加人數
                    await update_participants_count(reaction.message)

async def update_participants_count(message):
    """更新參加人數顯示"""
    msg_id = str(message.id)
    if msg_id in active_giveaways:
        count = len(active_giveaways[msg_id]['participants'])

        # 更新嵌入訊息
        embed = message.embeds[0] if message.embeds else None
        if embed:
            embed_dict = embed.to_dict()
            for i, field in enumerate(embed_dict.get('fields', [])):
                if field['name'] == '👥 參加人數':
                    embed_dict['fields'][i]['value'] = str(count)
                    await message.edit(embed=discord.Embed.from_dict(embed_dict))
                    break

# 錯誤處理
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ 你沒有使用此指令的權限！")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ 參數不足！請檢查指令格式。")
    else:
        await ctx.send(f"❌ 發生錯誤：{error}")

# 執行程式
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("錯誤：找不到 DISCORD_TOKEN，請檢查 .env 檔案。")
