# pingcord_moderator.py
# 小智機器人 - PingCord 頁面審核員
# 依賴: pip install discord.py

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
from discord.ext import commands
import re
import datetime
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# 配置區域
# ============================================================
# 優先從環境變數讀取，若無則使用預設字串
BOT_TOKEN = os.getenv("DISCORD_TOKEN") or "你的機器人TOKEN"          # 替換為你的 Token
LOG_CHANNEL_ID = 123456789012345678    # 審核日誌頻道 ID
MUTE_ROLE_ID = 987654321098765432      # 禁言身分組 ID（可選）
WARN_THRESHOLD = 3                     # 警告次數達此值自動禁言

# 違規關鍵詞（可自行增減，支援正則）
BAD_WORDS = [
    r"廣告", r"加微信", r"免費領取", r"私聊",
    r"https?://(?!discord\.com|discord\.gg)\S+",  # 非 Discord 官方連結
]

# 違規行為對應的處罰動作
PUNISH_ACTIONS = {
    "delete": True,       # 刪除訊息
    "warn": True,         # 發送警告
    "mute": False,        # 是否立即禁言（可搭配警告次數）
}

# ============================================================
# 機器人初始化
# ============================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 用戶警告記錄 {user_id: {"count": int, "reasons": list}}
warnings_db: dict[int, dict] = {}


# ============================================================
# 工具函數
# ============================================================
def contains_bad_word(content: str) -> str | None:
    """檢查訊息是否包含違規詞，返回匹配到的詞或 None"""
    for pattern in BAD_WORDS:
        if re.search(pattern, content, re.IGNORECASE):
            return pattern
    return None


async def send_log(guild: discord.Guild, embed: discord.Embed):
    """發送審核日誌到指定頻道"""
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(embed=embed)


async def apply_mute(member: discord.Member, reason: str):
    """對成員施加禁言"""
    mute_role = member.guild.get_role(MUTE_ROLE_ID)
    if mute_role:
        await member.add_roles(mute_role, reason=reason)
        return True
    return False


# ============================================================
# 事件監聽：訊息審核
# ============================================================
@bot.event
async def on_message(message: discord.Message):
    # 忽略機器人自己的訊息
    if message.author.bot:
        return

    # 忽略管理員
    if message.author.guild_permissions.administrator:
        await bot.process_commands(message)
        return

    # 檢查違規詞
    matched = contains_bad_word(message.content)
    if matched:
        # 刪除訊息
        if PUNISH_ACTIONS["delete"]:
            try:
                await message.delete()
            except discord.Forbidden:
                pass

        # 記錄警告
        uid = message.author.id
        if uid not in warnings_db:
            warnings_db[uid] = {"count": 0, "reasons": []}
        warnings_db[uid]["count"] += 1
        warnings_db[uid]["reasons"].append(matched)

        warn_count = warnings_db[uid]["count"]

        # 發送警告訊息
        if PUNISH_ACTIONS["warn"]:
            try:
                warn_msg = await message.channel.send(
                    f"⚠️ {message.author.mention}，你的訊息因包含違規內容已被刪除。"
                    f"（警告 {warn_count}/{WARN_THRESHOLD}）"
                )
                await asyncio.sleep(5)
                await warn_msg.delete()
            except discord.Forbidden:
                pass

        # 達到閾值自動禁言
        if warn_count >= WARN_THRESHOLD and PUNISH_ACTIONS.get("mute", False):
            muted = await apply_mute(
                message.author,
                reason=f"累計 {warn_count} 次違規，自動禁言"
            )
            if muted:
                await message.channel.send(
                    f"🔇 {message.author.mention} 因多次違規已被禁言。"
                )

        # 發送審核日誌
        embed = discord.Embed(
            title="🔍 違規訊息審核",
            color=discord.Color.red(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="用戶", value=f"{message.author} (`{uid}`)", inline=True)
        embed.add_field(name="頻道", value=message.channel.mention, inline=True)
        embed.add_field(name="違規詞", value=f"`{matched}`", inline=True)
        embed.add_field(name="原始內容", value=message.content[:1000], inline=False)
        embed.add_field(name="累計警告", value=str(warn_count), inline=True)
        embed.set_footer(text="PingCord 頁面審核員")
        await send_log(message.guild, embed)

    await bot.process_commands(message)


# ============================================================
# 指令：手動警告
# ============================================================
@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def warn_user(ctx, member: discord.Member, *, reason: str = "未提供原因"):
    """手動警告成員：!warn @用戶 原因"""
    uid = member.id
    if uid not in warnings_db:
        warnings_db[uid] = {"count": 0, "reasons": []}
    warnings_db[uid]["count"] += 1
    warnings_db[uid]["reasons"].append(f"[手動] {reason}")

    embed = discord.Embed(
        title="⚠️ 手動警告",
        color=discord.Color.orange(),
        timestamp=datetime.datetime.utcnow()
    )
    embed.add_field(name="用戶", value=member.mention, inline=True)
    embed.add_field(name="原因", value=reason, inline=True)
    embed.add_field(name="累計警告", value=str(warnings_db[uid]["count"]), inline=True)
    embed.set_footer(text=f"審核員：{ctx.author}")
    await ctx.send(embed=embed)

    # 達到閾值禁言
    if warnings_db[uid]["count"] >= WARN_THRESHOLD and PUNISH_ACTIONS.get("mute", False):
        muted = await apply_mute(member, reason=f"累計 {warnings_db[uid]['count']} 次警告")
        if muted:
            await ctx.send(f"🔇 {member.mention} 已被禁言。")


# ============================================================
# 指令：清除警告
# ============================================================
@bot.command(name="clearwarn")
@commands.has_permissions(administrator=True)
async def clear_warn(ctx, member: discord.Member):
    """清除成員警告記錄：!clearwarn @用戶"""
    warnings_db.pop(member.id, None)
    await ctx.send(f"✅ 已清除 {member.mention} 的警告記錄。")


# ============================================================
# 指令：查看警告
# ============================================================
@bot.command(name="warns")
@commands.has_permissions(manage_messages=True)
async def check_warns(ctx, member: discord.Member):
    """查看成員警告記錄：!warns @用戶"""
    data = warnings_db.get(member.id)
    if not data:
        await ctx.send(f"{member.mention} 沒有任何警告記錄。")
        return

    embed = discord.Embed(
        title=f"📋 {member.display_name} 的警告記錄",
        color=discord.Color.yellow()
    )
    embed.add_field(name="累計次數", value=str(data["count"]), inline=False)
    reasons = "\n".join(f"• {r}" for r in data["reasons"][-10:])
    embed.add_field(name="最近原因", value=reasons or "無", inline=False)
    await ctx.send(embed=embed)


# ============================================================
# 啟動
# ============================================================
@bot.event
async def on_ready():
    print(f"✅ 小智審核員已上線：{bot.user} (ID: {bot.user.id})")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="PingCord 頁面"
        )
    )


if __name__ == "__main__":
    bot.run(BOT_TOKEN)