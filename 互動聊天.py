import discord
from discord.ext import commands
import asyncio

# 機器人設置
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'✅ 機器人已登入為 {bot.user}')
    print(f'📊 已連線到 {len(bot.guilds)} 個伺服器')

    # 設定機器人狀態
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="伺服器成員 | !invite"
        )
    )

@bot.command(name='invite')
async def create_invite(ctx, max_uses: int = 1, max_age: int = 86400):
    """
    創建文字頻道的邀請連結
    用法: !invite [最多使用次數] [有效秒數]
    範例: !invite 5 3600  (5次使用, 1小時有效)
    """

    # 檢查是否有權限創建邀請
    if not ctx.guild.me.guild_permissions.create_instant_invite:
        await ctx.send("❌ 我沒有權限創建邀請連結！")
        return

    # 檢查使用者是否有管理權限
    if not ctx.author.guild_permissions.manage_guild:
        await ctx.send("❌ 你沒有權限使用這個指令！需要管理伺服器權限。")
        return

    try:
        # 創建邀請連結
        invite = await ctx.channel.create_invite(
            max_uses=max_uses,
            max_age=max_age,
            reason=f"由 {ctx.author.name} 創建"
        )

        # 創建嵌入訊息
        embed = discord.Embed(
            title="📨 文字頻道邀請連結",
            description=f"邀請連結已創建成功！",
            color=discord.Color.green()
        )
        embed.add_field(name="🔗 連結", value=f"[點擊加入]({invite.url})", inline=False)
        embed.add_field(name="📋 邀請代碼", value=f"`{invite.code}`", inline=True)
        embed.add_field(name="👤 創建者", value=ctx.author.mention, inline=True)
        embed.add_field(name="⏰ 有效期限", value=f"{max_age//60} 分鐘" if max_age < 3600 else f"{max_age//3600} 小時", inline=True)
        embed.add_field(name="🔢 使用次數限制", value=f"{max_uses} 次", inline=True)
        embed.add_field(name="📢 頻道", value=ctx.channel.mention, inline=True)
        embed.set_footer(text=f"伺服器: {ctx.guild.name}")

        # 發送邀請訊息
        await ctx.send(embed=embed)

        # 也在私訊中發送連結（確保成員能收到）
        try:
            await ctx.author.send(f"📨 你創建的邀請連結：{invite.url}")
        except discord.Forbidden:
            pass  # 如果無法發送私訊就跳過

    except discord.Forbidden:
        await ctx.send("❌ 我沒有權限在這個頻道創建邀請連結！")
    except discord.HTTPException as e:
        await ctx.send(f"❌ 創建邀請時發生錯誤：{str(e)}")
    except Exception as e:
        await ctx.send(f"❌ 發生未知錯誤：{str(e)}")

@bot.command(name='invite_info')
async def invite_info(ctx, invite_code: str = None):
    """
    查詢邀請連結的詳細資訊
    用法: !invite_info [邀請代碼]
    """

    if not invite_code:
        await ctx.send("❌ 請提供邀請代碼！\n用法：`!invite_info 邀請代碼`")
        return

    try:
        # 獲取邀請資訊
        invite = await bot.fetch_invite(invite_code)

        embed = discord.Embed(
            title="📊 邀請連結詳細資訊",
            color=discord.Color.blue()
        )
        embed.add_field(name="🔗 連結", value=f"[點擊加入]({invite.url})", inline=False)
        embed.add_field(name="📋 邀請代碼", value=f"`{invite.code}`", inline=True)
        embed.add_field(name="👤 創建者", value=invite.inviter.name if invite.inviter else "未知", inline=True)
        embed.add_field(name="📢 頻道", value=f"#{invite.channel.name}" if invite.channel else "未知", inline=True)
        embed.add_field(name="🏠 伺服器", value=invite.guild.name if invite.guild else "未知", inline=True)
        embed.add_field(name="🔢 使用次數", value=f"{invite.uses} 次", inline=True)
        embed.add_field(name="⏰ 到期時間", value=f"<t:{int(invite.expires_at.timestamp())}:R>" if invite.expires_at else "永不過期", inline=True)

        await ctx.send(embed=embed)

    except discord.NotFound:
        await ctx.send("❌ 找不到這個邀請連結，請確認邀請代碼是否正確。")
    except discord.HTTPException as e:
        await ctx.send(f"❌ 查詢邀請資訊時發生錯誤：{str(e)}")

@bot.command(name='invites_list')
async def list_invites(ctx):
    """
    列出伺服器中所有的邀請連結
    """

    if not ctx.author.guild_permissions.manage_guild:
        await ctx.send("❌ 你沒有權限使用這個指令！需要管理伺服器權限。")
        return

    try:
        # 獲取伺服器所有邀請
        invites = await ctx.guild.invites()

        if not invites:
            await ctx.send("📭 這個伺服器目前沒有有效的邀請連結。")
            return

        # 創建嵌入訊息
        embed = discord.Embed(
            title="📨 伺服器邀請連結列表",
            color=discord.Color.gold()
        )

        for invite in invites[:10]:  # 只顯示前10個
            channel_name = f"#{invite.channel.name}" if invite.channel else "未知"
            inviter_name = invite.inviter.name if invite.inviter else "未知"
            expires = f"<t:{int(invite.expires_at.timestamp())}:R>" if invite.expires_at else "永不過期"

            embed.add_field(
                name=f"🔗 {invite.code}",
                value=f"頻道: {channel_name}\n創建者: {inviter_name}\n使用次數: {invite.uses}\n到期: {expires}",
                inline=False
            )

        if len(invites) > 10:
            embed.set_footer(text=f"還有 {len(invites)-10} 個邀請連結未顯示")

        await ctx.send(embed=embed)

    except discord.HTTPException as e:
        await ctx.send(f"❌ 獲取邀請列表時發生錯誤：{str(e)}")

@bot.command(name='delete_invite')
async def delete_invite(ctx, invite_code: str):
    """
    刪除指定的邀請連結
    用法: !delete_invite [邀請代碼]
    """

    if not ctx.author.guild_permissions.manage_guild:
        await ctx.send("❌ 你沒有權限使用這個指令！需要管理伺服器權限。")
        return

    try:
        # 獲取並刪除邀請
        invite = await bot.fetch_invite(invite_code)
        await invite.delete(reason=f"由 {ctx.author.name} 刪除")

        await ctx.send(f"✅ 已成功刪除邀請連結 `{invite_code}`")

    except discord.NotFound:
        await ctx.send("❌ 找不到這個邀請連結，請確認邀請代碼是否正確。")
    except discord.Forbidden:
        await ctx.send("❌ 我沒有權限刪除這個邀請連結！")
    except discord.HTTPException as e:
        await ctx.send(f"❌ 刪除邀請時發生錯誤：{str(e)}")

# 錯誤處理
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ 你沒有權限使用這個指令！")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ 參數格式錯誤！請檢查輸入的數值是否正確。")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ 缺少必要參數！請檢查指令用法。")
    else:
        await ctx.send(f"❌ 發生錯誤：{str(error)}")
        print(f"錯誤: {error}")

# 啟動機器人
if __name__ == "__main__":
    # 請將 'YOUR_BOT_TOKEN' 替換為你的機器人 Token
    TOKEN = 'YOUR_BOT_TOKEN'
    bot.run(TOKEN)