import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# 啟用所有 Intents（必要，才能接收成員加入事件）
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ 機器人已登入為 {bot.user}")

# ========== 功能一：生成邀請連結 ==========
@bot.command(name="invite")
async def generate_invite(ctx, max_uses: int = 1, unique: bool = True):
    """
    在當前頻道生成邀請連結
    用法：!invite [使用次數] [是否唯一]
    範例：!invite 5 true
    """
    try:
        invite = await ctx.channel.create_invite(
            max_uses=max_uses,
            unique=unique
        )
        await ctx.send(f"🔗 邀請連結已生成：{invite}")
    except discord.Forbidden:
        await ctx.send("❌ 權限不足，無法生成邀請連結。")
    except Exception as e:
        await ctx.send(f"❌ 發生錯誤：{e}")

# ========== 功能二：查詢自己的邀請人數 ==========
@bot.command(name="myinvites")
async def my_invites(ctx):
    """
    查詢自己總共邀請了多少人加入伺服器
    用法：!myinvites
    """
    try:
        total = 0
        invites = await ctx.guild.invites()
        for invite in invites:
            if invite.inviter and invite.inviter.id == ctx.author.id:
                total += invite.uses
        await ctx.send(f"📊 {ctx.author.mention}，你總共邀請了 **{total}** 位成員！")
    except Exception as e:
        await ctx.send(f"❌ 發生錯誤：{e}")

# ========== 功能三：追蹤新成員是由誰邀請的 ==========
@bot.event
async def on_member_join(member):
    """
    當新成員加入時，顯示是誰邀請他進來的
    """
    try:
        invites_before = await member.guild.invites()

        # 等待短暫時間讓 Discord 更新邀請使用次數
        await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=1))

        invites_after = await member.guild.invites()

        for invite in invites_after:
            for old_invite in invites_before:
                if invite.code == old_invite.code and invite.uses > old_invite.uses:
                    inviter = invite.inviter
                    channel = member.guild.system_channel or member.guild.text_channels[0]
                    await channel.send(
                        f"👋 歡迎 {member.mention} 加入伺服器！邀請人：{inviter.mention if inviter else '未知'}"
                    )
                    return
    except Exception as e:
        print(f"追蹤邀請人時發生錯誤：{e}")

# ========== 功能四：伺服器所有邀請連結列表（管理員專用）==========
@bot.command(name="listinvites")
@commands.has_permissions(administrator=True)
async def list_invites(ctx):
    """
    列出伺服器所有的邀請連結及其使用次數（僅限管理員）
    用法：!listinvites
    """
    try:
        invites = await ctx.guild.invites()
        if not invites:
            await ctx.send("📭 此伺服器目前沒有任何邀請連結。")
            return

        message = "📋 **伺服器邀請連結列表：**\n"
        for invite in invites:
            inviter = invite.inviter.name if invite.inviter else "未知"
            message += f"- 代碼：{invite.code} | 使用次數：{invite.uses} | 建立者：{inviter}\n"
        await ctx.send(message)
    except Exception as e:
        await ctx.send(f"❌ 發生錯誤：{e}")

# ========== 啟動機器人 ==========
if __name__ == "__main__":
    bot.run(TOKEN)