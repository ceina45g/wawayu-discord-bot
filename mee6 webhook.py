# ... (前面的 import 保持不變)
import aiohttp
from discord import Webhook, AsyncWebhookAdapter

# ... (bot 實例和事件保持不變)

@bot.command()
async def webhook_test(ctx, *, message: str):
    """測試發送 Webhook 訊息"""
    webhook_url = "你的webhook網址" # 請替換成你的實際網址

    try:
        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(webhook_url, adapter=AsyncWebhookAdapter(session))
            await webhook.send(
                content=message,
                username="我的測試機器人", # 可選：自訂名稱
                # avatar_url="圖片網址"  # 可選：自訂頭像
            )
        await ctx.send(f"✅ 已透過 Webhook 發送訊息：{message}")
    except Exception as e:
        await ctx.send(f"❌ 發送失敗：{e}")