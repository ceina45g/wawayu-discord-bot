import requests
import json
import time
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import os
import sys

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('webhook_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WebhookBot:
    """Discord Webhook 訊息發送機器人"""

    def __init__(self, webhook_url: str):
        """
        初始化機器人

        Args:
            webhook_url (str): Discord Webhook URL
        """
        self.webhook_url = webhook_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DiscordWebhookBot/1.0',
            'Content-Type': 'application/json'
        })
        logger.info("🤖 Webhook 機器人初始化完成")

    # ============ 基本訊息發送 ============

    def send_text(self, message: str, username: Optional[str] = None,
                  avatar_url: Optional[str] = None) -> bool:
        """
        發送純文字訊息

        Args:
            message (str): 要發送的訊息
            username (str): 自訂顯示名稱
            avatar_url (str): 自訂頭像 URL

        Returns:
            bool: 發送成功與否
        """
        data = {"content": message}
        if username:
            data["username"] = username
        if avatar_url:
            data["avatar_url"] = avatar_url

        return self._send_request(data)

    def send_embed(self, title: str, description: str,
                   color: str = "#00ff00",
                   fields: Optional[List[Dict]] = None,
                   footer: Optional[str] = None,
                   thumbnail: Optional[str] = None,
                   image: Optional[str] = None,
                   author: Optional[Dict] = None) -> bool:
        """
        發送 Embed 訊息

        Args:
            title (str): 標題
            description (str): 描述
            color (str): 顏色 (十六進位色碼)
            fields (List[Dict]): 欄位列表
            footer (str): 頁腳文字
            thumbnail (str): 縮圖 URL
            image (str): 圖片 URL
            author (Dict): 作者資訊

        Returns:
            bool: 發送成功與否
        """
        # 轉換顏色
        if color.startswith("#"):
            color = int(color[1:], 16)

        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.utcnow().isoformat()
        }

        if fields:
            embed["fields"] = fields
        if footer:
            embed["footer"] = {"text": footer}
        if thumbnail:
            embed["thumbnail"] = {"url": thumbnail}
        if image:
            embed["image"] = {"url": image}
        if author:
            embed["author"] = author

        return self._send_request({"embeds": [embed]})

    def send_embed_text(self, title: str, message: str,
                        color: str = "#00ff00") -> bool:
        """
        發送文字轉 Embed 的訊息（簡化版）

        Args:
            title (str): 標題
            message (str): 訊息內容
            color (str): 顏色

        Returns:
            bool: 發送成功與否
        """
        return self.send_embed(
            title=title,
            description=message,
            color=color
        )

    # ============ 進階訊息發送 ============

    def send_file(self, file_path: str, content: Optional[str] = None,
                  username: Optional[str] = None) -> bool:
        """
        發送檔案

        Args:
            file_path (str): 檔案路徑
            content (str): 附加文字訊息
            username (str): 自訂顯示名稱

        Returns:
            bool: 發送成功與否
        """
        if not os.path.exists(file_path):
            logger.error(f"❌ 檔案不存在: {file_path}")
            return False

        try:
            data = {}
            if content:
                data["content"] = content
            if username:
                data["username"] = username

            with open(file_path, 'rb') as f:
                files = {
                    'file': (os.path.basename(file_path), f, 'application/octet-stream')
                }
                response = self.session.post(
                    self.webhook_url,
                    data={'payload_json': json.dumps(data)},
                    files=files
                )

            if response.status_code == 204:
                logger.info(f"✅ 檔案發送成功: {os.path.basename(file_path)}")
                return True
            else:
                logger.error(f"❌ 檔案發送失敗: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"❌ 發送檔案錯誤: {e}")
            return False

    def send_multi_embed(self, embeds: List[Dict]) -> bool:
        """
        發送多個 Embed 訊息

        Args:
            embeds (List[Dict]): Embed 列表

        Returns:
            bool: 發送成功與否
        """
        if len(embeds) > 10:
            logger.warning("⚠️ Discord 限制最多 10 個 Embed，將只發送前 10 個")
            embeds = embeds[:10]

        return self._send_request({"embeds": embeds})

    # ============ 特殊訊息類型 ============

    def send_success(self, title: str, message: str,
                     details: Optional[Dict] = None) -> bool:
        """
        發送成功訊息（綠色）

        Args:
            title (str): 標題
            message (str): 訊息內容
            details (Dict): 詳細資訊

        Returns:
            bool: 發送成功與否
        """
        fields = []
        if details:
            for key, value in details.items():
                fields.append({
                    "name": key,
                    "value": str(value),
                    "inline": True
                })

        return self.send_embed(
            title=f"✅ {title}",
            description=message,
            color="#00ff00",
            fields=fields,
            footer=f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def send_error(self, title: str, message: str,
                   error_details: Optional[str] = None) -> bool:
        """
        發送錯誤訊息（紅色）

        Args:
            title (str): 標題
            message (str): 錯誤訊息
            error_details (str): 詳細錯誤資訊

        Returns:
            bool: 發送成功與否
        """
        fields = []
        if error_details:
            fields.append({
                "name": "❌ 錯誤詳細",
                "value": f"```\n{error_details}\n```",
                "inline": False
            })

        return self.send_embed(
            title=f"❌ {title}",
            description=message,
            color="#ff0000",
            fields=fields,
            footer=f"錯誤時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def send_warning(self, title: str, message: str,
                     suggestion: Optional[str] = None) -> bool:
        """
        發送警告訊息（黃色）

        Args:
            title (str): 標題
            message (str): 警告訊息
            suggestion (str): 建議

        Returns:
            bool: 發送成功與否
        """
        fields = []
        if suggestion:
            fields.append({
                "name": "💡 建議",
                "value": suggestion,
                "inline": False
            })

        return self.send_embed(
            title=f"⚠️ {title}",
            description=message,
            color="#ffff00",
            fields=fields,
            footer=f"警告時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def send_info(self, title: str, message: str,
                  info_details: Optional[Dict] = None) -> bool:
        """
        發送資訊訊息（藍色）

        Args:
            title (str): 標題
            message (str): 資訊內容
            info_details (Dict): 詳細資訊

        Returns:
            bool: 發送成功與否
        """
        fields = []
        if info_details:
            for key, value in info_details.items():
                fields.append({
                    "name": key,
                    "value": str(value),
                    "inline": True
                })

        return self.send_embed(
            title=f"ℹ️ {title}",
            description=message,
            color="#00aaff",
            fields=fields,
            footer=f"資訊時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    # ============ 批量發送 ============

    def send_batch(self, messages: List[str], delay: float = 1.0) -> Dict[str, int]:
        """
        批量發送訊息

        Args:
            messages (List[str]): 訊息列表
            delay (float): 每條訊息間隔秒數

        Returns:
            Dict[str, int]: 發送統計
        """
        stats = {"success": 0, "failed": 0}

        for i, message in enumerate(messages, 1):
            logger.info(f"📤 發送第 {i}/{len(messages)} 條訊息")

            if self.send_text(message):
                stats["success"] += 1
            else:
                stats["failed"] += 1

            if i < len(messages):
                time.sleep(delay)

        logger.info(f"📊 批量發送完成: 成功 {stats['success']}, 失敗 {stats['failed']}")
        return stats

    # ============ 核心方法 ============

    def _send_request(self, data: Dict[str, Any]) -> bool:
        """
        發送 HTTP 請求到 Discord

        Args:
            data (Dict): 要發送的資料

        Returns:
            bool: 發送成功與否
        """
        try:
            response = self.session.post(
                self.webhook_url,
                json=data,
                timeout=10
            )

            if response.status_code == 204:
                logger.debug("✅ 訊息發送成功")
                return True
            elif response.status_code == 429:
                # 速率限制
                retry_after = response.json().get('retry_after', 1)
                logger.warning(f"⚠️ 速率限制，等待 {retry_after} 秒")
                time.sleep(retry_after)
                return self._send_request(data)  # 重試
            else:
                logger.error(f"❌ 發送失敗: {response.status_code}")
                logger.debug(f"回應內容: {response.text}")
                return False

        except requests.exceptions.Timeout:
            logger.error("❌ 請求超時")
            return False
        except requests.exceptions.ConnectionError:
            logger.error("❌ 連線錯誤")
            return False
        except Exception as e:
            logger.error(f"❌ 未知錯誤: {e}")
            return False

# ============ 使用範例 ============

def main():
    """主程式範例"""

    # 請替換成你的 Webhook URL
    WEBHOOK_URL = "https://discord.com/api/webhooks/你的ID/你的Token"

    # 建立機器人實例
    bot = WebhookBot(WEBHOOK_URL)

    # 1. 發送簡單文字訊息
    print("\n📝 發送文字訊息...")
    bot.send_text("Hello Discord! 這是一個測試訊息 🚀")

    # 2. 發送帶有名稱的訊息
    print("\n👤 發送自訂名稱訊息...")
    bot.send_text(
        "這是由自訂名稱發送的訊息！",
        username="我的機器人",
        avatar_url="https://cdn.discordapp.com/embed/avatars/1.png"
    )

    # 3. 發送 Embed 訊息
    print("\n📊 發送 Embed 訊息...")
    bot.send_embed(
        title="📊 系統狀態報告",
        description="當前系統運作狀態總覽",
        color="#3498db",
        fields=[
            {"name": "CPU 使用率", "value": "45%", "inline": True},
            {"name": "記憶體使用率", "value": "62%", "inline": True},
            {"name": "硬碟使用率", "value": "78%", "inline": True},
            {"name": "線上使用者", "value": "1,234 人", "inline": True},
            {"name": "系統正常運行", "value": "3天 4小時", "inline": True}
        ],
        footer="自動監控系統",
        thumbnail="https://cdn.discordapp.com/embed/avatars/0.png"
    )

    # 4. 發送成功訊息
    print("\n✅ 發送成功訊息...")
    bot.send_success(
        "部署完成",
        "應用程式已成功部署到生產環境",
        {
            "版本": "v2.1.0",
            "部署時間": "2026-01-18 14:30",
            "狀態": "✅ 正常運作"
        }
    )

    # 5. 發送錯誤訊息
    print("\n❌ 發送錯誤訊息...")
    bot.send_error(
        "資料庫連線失敗",
        "無法連接到主要資料庫伺服器",
        "Connection refused: 192.168.1.100:3306"
    )

    # 6. 發送警告訊息
    print("\n⚠️ 發送警告訊息...")
    bot.send_warning(
        "磁碟空間不足",
        "系統磁碟可用空間低於 10%",
        "請清理不必要的檔案或擴充磁碟空間"
    )

    # 7. 發送資訊訊息
    print("\nℹ️ 發送資訊訊息...")
    bot.send_info(
        "系統維護公告",
        "系統將於今晚進行例行維護",
        {
            "維護時間": "2026-01-19 02:00",
            "預計持續": "2 小時",
            "影響範圍": "所有服務"
        }
    )

    # 8. 批量發送訊息
    print("\n📤 批量發送訊息...")
    messages = [
        "這是第 1 條訊息",
        "這是第 2 條訊息",
        "這是第 3 條訊息"
    ]
    bot.send_batch(messages, delay=0.5)

    print("\n🎉 所有訊息發送完成！")

if __name__ == "__main__":
    main()