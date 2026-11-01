import discord
from discord.ext import commands
import asyncio
import json
import os
from datetime import datetime

# 設定檔管理
class Config:
    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        else:
            self.data = {
                'prefix': '!',
                'forum_category_id': None,
                'allowed_roles': [],
                'moderation_role': None
            }
            self.save_config()

    def save_config(self):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

# 機器人類別
class ForumBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.guild_messages = True

        super().__init__(
            command_prefix=self.get_prefix,
            intents=intents,
            help_command=None
        )

        self.config = Config()
        self.setup_commands()

    async def get_prefix(self, message):
        return self.config.data.get('prefix', '!')

    def setup_commands(self):
        # 基本命令
        @self.command(name='setup_forum')
        @commands.has_permissions(administrator=True)
        async def setup_forum(ctx, category_name: str = "論壇"):
            """設定論壇分類 (管理員專用)"""
            try:
                # 檢查是否已有論壇分類
                existing_category = discord.utils.get(ctx.guild.categories, name=category_name)
                if existing_category:
                    await ctx.send(f"✅ 已找到現有的「{category_name}」分類")
                    self.config.data['forum_category_id'] = existing_category.id
                else:
                    # 創建新的分類
                    overwrites = {
                        ctx.guild.default_role: discord.PermissionOverwrite(
                            send_messages=True,
                            read_messages=True,
                            create_public_threads=True,
                            create_private_threads=False
                        )
                    }
                    category = await ctx.guild.create_category(category_name, overwrites=overwrites)
                    self.config.data['forum_category_id'] = category.id
                    await ctx.send(f"✅ 已創建「{category_name}」分類")

                # 設定管理員權限
                admin_role = ctx.guild.default_role
                category = ctx.guild.get_channel(self.config.data['forum_category_id'])
                await category.set_permissions(ctx.guild.default_role,
                                               create_public_threads=True,
                                               create_private_threads=False,
                                               send_messages=True)

                self.config.save_config()

                # 創建論壇頻道範例
                await self.create_forum_channels(ctx.guild)

            except Exception as e:
                await ctx.send(f"❌ 設定失敗: {str(e)}")

        @self.command(name='create_topic')
        async def create_topic(ctx, *, title: str):
            """創建新的論壇主題"""
            try:
                # 檢查使用者權限
                if not self.check_user_permission(ctx.author):
                    await ctx.send("❌ 你沒有權限創建論壇主題")
                    return

                # 獲取論壇分類
                category = ctx.guild.get_channel(self.config.data.get('forum_category_id'))
                if not category:
                    await ctx.send("❌ 找不到論壇分類，請先執行 !setup_forum")
                    return

                # 尋找可用的論壇頻道
                forum_channel = None
                for channel in category.channels:
                    if isinstance(channel, discord.TextChannel) and channel.name.startswith('topic-'):
                        forum_channel = channel
                        break

                if not forum_channel:
                    await ctx.send("❌ 找不到論壇頻道，請先執行 !setup_forum")
                    return

                # 創建主題討論串
                thread = await forum_channel.create_thread(
                    name=title,
                    message=None,
                    auto_archive_duration=1440,  # 24小時
                    reason=f"由 {ctx.author.name} 創建"
                )

                # 發送歡迎訊息
                welcome_msg = f"""
# 📋 主題：{title}

**創建者：** {ctx.author.mention}
**創建時間：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📌 主題說明
請在此討論與主題相關的內容。

## 📝 規則
1. 請保持討論內容與主題相關
2. 尊重他人意見
3. 禁止人身攻擊或不當言論

---
💡 使用 `!close_topic` 來關閉此主題（僅限創建者或管理員）
"""
                await thread.send(welcome_msg)

                # 將創建者加入討論串
                await thread.add_user(ctx.author)

                await ctx.send(f"✅ 已創建主題：{title}，請前往 {thread.mention} 查看")

            except Exception as e:
                await ctx.send(f"❌ 創建主題失敗: {str(e)}")

        @self.command(name='close_topic')
        async def close_topic(ctx):
            """關閉當前論壇主題"""
            try:
                thread = ctx.channel

                # 檢查是否為討論串
                if not isinstance(thread, discord.Thread):
                    await ctx.send("❌ 此命令只能在論壇討論串中使用")
                    return

                # 檢查權限
                if not await self.check_close_permission(ctx):
                    return

                # 發送關閉訊息
                await thread.send(f"🔒 此主題將在 5 秒後關閉，由 {ctx.author.mention} 發起")
                await asyncio.sleep(5)

                # 鎖定討論串
                await thread.edit(
                    locked=True,
                    archived=True,
                    reason=f"由 {ctx.author.name} 關閉"
                )

                await ctx.send("✅ 主題已關閉")

            except Exception as e:
                await ctx.send(f"❌ 關閉主題失敗: {str(e)}")

        @self.command(name='list_topics')
        async def list_topics(ctx):
            """列出所有活躍的論壇主題"""
            try:
                category = ctx.guild.get_channel(self.config.data.get('forum_category_id'))
                if not category:
                    await ctx.send("❌ 找不到論壇分類")
                    return

                topics = []
                for channel in category.channels:
                    if isinstance(channel, discord.TextChannel):
                        for thread in channel.threads:
                            if not thread.archived:
                                topics.append(f"📌 {thread.name} - {thread.mention}")

                if not topics:
                    await ctx.send("📭 目前沒有活躍的主題")
                    return

                embed = discord.Embed(
                    title="📋 活躍論壇主題",
                    description="\n".join(topics),
                    color=discord.Color.blue()
                )
                embed.set_footer(text=f"共 {len(topics)} 個主題")
                await ctx.send(embed=embed)

            except Exception as e:
                await ctx.send(f"❌ 獲取主題列表失敗: {str(e)}")

        # 錯誤處理
        @self.event
        async def on_command_error(ctx, error):
            if isinstance(error, commands.MissingPermissions):
                await ctx.send("❌ 你沒有權限執行此命令")
            elif isinstance(error, commands.MissingRequiredArgument):
                await ctx.send(f"❌ 缺少必要參數: {error.param}")
            else:
                await ctx.send(f"❌ 發生錯誤: {str(error)}")

    async def create_forum_channels(self, guild):
        """創建範例論壇頻道"""
        category = guild.get_channel(self.config.data['forum_category_id'])
        if not category:
            return

        # 創建主要論壇頻道
        main_channel = discord.utils.get(category.channels, name="topic-主要討論")
        if not main_channel:
            await guild.create_text_channel(
                "topic-主要討論",
                category=category,
                topic="主要論壇討論區 - 使用 !create_topic 創建主題"
            )

        # 創建其他範例頻道
        channels = ["topic-公告", "topic-建議", "topic-問答"]
        for channel_name in channels:
            existing = discord.utils.get(category.channels, name=channel_name)
            if not existing:
                await guild.create_text_channel(
                    channel_name,
                    category=category,
                    topic=f"{channel_name} - 使用 !create_topic 創建主題"
                )

    def check_user_permission(self, user):
        """檢查用戶是否有權限創建主題"""
        allowed_roles = self.config.data.get('allowed_roles', [])
        if not allowed_roles:
            return True  # 如果沒有設定限制，所有人都可以創建

        for role in user.roles:
            if role.id in allowed_roles:
                return True
        return False

    async def check_close_permission(self, ctx):
        """檢查關閉權限"""
        thread = ctx.channel

        # 管理員可以關閉任何主題
        if ctx.author.guild_permissions.administrator:
            return True

        # 創建者可以關閉
        thread_members = await thread.fetch_members()
        starter = thread.owner_id if hasattr(thread, 'owner_id') else None
        if ctx.author.id == starter:
            return True

        # 檢查是否有管理角色
        moderation_role = self.config.data.get('moderation_role')
        if moderation_role:
            role = discord.utils.get(ctx.guild.roles, id=moderation_role)
            if role and role in ctx.author.roles:
                return True

        await ctx.send("❌ 只有管理員、創建者或指定管理角色才能關閉主題")
        return False

    async def on_ready(self):
        print(f'✅ 機器人已登入為 {self.user.name}')
        print(f'✅ 已連線到 {len(self.guilds)} 個伺服器')
        print(f'✅ 前綴: {self.config.data.get("prefix", "!")}')
        print('=' * 50)

# 主程式
def main():
    # 從環境變數獲取 Token（建議）
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("請設定環境變數 DISCORD_BOT_TOKEN")
        print("或在程式碼中直接輸入 Token（不建議）")
        token = input("請輸入 Discord Bot Token: ")

    # 創建並執行機器人
    bot = ForumBot()

    try:
        bot.run(token)
    except discord.LoginFailure:
        print("❌ Token 無效，請檢查你的 Bot Token")
    except Exception as e:
        print(f"❌ 啟動失敗: {str(e)}")

if __name__ == "__main__":
    main()