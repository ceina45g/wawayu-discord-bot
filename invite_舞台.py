import discord
from discord.ext import commands
import asyncio
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO)

# 機器人設定
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'機器人已登入: {bot.user.name}')
    print(f'機器人ID: {bot.user.id}')
    print('-' * 30)

@bot.command(name='create_stage')
async def create_stage_channel(ctx, channel_name: str = "舞台頻道"):
    """
    創建舞台頻道
    用法: !create_stage [頻道名稱]
    """
    try:
        # 取得伺服器
        guild = ctx.guild

        # 檢查權限
        if not ctx.author.guild_permissions.manage_channels:
            await ctx.send("❌ 你沒有管理頻道的權限！")
            return

        # 創建舞台頻道
        stage_channel = await guild.create_stage_channel(
            name=channel_name,
            topic="歡迎加入舞台！",
            user_limit=0,  # 0表示無限制
        )

        await ctx.send(f"✅ 舞台頻道 **{channel_name}** 已成功創建！")
        return stage_channel

    except discord.Forbidden:
        await ctx.send("❌ 機器人沒有創建頻道的權限！")
    except Exception as e:
        await ctx.send(f"❌ 創建失敗: {str(e)}")

@bot.command(name='invite_to_stage')
async def invite_to_stage(ctx, role: discord.Role = None, member: discord.Member = None):
    """
    邀請成員加入舞台
    用法: !invite_to_stage @角色 或 !invite_to_stage @成員
    """
    try:
        # 檢查是否在語音頻道
        if not ctx.author.voice:
            await ctx.send("❌ 你必須在語音頻道/舞台中才能使用此指令！")
            return

        # 獲取當前語音頻道
        voice_state = ctx.author.voice
        channel = voice_state.channel

        # 檢查是否為舞台頻道
        if not isinstance(channel, discord.StageChannel):
            await ctx.send("❌ 你必須在舞台頻道中使用此指令！")
            return

        # 檢查權限
        if not ctx.author.guild_permissions.mute_members:
            await ctx.send("❌ 你沒有邀請成員加入舞台的權限！")
            return

        invited_count = 0

        if role:
            # 邀請整個角色的成員
            for member in role.members:
                if member != ctx.author and not member.bot:
                    try:
                        await channel.invite_member(member)
                        invited_count += 1
                        await asyncio.sleep(0.5)  # 避免請求過快
                    except discord.Forbidden:
                        await ctx.send(f"⚠️ 無法邀請 {member.mention}，可能權限不足")
                    except Exception as e:
                        await ctx.send(f"⚠️ 邀請 {member.mention} 失敗: {str(e)}")

            await ctx.send(f"✅ 已邀請 **{invited_count}** 位成員加入舞台！")

        elif member:
            # 邀請特定成員
            try:
                await channel.invite_member(member)
                await ctx.send(f"✅ 已邀請 {member.mention} 加入舞台！")
            except discord.Forbidden:
                await ctx.send(f"❌ 無法邀請 {member.mention}，可能權限不足")
            except Exception as e:
                await ctx.send(f"❌ 邀請失敗: {str(e)}")

        else:
            # 默認邀請所有頻道成員
            for member in channel.members:
                if member != ctx.author and not member.bot:
                    try:
                        await channel.invite_member(member)
                        invited_count += 1
                        await asyncio.sleep(0.5)
                    except:
                        pass
            await ctx.send(f"✅ 已邀請 **{invited_count}** 位成員加入舞台！")

    except Exception as e:
        await ctx.send(f"❌ 操作失敗: {str(e)}")

@bot.command(name='move_to_stage')
async def move_to_stage(ctx, user: discord.Member = None):
    """
    移動成員到舞台頻道
    用法: !move_to_stage @成員
    """
    try:
        # 檢查權限
        if not ctx.author.guild_permissions.move_members:
            await ctx.send("❌ 你沒有移動成員的權限！")
            return

        # 檢查發送者是否在舞台頻道
        if not ctx.author.voice or not isinstance(ctx.author.voice.channel, discord.StageChannel):
            await ctx.send("❌ 你必須在舞台頻道中才能使用此指令！")
            return

        target_member = user or ctx.author
        stage_channel = ctx.author.voice.channel

        # 檢查目標成員是否在語音頻道
        if not target_member.voice:
            await ctx.send(f"❌ {target_member.mention} 不在任何語音頻道中！")
            return

        # 移動成員到舞台
        await target_member.move_to(stage_channel)
        await ctx.send(f"✅ 已將 {target_member.mention} 移動到舞台！")

    except discord.Forbidden:
        await ctx.send("❌ 機器人沒有移動成員的權限！")
    except Exception as e:
        await ctx.send(f"❌ 移動失敗: {str(e)}")

@bot.command(name='stage_help')
async def stage_help(ctx):
    """顯示所有舞台相關指令"""
    help_text = """
    📋 **舞台頻道指令列表**
    
    `!create_stage [名稱]` - 創建新的舞台頻道
    `!invite_to_stage @角色` - 邀請整個角色的成員加入舞台
    `!invite_to_stage @成員` - 邀請特定成員加入舞台
    `!invite_to_stage` - 邀請當前頻道所有成員加入舞台
    `!move_to_stage @成員` - 移動成員到舞台頻道
    `!stage_speaker @成員` - 設定成員為演講者
    `!stage_remove @成員` - 移除成員的演講者權限
    `!stage_info` - 顯示當前舞台資訊
    `!stage_help` - 顯示此幫助訊息
    """
    await ctx.send(help_text)

@bot.command(name='stage_speaker')
async def set_speaker(ctx, member: discord.Member):
    """
    設定成員為舞台演講者
    用法: !stage_speaker @成員
    """
    try:
        if not ctx.author.voice or not isinstance(ctx.author.voice.channel, discord.StageChannel):
            await ctx.send("❌ 你必須在舞台頻道中！")
            return

        channel = ctx.author.voice.channel

        if not ctx.author.guild_permissions.mute_members:
            await ctx.send("❌ 你沒有管理演講者的權限！")
            return

        # 設定為演講者
        await channel.send(f"{member.mention} 已被設定為演講者")
        await member.move_to(channel, suppress=False)  # False = 啟用麥克風

        await ctx.send(f"✅ {member.mention} 現在是演講者！")

    except Exception as e:
        await ctx.send(f"❌ 操作失敗: {str(e)}")

@bot.command(name='stage_remove')
async def remove_speaker(ctx, member: discord.Member):
    """
    移除成員的演講者權限
    用法: !stage_remove @成員
    """
    try:
        if not ctx.author.voice or not isinstance(ctx.author.voice.channel, discord.StageChannel):
            await ctx.send("❌ 你必須在舞台頻道中！")
            return

        channel = ctx.author.voice.channel

        if not ctx.author.guild_permissions.mute_members:
            await ctx.send("❌ 你沒有管理演講者的權限！")
            return

        # 移除演講者權限（靜音）
        await member.move_to(channel, suppress=True)  # True = 靜音

        await ctx.send(f"✅ 已移除 {member.mention} 的演講者權限")

    except Exception as e:
        await ctx.send(f"❌ 操作失敗: {str(e)}")

@bot.command(name='stage_info')
async def stage_info(ctx):
    """顯示當前舞台的資訊"""
    try:
        if not ctx.author.voice:
            await ctx.send("❌ 你不在任何語音頻道中！")
            return

        channel = ctx.author.voice.channel

        if not isinstance(channel, discord.StageChannel):
            await ctx.send("❌ 這不是一個舞台頻道！")
            return

        # 獲取舞台資訊
        info = f"""
        📊 **舞台資訊**
        
        名稱: {channel.name}
        類別: {channel.category.name if channel.category else "無"}
        成員數: {len(channel.members)}
        話題: {channel.topic or "無"}
        伺服器: {channel.guild.name}
        """

        # 顯示所有成員
        if channel.members:
            info += "\n👥 **成員列表:**\n"
            for member in channel.members:
                status = "🎤 演講者" if not member.voice.suppress else "👤 聽眾"
                info += f"- {member.mention} ({status})\n"

        await ctx.send(info)

    except Exception as e:
        await ctx.send(f"❌ 獲取資訊失敗: {str(e)}")

# 設定機器人的指令前綴和權限檢查
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ 你沒有使用此指令的權限！")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ 缺少必要參數！請使用 `!stage_help` 查看正確用法。")
    else:
        await ctx.send(f"❌ 發生錯誤: {str(error)}")

# 啟動機器人
if __name__ == "__main__":
    # 請替換為你的機器人Token
    TOKEN = 'YOUR_BOT_TOKEN_HERE'

    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("❌ Token 無效，請檢查你的機器人Token！")
    except Exception as e:
        print(f"❌ 啟動失敗: {str(e)}")