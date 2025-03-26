import discord
from discord.ext import commands
from core.config import DiscordConfig

HELP_EMBED = discord.Embed(
    title="Bridge Bot | Help Commands",
    description="``< >`` = Required arguments\n``[ ]`` = Optional arguments",
    colour=0x1ABC9C
)
HELP_EMBED.add_field(
    name="Command Prefix",
    value=f"Prefix: ``{DiscordConfig.prefix}``"
)
HELP_EMBED.add_field(
    name="Discord Commands",
    value=f"``{DiscordConfig.prefix}invite <username>`` Invites the user to the guild\n"
            f"``{DiscordConfig.prefix}promote <username>`` Promotes the given user\n"
            f"``{DiscordConfig.prefix}demote <username>`` Demotes the given user\n"
            f"``{DiscordConfig.prefix}setrank <username> <rank>`` Sets the given user to a specific rank\n"
            f"``{DiscordConfig.prefix}kick <username> [reason]`` Kicks the given user\n"
            f"``{DiscordConfig.prefix}notifications`` Toggles join / leave notifications\n"
            f"``{DiscordConfig.prefix}online`` Shows the online members\n"
            f"``{DiscordConfig.prefix}list`` Shows the list of members\n"
            f"``{DiscordConfig.prefix}top`` Shows experience ranking of members for the day\n"
            f"``{DiscordConfig.prefix}info``Shows guild information\n"
            f"``{DiscordConfig.prefix}override <command>`` Forces the bot to use a given command\n"
            f"``{DiscordConfig.prefix}toggleaccept`` Toggles auto accepting members joining the guild\n"
            f"``{DiscordConfig.prefix}mute <username> <time>`` Mutes the user for a specific time\n"
            f"``{DiscordConfig.prefix}unmute <username>`` Unmutes the user\n"
            f"``{DiscordConfig.prefix}log [params]`` Shows guild audit logs",
    inline=False
)
HELP_EMBED.add_field(
    name="Info",
    value="Guild Channel: " + (f"<#{DiscordConfig.channel}>" if DiscordConfig.channel else "❌") + "\n" + 
            "Officer Channel: " + (f"<#{DiscordConfig.officerChannel}>" if DiscordConfig.officerChannel else "❌") + "\n" + 
            "Command Role: " + (f"<@&{DiscordConfig.commandRole}>" if DiscordConfig.commandRole else "❌") + "\n" + 
            "Override Role: " + (f"<@&{DiscordConfig.overrideRole}>" if DiscordConfig.overrideRole else "❌") + "\n",
    inline=False
)
HELP_EMBED.set_footer(text=f"Made by SkyKings")

class Generic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def help(self, ctx):
        HELP_EMBED.timestamp = ctx.message.created_at
        await ctx.send(embed=HELP_EMBED)


async def setup(bot):
    await bot.add_cog(Generic(bot))
