"""
小智機器人 - Discord 討論串管理
使用 discord.py 2.x
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging

# ── 日誌設定 ──────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("小智機器人")

# ── 機器人初始化 ──────────────────────────────────────
intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ── 工具函式：檢查是否具備管理討論串權限 ────────────────
def has_manage_threads(member: discord.Member) -> bool:
    """檢查成員是否擁有 Manage Threads 權限。"""
    return member.guild_permissions.manage_threads


# ── 事件：機器人啟動 ──────────────────────────────────
@bot.event
async def on_ready():
    logger.info(f"小智機器人已上線：{bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        logger.info(f"已同步 {len(synced)} 個斜線指令")
    except Exception as e:
        logger.error(f"指令同步失敗：{e}")


# ── 斜線指令：建立討論串 ─────────────────────────────
@bot.tree.command(name="建立討論串", description="在目前頻道建立一個新的討論串")
@app_commands.describe(
    名稱="討論串名稱（最多 100 字）",
    內容="討論串的起始訊息內容",
    公開="是否為公開討論串（預設 True）",
    自動封存="自動封存時間（分鐘），可選 60 / 1440 / 4320 / 10080",
)
async def create_thread(
    interaction: discord.Interaction,
    名稱: str,
    內容: str = "",
    公開: bool = True,
    自動封存: int = 1440,
):
    """在指令所在的文字頻道中建立討論串。"""
    await interaction.response.defer(ephemeral=False)

    # 檢查頻道類型
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.followup.send("❌ 這個指令只能在文字頻道中使用。", ephemeral=True)
        return

    # 檢查權限
    if not channel.permissions_for(interaction.guild.me).create_public_threads:
        await interaction.followup.send("❌ 我沒有建立討論串的權限。", ephemeral=True)
        return

    # 驗證自動封存時間
    valid_durations = {60, 1440, 4320, 10080}
    if 自動封存 not in valid_durations:
        await interaction.followup.send(
            f"❌ 自動封存時間必須是 {valid_durations} 其中之一（分鐘）。",
            ephemeral=True,
        )
        return

    try:
        thread_type = discord.ChannelType.public_thread if 公開 else discord.ChannelType.private_thread

        thread = await channel.create_thread(
            name=名稱[:100],
            type=thread_type,
            auto_archive_duration=自動封存,
            reason=f"由 {interaction.user} 透過小智機器人建立",
        )

        # 將指令使用者加入討論串（私人討論串必須）
        if not 公開:
            await thread.add_user(interaction.user)

        # 發送起始訊息
        if 內容:
            await thread.send(內容)

        await interaction.followup.send(
            f"✅ 討論串已建立：{thread.mention}\n"
            f"自動封存時間：{自動封存} 分鐘",
            ephemeral=False,
        )
        logger.info(f"討論串已建立：{thread.name} (ID: {thread.id})")

    except discord.Forbidden:
        await interaction.followup.send("❌ 權限不足，無法建立討論串。", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.followup.send(f"❌ 建立失敗：{e}", ephemeral=True)
        logger.error(f"建立討論串失敗：{e}")


# ── 斜線指令：封存討論串 ─────────────────────────────
@bot.tree.command(name="封存討論串", description="封存目前的討論串")
async def archive_thread(interaction: discord.Interaction):
    """封存指令所在的討論串。"""
    thread = interaction.channel

    if not isinstance(thread, discord.Thread):
        await interaction.response.send_message("❌ 這個指令只能在討論串中使用。", ephemeral=True)
        return

    if not has_manage_threads(interaction.user):
        await interaction.response.send_message("❌ 你需要「管理討論串」權限才能封存。", ephemeral=True)
        return

    try:
        await thread.edit(archived=True, reason=f"由 {interaction.user} 手動封存")
        await interaction.response.send_message(f"✅ 討論串「{thread.name}」已封存。")
        logger.info(f"討論串已封存：{thread.name} (ID: {thread.id})")
    except discord.Forbidden:
        await interaction.response.send_message("❌ 權限不足，無法封存討論串。", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"❌ 封存失敗：{e}", ephemeral=True)


# ── 斜線指令：解除封存 ───────────────────────────────
@bot.tree.command(name="解除封存", description="解除目前討論串的封存狀態")
async def unarchive_thread(interaction: discord.Interaction):
    """解除指令所在討論串的封存。"""
    thread = interaction.channel

    if not isinstance(thread, discord.Thread):
        await interaction.response.send_message("❌ 這個指令只能在討論串中使用。", ephemeral=True)
        return

    if not has_manage_threads(interaction.user):
        await interaction.response.send_message("❌ 你需要「管理討論串」權限。", ephemeral=True)
        return

    try:
        await thread.edit(archived=False, reason=f"由 {interaction.user} 解除封存")
        await interaction.response.send_message(f"✅ 討論串「{thread.name}」已解除封存。")
    except discord.HTTPException as e:
        await interaction.response.send_message(f"❌ 操作失敗：{e}", ephemeral=True)


# ── 斜線指令：鎖定討論串 ─────────────────────────────
@bot.tree.command(name="鎖定討論串", description="鎖定目前的討論串，禁止新訊息")
async def lock_thread(interaction: discord.Interaction):
    """鎖定指令所在的討論串。"""
    thread = interaction.channel

    if not isinstance(thread, discord.Thread):
        await interaction.response.send_message("❌ 這個指令只能在討論串中使用。", ephemeral=True)
        return

    if not has_manage_threads(interaction.user):
        await interaction.response.send_message("❌ 你需要「管理討論串」權限。", ephemeral=True)
        return

    try:
        await thread.edit(locked=True, reason=f"由 {interaction.user} 鎖定")
        await interaction.response.send_message(f"🔒 討論串「{thread.name}」已鎖定。")
        logger.info(f"討論串已鎖定：{thread.name}")
    except discord.HTTPException as e:
        await interaction.response.send_message(f"❌ 鎖定失敗：{e}", ephemeral=True)


# ── 斜線指令：解鎖討論串 ─────────────────────────────
@bot.tree.command(name="解鎖討論串", description="解除目前討論串的鎖定")
async def unlock_thread(interaction: discord.Interaction):
    """解除指令所在討論串的鎖定。"""
    thread = interaction.channel

    if not isinstance(thread, discord.Thread):
        await interaction.response.send_message("❌ 這個指令只能在討論串中使用。", ephemeral=True)
        return

    if not has_manage_threads(interaction.user):
        await interaction.response.send_message("❌ 你需要「管理討論串」權限。", ephemeral=True)
        return

    try:
        await thread.edit(locked=False, reason=f"由 {interaction.user} 解鎖")
        await interaction.response.send_message(f"🔓 討論串「{thread.name}」已解鎖。")
    except discord.HTTPException as e:
        await interaction.response.send_message(f"❌ 解鎖失敗：{e}", ephemeral=True)


# ── 斜線指令：刪除討論串 ─────────────────────────────
@bot.tree.command(name="刪除討論串", description="刪除目前的討論串（不可復原）")
async def delete_thread(interaction: discord.Interaction):
    """刪除指令所在的討論串。"""
    thread = interaction.channel

    if not isinstance(thread, discord.Thread):
        await interaction.response.send_message("❌ 這個指令只能在討論串中使用。", ephemeral=True)
        return

    if not has_manage_threads(interaction.user):
        await interaction.response.send_message("❌ 你需要「管理討論串」權限。", ephemeral=True)
        return

    try:
        thread_name = thread.name
        await thread.delete(reason=f"由 {interaction.user} 刪除")
        await interaction.response.send_message(f"🗑️ 討論串「{thread_name}」已刪除。")
        logger.info(f"討論串已刪除：{thread_name}")
    except discord.Forbidden:
        await interaction.response.send_message("❌ 權限不足，無法刪除討論串。", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"❌ 刪除失敗：{e}", ephemeral=True)


# ── 事件：討論串建立時自動發送歡迎訊息 ────────────────
@bot.event
async def on_thread_create(thread: discord.Thread):
    """當有新討論串被建立時觸發。"""
    logger.info(f"偵測到新討論串：{thread.name} (ID: {thread.id})")

    # 可選：在討論串中發送提示
    try:
        await thread.send(
            f"👋 歡迎來到 **{thread.name}**！\n"
            f"使用 `/封存討論串`、`/鎖定討論串` 或 `/刪除討論串` 來管理這個討論串。"
        )
    except discord.HTTPException:
        pass  # 若無法發送則忽略


# ── 事件：討論串成員加入時記錄 ────────────────────────
@bot.event
async def on_thread_member_join(member: discord.ThreadMember):
    """當有成員加入討論串時觸發。"""
    logger.info(f"成員 {member.id} 加入了討論串 {member.thread_id}")


# ── 啟動機器人 ────────────────────────────────────────
if __name__ == "__main__":
    TOKEN = "你的_BOT_TOKEN_放在這裡"  # 建議改用環境變數
    bot.run(TOKEN)