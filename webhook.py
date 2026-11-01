import requests
import json
from datetime import datetime

class DiscordWebhook:
    def __init__(self, webhook_url):
        """
        初始化 Discord Webhook

        Args:
            webhook_url (str): Discord Webhook URL
        """
        self.webhook_url = webhook_url

    def send_message(self, content=None, username=None, avatar_url=None,
                     embeds=None, tts=False, file=None):
        """
        發送訊息到 Discord

        Args:
            content (str): 訊息內容
            username (str): 自訂使用者名稱
            avatar_url (str): 自訂頭像 URL
            embeds (list): Embed 物件列表
            tts (bool): 是否使用 TTS
            file (file): 要上傳的檔案
        """
        data = {}

        if content:
            data['content'] = content
        if username:
            data['username'] = username
        if avatar_url:
            data['avatar_url'] = avatar_url
        if embeds:
            data['embeds'] = embeds
        if tts:
            data['tts'] = tts

        headers = {'Content-Type': 'application/json'}

        try:
            if file:
                # 發送帶檔案的訊息
                files = {'file': file}
                response = requests.post(
                    self.webhook_url,
                    data={'payload_json': json.dumps(data)},
                    files=files
                )
            else:
                # 發送一般訊息
                response = requests.post(
                    self.webhook_url,
                    data=json.dumps(data),
                    headers=headers
                )

            if response.status_code == 204:
                print("✅ 訊息發送成功！")
                return True
            else:
                print(f"❌ 發送失敗，狀態碼: {response.status_code}")
                print(f"回應: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"❌ 請求錯誤: {e}")
            return False

    def send_embed(self, title, description, color=0x00ff00,
                   fields=None, footer=None, timestamp=True):
        """
        發送 Embed 訊息

        Args:
            title (str): 標題
            description (str): 描述
            color (int): 顏色 (十六進位)
            fields (list): 欄位列表 [{"name": "名稱", "value": "值", "inline": True}]
            footer (str): 頁腳文字
            timestamp (bool): 是否顯示時間戳
        """
        embed = {
            "title": title,
            "description": description,
            "color": color
        }

        if fields:
            embed["fields"] = fields

        if footer:
            embed["footer"] = {"text": footer}

        if timestamp:
            embed["timestamp"] = datetime.utcnow().isoformat()

        return self.send_message(embeds=[embed])

# 使用範例
if __name__ == "__main__":
    # 請替換成你的 Webhook URL
    WEBHOOK_URL = "https://discord.com/api/webhooks/你的ID/你的Token"

    # 建立 Webhook 實例
    webhook = DiscordWebhook(WEBHOOK_URL)

    # 1. 發送簡單訊息
    webhook.send_message("Hello Discord! 🚀")

    # 2. 發送自訂名稱和頭像的訊息
    webhook.send_message(
        content="這是由機器人發送的訊息！",
        username="我的機器人",
        avatar_url="https://example.com/avatar.png"
    )

    # 3. 發送 Embed 訊息
    webhook.send_embed(
        title="📢 系統通知",
        description="這是一則重要的系統通知訊息",
        color=0x00ff00,
        fields=[
            {"name": "狀態", "value": "✅ 正常運作", "inline": True},
            {"name": "版本", "value": "v2.0.1", "inline": True},
            {"name": "更新時間", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        ],
        footer="系統自動發送"
    )