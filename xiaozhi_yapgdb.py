#!/usr/bin/env python3
"""
xiaozhi_yagpdb_reviewer.py
小智机器人 —— YAGPDB 页面审核员
用途：监听 Discord 消息，执行内容审核，并与 YAGPDB 联动记录日志。
"""

import os
import re
import logging
import aiohttp
import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta

# ======================== 配置区域 ========================
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
YAGPDB_WEBHOOK_URL = os.getenv("YAGPDB_WEBHOOK_URL", "")  # 可选：YAGPDB 日志 Webhook
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))    # 审核日志频道 ID

# 审核规则配置
BAD_WORDS = [
    "spam", "scam", "phishing", "恶意链接",
    # 在此添加更多违禁词
]

SUSPICIOUS_PATTERNS = [
    re.compile(r"https?://(?:bit\.ly|tinyurl\.com|goo\.gl)/\w+", re.I),  # 短链接
    re.compile(r"(?:free|gratis|免费).{0,20}(?:nitro|gift|礼物)", re.I),      # 免费 Nitro 骗局
    re.compile(r"@everyone|@here", re.I),                                    # 滥用提及
]

# 违规处罚阈值
VIOLATION_THRESHOLD = 3   # 3 次违规触发 timeout
TIMEOUT_MINUTES = 10      # 禁言时长

# ========================================================

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("xiaozhi_reviewer")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 用户违规记录：{user_id: [(timestamp, reason), ...]}
violation_records: dict[int, list[tuple[datetime, str]]] = {}


def check_message_content(content: str) -> list[str]:
    """检查消息内容，返回违规原因列表。"""
    violations = []
    content_lower = content.lower()

    for word in BAD_WORDS:
        if word.lower() in content_lower:
            violations.append(f"包含违禁词: {word}")

    for pattern in SUSPICIOUS_PATTERNS:
        if pattern.search(content):
            violations.append(f"匹配可疑模式: {pattern.pattern}")

    return violations


def record_violation(user_id: int, reason: str) -> int:
    """记录违规，返回最近时间窗口内的违规次数。"""
    now = datetime.utcnow()
    if user_id not in violation_records:
        violation_records[user_id] = []

    violation_records[user_id].append((now, reason))

    # 只保留最近 1 小时的记录
    cutoff = now - timedelta(hours=1)
    violation_records[user_id] = [
        (t, r) for t, r in violation_records[user_id] if t > cutoff
    ]

    return len(violation_records[user_id])


async def send_yagpdb_log(embed: discord.Embed):
    """通过 Webhook 将审核日志发送到 YAGPDB 日志频道。"""
    if not YAGPDB_WEBHOOK_URL:
        return
    try:
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(YAGPDB_WEBHOOK_URL, session=session)
            await webhook.send(embed=embed, username="小智审核员")
    except Exception as e:
        logger.error(f"发送 YAGPDB Webhook 失败: {e}")


@bot.event
async def on_ready():
    logger.info(f"小智审核员已上线: {bot.user} (ID: {bot.user.id})")
    logger.info(f"已加入 {len(bot.guilds)} 个服务器")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="服务器内容")
    )


@bot.event
async def on_message(message: discord.Message):
    # 忽略机器人自己的消息
    if message.author.bot:
        return

    violations = check_message_content(message.content)
    if not violations:
        return

    reason = "; ".join(violations)
    logger.info(f"检测到违规: {message.author} 在 #{message.channel} — {reason}")

    # 删除违规消息
    try:
        await message.delete()
    except discord.Forbidden:
        logger.warning("缺少删除消息权限")

    # 记录违规
    count = record_violation(message.author.id, reason)

    # 发送警告
    warning_embed = discord.Embed(
        title="⚠️ 内容审核警告",
        description=f"{message.author.mention}，你的消息因以下原因被移除：\n`{reason}`",
        color=discord.Color.orange(),
        timestamp=datetime.utcnow()
    )
    warning_embed.set_footer(text=f"小智审核员 | 近期违规次数: {count}")
    try:
        await message.channel.send(embed=warning_embed, delete_after=15)
    except discord.Forbidden:
        pass

    # 达到阈值触发 timeout
    if count >= VIOLATION_THRESHOLD:
        try:
            until = discord.utils.utcnow() + timedelta(minutes=TIMEOUT_MINUTES)
            await message.author.timeout(until, reason=f"累计违规 {count} 次: {reason}")
            logger.info(f"已对 {message.author} 执行 timeout ({TIMEOUT_MINUTES}分钟)")
        except discord.Forbidden:
            logger.warning("缺少 timeout 权限")

    # 发送日志到 YAGPDB
    log_embed = discord.Embed(
        title="📋 审核日志",
        color=discord.Color.red(),
        timestamp=datetime.utcnow()
    )
    log_embed.add_field(name="用户", value=f"{message.author} ({message.author.id})", inline=True)
    log_embed.add_field(name="频道", value=message.channel.mention, inline=True)
    log_embed.add_field(name="原因", value=reason, inline=False)
    log_embed.add_field(name="累计违规", value=str(count), inline=True)
    log_embed.set_footer(text="小智审核员 · YAGPDB 联动")

    await send_yagpdb_log(log_embed)

    if LOG_CHANNEL_ID:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            try:
                await log_channel.send(embed=log_embed)
            except discord.Forbidden:
                pass

    await bot.process_commands(message)


@bot.command(name="review_status")
@commands.has_permissions(manage_messages=True)
async def review_status(ctx):
    """查看当前审核系统的状态。"""
    active_users = len(violation_records)
    embed = discord.Embed(
        title="🔍 小智审核员状态",
        color=discord.Color.blue()
    )
    embed.add_field(name="监控中用户", value=str(active_users), inline=True)
    embed.add_field(name="违禁词数量", value=str(len(BAD_WORDS)), inline=True)
    embed.add_field(name="可疑模式", value=str(len(SUSPICIOUS_PATTERNS)), inline=True)
    embed.set_footer(text="YAGPDB 页面审核员 · 小智")
    await ctx.send(embed=embed)


@bot.command(name="clear_violations")
@commands.has_permissions(administrator=True)
async def clear_violations(ctx, member: discord.Member):
    """清除指定用户的违规记录。"""
    violation_records.pop(member.id, None)
    await ctx.send(f"✅ 已清除 {member.mention} 的违规记录。")


if __name__ == "__main__":
    if not DISCORD_TOKEN or DISCORD_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("请设置 DISCORD_BOT_TOKEN 环境变量或直接填入 token")
        raise SystemExit(1)

    bot.run(DISCORD_TOKEN)