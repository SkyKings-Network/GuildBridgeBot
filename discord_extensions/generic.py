import discord
from discord.ext import commands
from core.config import DiscordConfig


class Generic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def help(self, ctx):
        embed = discord.Embed(
            title="Bridge Bot | Help Commands",
            description="``< >`` = Required arguments\n``[ ]`` = Optional arguments",
            colour=0x1ABC9C, timestamp=ctx.message.created_at
        )
        
        # Command Prefix Section
        embed.add_field(
            name="Command Prefix",
            value=f"Prefix: ``{DiscordConfig.prefix}``",
            inline=False
        )

        # General Commands Section
        embed.add_field(
            name="General Commands",
            value=f"``{DiscordConfig.prefix}notifications``: Toggles join/leave notifications\n"
                f"``{DiscordConfig.prefix}online``: Shows the online members\n"
                f"``{DiscordConfig.prefix}list``: Shows the list of members\n"
                f"``{DiscordConfig.prefix}top``: Shows experience ranking of members for the day\n"
                f"``{DiscordConfig.prefix}info``: Shows Guild Information",
            inline=False
        )

        # Moderation Commands Section
        embed.add_field(
            name="Moderation Commands",
            value=f"``{DiscordConfig.prefix}kick <username> [reason]``: Kicks the given user\n"
                f"``{DiscordConfig.prefix}mute <username> <time>``: Mutes the user for a specific time\n"
                f"``{DiscordConfig.prefix}unmute <username>``: Unmutes the user",
            inline=False
        )
        
        # Guild Management Commands Section
        embed.add_field(
            name="Guild Management Commands",
            value=f"``{DiscordConfig.prefix}invite <username>``: Invites the user to the guild\n"
                f"``{DiscordConfig.prefix}promote <username>``: Promotes the given user\n"
                f"``{DiscordConfig.prefix}demote <username>``: Demotes the given user\n"
                f"``{DiscordConfig.prefix}setrank <username> <rank>``: Sets the given user to a specific rank\n"
                f"``{DiscordConfig.prefix}override <command>``: Forces the bot to use a given command\n"
                f"``{DiscordConfig.prefix}toggleaccept``: Toggles auto accepting members joining the guild",
            inline=False
        )

        # Configuration Commands Section
        embed.add_field(
            name="Configuration Commands",
            value=f"``{DiscordConfig.prefix}showconfig``: Displays the current configuration\n"
                f"``{DiscordConfig.prefix}updateconfig <key> <value>``: Queues a configuration update\n"
                f"``{DiscordConfig.prefix}saveconfig``: Applies and saves queued configuration changes\n"
                f"``{DiscordConfig.prefix}cancelchanges``: Cancels all queued configuration changes\n"
                f"``{DiscordConfig.prefix}showchanges``: Shows all queued configuration changes\n"
                f"``{DiscordConfig.prefix}backupconfig``: Creates a backup of the current configuration\n"
                f"``{DiscordConfig.prefix}restoreconfig``: Restores configuration from a backup\n"
                f"``{DiscordConfig.prefix}validateconfig``: Validates the current configuration",
            inline=False
        )

        # Information Section
        embed.add_field(
            name="Info",
            value=f"Guild Channel: <#{DiscordConfig.channel}>\n"
                f"Officer Channel: <#{DiscordConfig.officerChannel}>\n"
                f"Command Role: <@&{DiscordConfig.commandRole}>\n"
                f"Override Role: <@&{DiscordConfig.overrideRole}>\n"
                f"Server Name: {DiscordConfig.serverName}\n",
            inline=False
        )

        # Footer
        embed.set_footer(text="Made by SkyKings Development Team")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Generic(bot))
