@bot.command()
async def 龍說(ctx, *, message):
    """讓 yee式機器龍用 Webhook 模仿某人發言"""
    # 建立臨時 Webhook（名稱用發指令者的名字）
    webhook = await ctx.channel.create_webhook(
        name=ctx.author.display_name,
        avatar=await ctx.author.avatar.read() if ctx.author.avatar else None
    )

    # 透過 Webhook 發送訊息
    await webhook.send(
        content=f"🐉 {message}",
        username=f"{ctx.author.display_name}（龍龍代發）"
    )

    # 刪除 Webhook（避免累積）
    await webhook.delete()

@bot.command()
async def 龍噴火(ctx):
    """龍龍噴火特效（含嵌入訊息）"""
    webhook = await ctx.channel.create_webhook(name="yee式機器龍")

    embed = discord.Embed(
        title="🔥 龍龍噴火！",
        description="吼～～～～～ 燒毀一切！",
        color=discord.Color.red()
    )
    embed.set_footer(text="yee式機器龍 Webhook 版")

    await webhook.send(embed=embed, username="🐉 火焰龍龍")
    await webhook.delete()