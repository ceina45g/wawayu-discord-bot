import discord
from discord.ext import commands
import json
import os
from typing import Dict, List

# 設定檔
CONFIG_FILE = "config.json"

# 預設設定
DEFAULT_CONFIG = {
    "guild_id": None,  # 伺服器ID
    "category_id": None,  # 語言頻道分類ID
    "role_channel_id": None,  # 語言選擇頻道ID
    "languages": {
        "中文": {
            "role_name": "中文",
            "channel_name": "中文聊天",
            "emoji": "🇨🇳",
            "color": 0xFF6B6B
        },
        "English": {
            "role_name": "English",
            "channel_name": "english-chat",
            "emoji": "🇺🇸",
            "color": 0x4ECDC4
        },
        "日本語": {
            "role_name": "日本語",
            "channel_name": "日本語チャット",
            "emoji": "🇯🇵",
            "color": 0xFFE66D
        },
        "한국어": {
            "role_name": "한국어",
            "channel_name": "한국어-채팅",
            "emoji": "🇰🇷",
            "color": 0x95E1D3
        }
    }
}

class LanguageBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.config = self.load_config()

    def load_config(self):
        """載入設定檔"""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            self.save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG

    def save_config(self, config):
        """儲存設定檔"""
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)

    async def setup_hook(self):
        """機器人啟動時執行"""
        await self.add_cog(LanguageCog(self))
        await self.tree.sync()
        print("✅ 機器人已啟動並同步指令")

class LanguageCog(commands.Cog):
    def __init__(self, bot: LanguageBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"✅ 已登入為 {self.bot.user}")
        print(f"📊 已載入 {len(self.bot.config['languages'])} 種語言設定")

        # 初始化伺服器設定
        await self.setup_server()

    async def setup_server(self):
        """初始化伺服器設定"""
        guild = self.bot.get_guild(self.bot.config["guild_id"])
        if not guild:
            print("⚠️ 請先使用 /setup 指令設定伺服器")
            return

        # 檢查或建立語言角色
        for lang_name, lang_data in self.bot.config["languages"].items():
            role = discord.utils.get(guild.roles, name=lang_data["role_name"])
            if not role:
                role = await guild.create_role(
                    name=lang_data["role_name"],
                    color=lang_data["color"],
                    mentionable=True
                )
                print(f"✅ 已建立角色: {lang_name}")

    @commands.hybrid_command(name="setup", description="設定語言頻道系統")
    async def setup(self, ctx: commands.Context):
        """設定語言頻道系統（需要管理員權限）"""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ 你沒有權限使用此指令")
            return

        # 更新設定
        self.bot.config["guild_id"] = ctx.guild.id
        self.bot.save_config(self.bot.config)

        # 建立分類
        category = await ctx.guild.create_category("🌍 語言頻道")
        self.bot.config["category_id"] = category.id

        # 建立語言頻道
        for lang_name, lang_data in self.bot.config["languages"].items():
            channel = await ctx.guild.create_text_channel(
                lang_data["channel_name"],
                category=category
            )
            # 設定權限：只有該語言角色可以查看
            role = discord.utils.get(ctx.guild.roles, name=lang_data["role_name"])
            if role:
                await channel.set_permissions(
                    ctx.guild.default_role,
                    view_channel=False
                )
                await channel.set_permissions(
                    role,
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )
            print(f"✅ 已建立頻道: {lang_data['channel_name']}")

        # 建立語言選擇頻道
        channel = await ctx.guild.create_text_channel(
            "🌐 語言選擇",
            category=category
        )
        self.bot.config["role_channel_id"] = channel.id
        self.bot.save_config(self.bot.config)

        # 發送語言選擇訊息
        await self.send_language_selector(channel)

        await ctx.send("✅ 語言頻道系統設定完成！")

    async def send_language_selector(self, channel: discord.TextChannel):
        """發送語言選擇器訊息"""
        embed = discord.Embed(
            title="🌍 選擇你的語言頻道",
            description="點擊下方按鈕來選擇你想加入的語言頻道！\n"
                        "你可以選擇多個語言，點擊已選擇的按鈕可以取消。",
            color=0x5865F2
        )

        # 建立按鈕視圖
        view = discord.ui.View(timeout=None)

        for lang_name, lang_data in self.bot.config["languages"].items():
            button = LanguageButton(
                lang_name=lang_name,
                lang_data=lang_data,
                label=f"{lang_data['emoji']} {lang_name}",
                style=discord.ButtonStyle.primary
            )
            view.add_item(button)

        await channel.send(embed=embed, view=view)

    @commands.hybrid_command(name="add_language", description="新增語言")
    async def add_language(
            self,
            ctx: commands.Context,
            name: str,
            role_name: str,
            channel_name: str,
            emoji: str,
            color: str = "#5865F2"
    ):
        """新增語言（需要管理員權限）"""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ 你沒有權限使用此指令")
            return

        # 轉換顏色
        color_int = int(color.replace("#", ""), 16)

        # 新增語言設定
        self.bot.config["languages"][name] = {
            "role_name": role_name,
            "channel_name": channel_name,
            "emoji": emoji,
            "color": color_int
        }
        self.bot.save_config(self.bot.config)

        # 建立角色和頻道
        guild = ctx.guild
        category = guild.get_channel(self.bot.config["category_id"])

        # 建立角色
        role = await guild.create_role(
            name=role_name,
            color=color_int,
            mentionable=True
        )

        # 建立頻道
        channel = await guild.create_text_channel(
            channel_name,
            category=category
        )

        # 設定權限
        await channel.set_permissions(
            guild.default_role,
            view_channel=False
        )
        await channel.set_permissions(
            role,
            view_channel=True,
            send_messages=True,
            read_message_history=True
        )

        # 更新選擇器
        channel = guild.get_channel(self.bot.config["role_channel_id"])
        await channel.purge(limit=1)  # 清除舊訊息
        await self.send_language_selector(channel)

        await ctx.send(f"✅ 已新增語言: {name}")

class LanguageButton(discord.ui.Button):
    def __init__(self, lang_name: str, lang_data: Dict, **kwargs):
        super().__init__(**kwargs)
        self.lang_name = lang_name
        self.lang_data = lang_data
        self.custom_id = f"lang_{lang_name}"

    async def callback(self, interaction: discord.Interaction):
        """按鈕點擊回調"""
        member = interaction.user
        guild = interaction.guild

        # 獲取角色
        role = discord.utils.get(guild.roles, name=self.lang_data["role_name"])
        if not role:
            await interaction.response.send_message(
                f"❌ 找不到 {self.lang_name} 角色，請聯繫管理員",
                ephemeral=True
            )
            return

        # 切換角色
        if role in member.roles:
            await member.remove_roles(role)
            await interaction.response.send_message(
                f"✅ 已移除 {self.lang_data['emoji']} {self.lang_name} 角色",
                ephemeral=True
            )
        else:
            await member.add_roles(role)
            await interaction.response.send_message(
                f"✅ 已加入 {self.lang_data['emoji']} {self.lang_name} 頻道！",
                ephemeral=True
            )

# 執行機器人
if __name__ == "__main__":
    # 請在此輸入你的 Discord Bot Token
    TOKEN = "YOUR_BOT_TOKEN_HERE"

    if TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("⚠️ 請先在程式碼中設定你的 Discord Bot Token")
        print("1. 前往 https://discord.com/developers/applications")
        print("2. 建立應用程式並建立 Bot")
        print("3. 複製 Token 並貼到程式碼中")
    else:
        bot = LanguageBot()
        bot.run(TOKEN)