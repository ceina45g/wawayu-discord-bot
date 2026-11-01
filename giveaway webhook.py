import discord
from discord.ext import commands, tasks
import random
import asyncio
import json
import os
import aiohttp
from datetime import datetime
import pytz

# ===== 設定檔 =====
CONFIG_FILE = 'giveaways.json'

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ===== 資料管理 =====
def load_data():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'giveaways': {}, 'webhooks': {}}

def save_data(data):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# 載入資料
data = load_data()
active_giveaways = data.get('giveaways', {})
webhook_urls = data.get('webhooks', {})  # 格式：{guild_id: webhook_url}

# ===== Webhook 發送函數 =====
async def send_webhook(guild_id, payload):
    """發送抽獎結果到 Webhook"""
    url = webhook_urls.get(str(guild_id))
    if not url:
        return  # 未設定則跳過

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=10) as resp:
                if resp.status >= 400:
                    print(f"⚠️ Webhook 發送失敗，狀態碼：{resp.status}")
                else:
                    print("✅ Webhook 發送成功")
    except Exception as e:
        print(f"❌ Webhook 錯誤：{e}")

# ===== 結束抽獎（整合 Webhook） =====
async def end_giveaway(ctx, message_id):
    giveaway_data = active_giveaways[str(message_id)]
    participants = giveaway_data['participants']
    winners_count = giveaway_data['winners']

    # 取得原始訊息
    try:
        channel = bot.get_channel(giveaway_data['channel_id'])
        message = await channel.fetch_message(message_id)
    except:
        message = None

    # 抽出得獎者
    if not participants:
        result_msg = f"😢 沒有人參加抽獎：**{giveaway_data['prize']}**"
        winners = []
    else:
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

    # === 發送 Webhook 通知 ===
    webhook_payload = {
        "event": "giveaway_ended",
        "guild_id": ctx.guild.id,
        "channel_id": ctx.channel.id,
        "message_id": message_id,
        "prize": giveaway_data['prize'],
        "winners": winners,  # 使用者 ID 列表
        "winner_mentions": [f"<@{w}>" for w in winners],
        "participants_count": len(participants),
        "host_id": giveaway_data['host'],
        "end_time": giveaway_data['end_time']
    }
    await send_webhook(ctx.guild.id, webhook_payload)

    # 標記為已結束
    giveaway_data['ended'] = True
    data['giveaways'] = active_giveaways
    save_data(data)

# ===== 指令區 =====
@bot.event
async def on_ready():
    print(f'✅ 機器人已登入：{bot.user}')
    print(f'📊 載入 {len(active_giveaways)} 個進行中的抽獎')
    check_giveaways.start()

@bot.command()
@commands.has_permissions(administrator=True)
async def setwebhook(ctx, url: str):
    """設定 Webhook URL（管理員專用）"""
    # 簡單驗證 URL 格式
    if not url.startswith(('http://', 'https://')):
        await ctx.send("❌ 請輸入有效的 HTTP/HTTPS 網址")
        return

    webhook_urls[str(ctx.guild.id)] = url
    data['webhooks'] = webhook_urls
    save_data(data)
    await ctx.send(f"✅ Webhook 已設定：{url}")

@bot.command()
@commands.has_permissions(administrator=True)
async def removewebhook(ctx):
    """移除 Webhook 設定"""
    if str(ctx.guild.id) in webhook_urls:
        del webhook_urls[str(ctx.guild.id)]
        data['webhooks'] = webhook_urls
        save_data(data)
        await ctx.send("✅ Webhook 已移除")
    else:
        await ctx.send("ℹ️ 此伺服器尚未設定 Webhook")

@bot.command()
@commands.has_permissions(administrator=True)
async def giveaway(ctx, duration: int, winners: int = 1, *, prize):
    """開始抽獎 - 用法：!giveaway 秒數 得獎人數 獎品"""
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
    data['giveaways'] = active_giveaways
    save_data(data)

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
    if str(message_id) not in active_giveaways:
        await ctx.send("❌ 找不到此抽獎活動！")
        return
    await end_giveaway(ctx, message_id)

# ===== 定時檢查 =====
@tasks.loop(seconds=10)
async def check_giveaways():
    current_time = datetime.now().timestamp()
    to_remove = []

    for msg_id, g_data in active_giveaways.items():
        if g_data['ended']:
            continue
        if current_time >= g_data['end_time']:
            channel = bot.get_channel(g_data['channel_id'])
            if channel:
                try:
                    ctx = await bot.get_context(await channel.fetch_message(int(msg_id)))
                    await end_giveaway(ctx, int(msg_id))
                except Exception as e:
                    print(f"⚠️ 結束抽獎時出錯：{e}")
            to_remove.append(msg_id)

    for msg_id in to_remove:
        if msg_id in active_giveaways:
            active_giveaways[msg_id]['ended'] = True

    if to_remove:
        data['giveaways'] = active_giveaways
        save_data(data)

# ===== 反應事件 =====
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    msg_id = str(reaction.message.id)
    if msg_id in active_giveaways:
        if str(reaction.emoji) == "🎉":
            g_data = active_giveaways[msg_id]
            if not g_data['ended'] and user.id not in g_data['participants']:
                g_data['participants'].append(user.id)
                data['giveaways'] = active_giveaways
                save_data(data)
                await update_participants_count(reaction.message)

@bot.event
async def on_reaction_remove(reaction, user):
    if user.bot:
        return
    msg_id = str(reaction.message.id)
    if msg_id in active_giveaways:
        if str(reaction.emoji) == "🎉":
            g_data = active_giveaways[msg_id]
            if not g_data['ended'] and user.id in g_data['participants']:
                g_data['participants'].remove(user.id)
                data['giveaways'] = active_giveaways
                save_data(data)
                await update_participants_count(reaction.message)

async def update_participants_count(message):
    msg_id = str(message.id)
    if msg_id in active_giveaways:
        count = len(active_giveaways[msg_id]['participants'])
        if message.embeds:
            embed = message.embeds[0]
            embed_dict = embed.to_dict()
            for i, field in enumerate(embed_dict.get('fields', [])):
                if field['name'] == '👥 參加人數':
                    embed_dict['fields'][i]['value'] = str(count)
                    await message.edit(embed=discord.Embed.from_dict(embed_dict))
                    break

# ===== 錯誤處理 =====
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ 你沒有使用此指令的權限！")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ 參數不足！請檢查指令格式。")
    else:
        await ctx.send(f"❌ 發生錯誤：{error}")

# ===== 啟動 =====
if __name__ == "__main__":
    bot.run('YOUR_BOT_TOKEN')