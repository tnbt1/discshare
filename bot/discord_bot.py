import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import logging
from config import Config

logger = logging.getLogger(__name__)

class FileShareBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='/', intents=intents)
        self.api_base = f"http://localhost:{Config.API_PORT}"
    
    async def setup_hook(self):
        await self.tree.sync()
        logger.info("Slash commands synced globally")
    
    async def on_ready(self):
        logger.info(f"Bot logged in as {self.user}")
        logger.info(f"Connected to {len(self.guilds)} servers")
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} slash command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")

class FileCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name='upload', description='ファイルアップロード用のURLを生成します')
    async def upload(self, interaction: discord.Interaction):
        if not any(role.name == Config.REQUIRED_ROLE for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ このコマンドを実行する権限がありません",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            async with aiohttp.ClientSession() as session:
                data = {
                    "discord_server_id": str(interaction.guild.id),
                    "discord_user_id": str(interaction.user.id),
                    "discord_username": str(interaction.user)
                }
                
                async with session.post(
                    f"{self.bot.api_base}/api/create_session",
                    json=data
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        upload_url = f"{Config.SERVICE_URL}/upload/{result['token']}"
                        
                        embed = discord.Embed(
                            title="📁 アップロードURL生成完了",
                            color=discord.Color.green(),
                            description=f"[**ここをクリックしてアップロード**]({upload_url})"
                        )
                        embed.add_field(
                            name="🔗 URL（コピー用）",
                            value=f"`{upload_url}`",
                            inline=False
                        )
                        embed.add_field(
                            name="⏰ 有効期限",
                            value=f"{Config.URL_EXPIRY_DAYS}日間",
                            inline=True
                        )
                        embed.add_field(
                            name="📦 最大サイズ",
                            value="5GB",
                            inline=True
                        )
                        embed.add_field(
                            name="対応ファイル",
                            value="PDF, DOCX, XLSX, ZIP, JPG, PNG, MP4, AVI, MOV, MKV, WEBM, TXT, CSV, JSON, XML",
                            inline=False
                        )
                        embed.set_footer(text="URLは有効期限まで何度でも使用可能です")
                        
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send("❌ URL生成に失敗しました")
                        
        except Exception as e:
            logger.error(f"Error generating URL: {e}")
            await interaction.followup.send("❌ サービスに接続できません")
    
    @app_commands.command(name='generate', description='uploadコマンドと同じ（エイリアス）')
    async def generate(self, interaction: discord.Interaction):
        if not any(role.name == Config.REQUIRED_ROLE for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ このコマンドを実行する権限がありません",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            async with aiohttp.ClientSession() as session:
                data = {
                    "discord_server_id": str(interaction.guild.id),
                    "discord_user_id": str(interaction.user.id),
                    "discord_username": str(interaction.user)
                }
                
                async with session.post(
                    f"{self.bot.api_base}/api/create_session",
                    json=data
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        upload_url = f"{Config.SERVICE_URL}/upload/{result['token']}"
                        
                        embed = discord.Embed(
                            title="📁 アップロードURL生成完了",
                            color=discord.Color.green(),
                            description=f"[**ここをクリックしてアップロード**]({upload_url})"
                        )
                        embed.add_field(
                            name="🔗 URL（コピー用）",
                            value=f"`{upload_url}`",
                            inline=False
                        )
                        embed.add_field(
                            name="⏰ 有効期限",
                            value=f"{Config.URL_EXPIRY_DAYS}日間",
                            inline=True
                        )
                        embed.add_field(
                            name="📦 最大サイズ",
                            value="5GB",
                            inline=True
                        )
                        embed.add_field(
                            name="対応ファイル",
                            value="PDF, DOCX, XLSX, ZIP, JPG, PNG, MP4, AVI, MOV, MKV, WEBM, TXT, CSV, JSON, XML",
                            inline=False
                        )
                        embed.set_footer(text="URLは有効期限まで何度でも使用可能です")
                        
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send("❌ URL生成に失敗しました")
                        
        except Exception as e:
            logger.error(f"Error generating URL: {e}")
            await interaction.followup.send("❌ サービスに接続できません")
    
    @app_commands.command(name='help', description='ファイル共有サービスの使い方を表示')
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📖 ファイル共有サービスの使い方",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="/upload",
            value="アップロード用URLを生成します",
            inline=False
        )
        embed.add_field(
            name="必要な権限",
            value=f"`{Config.REQUIRED_ROLE}` ロール",
            inline=False
        )
        embed.add_field(
            name="対応ファイル",
            value="PDF, DOCX, XLSX, ZIP, JPG, PNG, MP4, AVI, MOV, MKV, WEBM, TXT, CSV, JSON, XML",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def run_bot():
    bot = FileShareBot()
    await bot.add_cog(FileCommands(bot))
    
    try:
        await bot.start(Config.DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Bot failed to start: {e}")
        raise