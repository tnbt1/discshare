import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import logging
from config import Config
from messages import get_message

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
    
    @app_commands.command(name='upload', description='Generate file upload URL')
    async def upload(self, interaction: discord.Interaction):
        if not any(role.name == Config.REQUIRED_ROLE for role in interaction.user.roles):
            await interaction.response.send_message(
                get_message('discord.error.no_permission'),
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
                            title=get_message('discord.upload.title'),
                            color=discord.Color.green(),
                            description=f"[{get_message('discord.upload.click_here')}]({upload_url})"
                        )
                        embed.add_field(
                            name=get_message('discord.upload.url_label'),
                            value=f"`{upload_url}`",
                            inline=False
                        )
                        embed.add_field(
                            name=get_message('discord.upload.expiry'),
                            value=get_message('discord.upload.expiry_days', days=Config.URL_EXPIRY_DAYS),
                            inline=True
                        )
                        embed.add_field(
                            name=get_message('discord.upload.max_size'),
                            value="5GB",
                            inline=True
                        )
                        embed.add_field(
                            name=get_message('discord.upload.supported_files'),
                            value=get_message('discord.upload.supported_formats'),
                            inline=False
                        )
                        embed.set_footer(text=get_message('discord.upload.footer'))

                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send(get_message('discord.error.generation_failed'))
                        
        except Exception as e:
            logger.error(f"Error generating URL: {e}")
            await interaction.followup.send(get_message('discord.error.service_unavailable'))
    
    @app_commands.command(name='generate', description='Alias for /upload command')
    async def generate(self, interaction: discord.Interaction):
        if not any(role.name == Config.REQUIRED_ROLE for role in interaction.user.roles):
            await interaction.response.send_message(
                get_message('discord.error.no_permission'),
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
                            title=get_message('discord.upload.title'),
                            color=discord.Color.green(),
                            description=f"[{get_message('discord.upload.click_here')}]({upload_url})"
                        )
                        embed.add_field(
                            name=get_message('discord.upload.url_label'),
                            value=f"`{upload_url}`",
                            inline=False
                        )
                        embed.add_field(
                            name=get_message('discord.upload.expiry'),
                            value=get_message('discord.upload.expiry_days', days=Config.URL_EXPIRY_DAYS),
                            inline=True
                        )
                        embed.add_field(
                            name=get_message('discord.upload.max_size'),
                            value="5GB",
                            inline=True
                        )
                        embed.add_field(
                            name=get_message('discord.upload.supported_files'),
                            value=get_message('discord.upload.supported_formats'),
                            inline=False
                        )
                        embed.set_footer(text=get_message('discord.upload.footer'))

                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send(get_message('discord.error.generation_failed'))
                        
        except Exception as e:
            logger.error(f"Error generating URL: {e}")
            await interaction.followup.send(get_message('discord.error.service_unavailable'))
    
    @app_commands.command(name='help', description='Show file sharing service guide')
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=get_message('discord.help.title'),
            color=discord.Color.blue()
        )
        embed.add_field(
            name=get_message('discord.help.upload_command'),
            value=get_message('discord.help.upload_desc'),
            inline=False
        )
        embed.add_field(
            name=get_message('discord.help.required_role'),
            value=f"`{Config.REQUIRED_ROLE}` role",
            inline=False
        )
        embed.add_field(
            name=get_message('discord.upload.supported_files'),
            value=get_message('discord.upload.supported_formats'),
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