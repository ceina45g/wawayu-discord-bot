from discord_webhook import DiscordWebhook, DiscordEmbed

# 1. 貼上你的 Webhook URL
webhook = DiscordWebhook(url="你的 Webhook URL", content="這是一則普通訊息")

# 2. 建立一個華麗的嵌入訊息 (Embed)
embed = DiscordEmbed(
    title="我的標題",
    description="這是一段更詳細的敘述",
    color="03b2f8"  # 可設定顏色
)
embed.set_author(name="作者名稱")
embed.set_footer(text="頁尾文字")
embed.set_timestamp()  # 自動加上時間戳記

# 3. 將 Embed 加入 Webhook 並發送
webhook.add_embed(embed)
response = webhook.execute()