import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# 設定 Intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ 蝦皮邀請機器人已啟動：{bot.user}")
    await bot.change_presence(activity=discord.Game(name="🛒 蝦皮購物特賣中 | !shopee_invite"))

@bot.command(name="shopee_invite")
async def shopee_invite(ctx, max_uses: int = 0, max_age: int = 0):
    """
    生成蝦皮購物頻道的邀請連結
    用法：!shopee_invite [使用次數] [有效秒數] (0 代表無限)
    """
    # 尋找名稱包含「蝦皮」的頻道
    target_channel = None
    for channel in ctx.guild.text_channels:
        if "蝦皮" in channel.name:
            target_channel = channel
            break
    
    if not target_channel:
        # 如果找不到，就用當前頻道
        target_channel = ctx.channel
        await ctx.send("⚠️ 找不到名稱包含「蝦皮」的頻道，將改為當前頻道生成邀請連結。")

    try:
        # 創建邀請連結
        invite = await target_channel.create_invite(
            max_uses=max_uses,
            max_age=max_age,
            unique=True,
            reason=f"蝦皮特派員 {ctx.author.name} 要求生成"
        )

        # 蝦皮橘色系 Embed (#EE4D2D)
        shopee_color = 0xEE4D2D
        
        embed = discord.Embed(
            title="🧡 蝦皮購物文字頻道 - 邀請函 🧡",
            description=f"歡迎加入我們的蝦皮購物討論區！這裡有最新的優惠資訊與推坑心得！",
            color=shopee_color
        )
        
        embed.add_field(name="🔗 專屬邀請連結", value=f"[點擊進入蝦皮頻道]({invite.url})", inline=False)
        embed.add_field(name="📢 目標頻道", value=target_channel.mention, inline=True)
        embed.add_field(name="🔢 使用限制", value="無限次" if max_uses == 0 else f"{max_uses} 次", inline=True)
        embed.add_field(name="⏰ 有效期限", value="永久有效" if max_age == 0 else f"{max_age} 秒", inline=True)
        
        embed.set_thumbnail(url="https://cf.shopee.tw/file/a47738096f30d09995c7cf1b3769c27f") # 蝦皮圖示連結
        embed.set_footer(text=f"由 {ctx.author.display_name} 誠心推薦 · 趕快加入以免錯過優惠！", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send("❌ 吼！龍龍沒有權限建立邀請連結，請確認權限設定。")
    except Exception as e:
        await ctx.send(f"❌ 發生錯誤：{e}")

if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("錯誤：找不到 DISCORD_TOKEN，請檢查 .env 檔案。")
