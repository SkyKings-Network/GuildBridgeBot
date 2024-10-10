import discord
from discord.ext import commands
from utils import config_utils
import json
import random
import asyncio
import os
from datetime import datetime, timedelta
import logging

class ConfigManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pending_changes = {}
        self.otp_cache = {}
        self.setup_logging()

    def setup_logging(self):
        self.logger = logging.getLogger('ConfigManagement')
        self.logger.setLevel(logging.INFO)
        handler = logging.FileHandler('config_changes.log')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    @commands.command(name="showconfig")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def show_config(self, ctx):
        """Display the current configuration"""
        config = config_utils.read_config()
        if config:
            redacted_config = self.redact_sensitive_info(config)
            formatted_config = json.dumps(redacted_config, indent=2)
            embed = discord.Embed(title="Current Configuration", description="```json\n" + formatted_config + "\n```", color=discord.Color.blue())
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="Error", description="Failed to read configuration.", color=discord.Color.red())
            await ctx.send(embed=embed)

    @commands.command(name="updateconfig")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(5, 60, commands.BucketType.user)
    async def update_config(self, ctx, key: str, value: str):
        """Queue a configuration update"""
        config = config_utils.read_config()
        if not config:
            embed = discord.Embed(title="Error", description="Failed to read configuration.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return

        keys = key.split('.')
        current = config
        for k in keys[:-1]:
            if k not in current:
                embed = discord.Embed(title="Error", description=f"Invalid key: {key}", color=discord.Color.red())
                await ctx.send(embed=embed)
                return
            current = current[k]

        if keys[-1] not in current:
            embed = discord.Embed(title="Error", description=f"Invalid key: {key}", color=discord.Color.red())
            await ctx.send(embed=embed)
            return

        # Validate the input using the appropriate validation function
        validator = getattr(config_utils, f"is_valid_{keys[-1]}", None)
        if validator and not validator(value):
            embed = discord.Embed(title="Error", description=f"Invalid value for {key}. Please check the format and try again.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return

        old_value = current[keys[-1]]
        self.pending_changes.setdefault(ctx.author.id, {})[key] = (old_value, value)

        embed = discord.Embed(title="Configuration Update Queued", color=discord.Color.green())
        embed.add_field(name="Key", value=key, inline=True)
        embed.add_field(name="New Value", value=value, inline=True)

        sensitive_keys = ['token', 'webhookURL', 'officerWebhookURL', 'debugWebhookURL', 'ownerId']
        if any(sensitive_key in key for sensitive_key in sensitive_keys):
            embed.add_field(name="Warning", value="⚠️ You are modifying a sensitive setting. Please be cautious.", inline=False)

        embed.set_footer(text="Use !saveconfig when you're ready to apply and save all queued changes.")
        await ctx.send(embed=embed)

    @commands.command(name="saveconfig")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def save_config(self, ctx):
        """Apply and save all queued configuration changes"""
        if ctx.author.id not in self.pending_changes or not self.pending_changes[ctx.author.id]:
            embed = discord.Embed(title="No Changes", description="No pending changes to save.", color=discord.Color.blue())
            await ctx.send(embed=embed)
            return

        changes = self.pending_changes[ctx.author.id]
        formatted_changes = "\n".join([f"{k}: {v[0]} -> {v[1]}" for k, v in changes.items()])
        
        embed = discord.Embed(title="Pending Changes", description=f"```\n{formatted_changes}\n```", color=discord.Color.gold())
        await ctx.send(embed=embed)

        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        self.otp_cache[ctx.author.id] = otp

        try:
            await ctx.author.send(f"Your OTP for confirming configuration changes is: **{otp}**")
            embed = discord.Embed(title="OTP Sent", description="An OTP has been sent to your DMs. Please enter it here to confirm the changes.", color=discord.Color.blue())
            await ctx.send(embed=embed)
        except discord.Forbidden:
            embed = discord.Embed(title="Error", description="Failed to send OTP via DM. Please enable DMs from server members and try again.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=60.0)
        except asyncio.TimeoutError:
            embed = discord.Embed(title="Timeout", description="OTP confirmation timed out. Changes not saved.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return

        if msg.content != otp:
            embed = discord.Embed(title="Invalid OTP", description="Invalid OTP. Changes not saved.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return

        config = config_utils.read_config()
        for key, (old_value, new_value) in changes.items():
            keys = key.split('.')
            current = config
            for k in keys[:-1]:
                current = current[k]
            current[keys[-1]] = new_value

        # Migrate config if necessary
        config = config_utils.migrate_config(config)

        config_utils.write_config(config)
        embed = discord.Embed(title="Configuration Updated", description="Configuration updated and saved successfully.", color=discord.Color.green())
        await ctx.send(embed=embed)
        self.log_changes(ctx.author, changes)
        self.pending_changes[ctx.author.id] = {}

    def log_changes(self, author, changes):
        for key, (old_value, new_value) in changes.items():
            self.logger.info(f"Config change by {author.name}#{author.discriminator} ({author.id}): {key} changed from {old_value} to {new_value}")

    @commands.command(name="cancelchanges")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(5, 60, commands.BucketType.user)
    async def cancel_changes(self, ctx):
        """Cancel all queued configuration changes"""
        if ctx.author.id in self.pending_changes:
            self.pending_changes[ctx.author.id] = {}
            embed = discord.Embed(title="Changes Cancelled", description="All pending changes have been cancelled.", color=discord.Color.green())
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="No Changes", description="No pending changes to cancel.", color=discord.Color.blue())
            await ctx.send(embed=embed)

    @commands.command(name="showchanges")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(5, 60, commands.BucketType.user)
    async def show_changes(self, ctx):
        """Show all queued configuration changes"""
        if ctx.author.id in self.pending_changes and self.pending_changes[ctx.author.id]:
            changes = self.pending_changes[ctx.author.id]
            formatted_changes = "\n".join([f"{k}: {v[0]} -> {v[1]}" for k, v in changes.items()])
            embed = discord.Embed(title="Pending Changes", description=f"```\n{formatted_changes}\n```", color=discord.Color.gold())
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="No Changes", description="No pending changes.", color=discord.Color.blue())
            await ctx.send(embed=embed)

    @commands.command(name="backupconfig")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 300, commands.BucketType.guild)
    async def backup_config(self, ctx):
        """Create a backup of the current configuration"""
        backup_name = config_utils.backup_config()
        embed = discord.Embed(title="Backup Created", description=f"Configuration backup created: {backup_name}", color=discord.Color.green())
        await ctx.send(embed=embed)
        await self.cleanup_old_backups()

    @commands.command(name="restoreconfig")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 300, commands.BucketType.guild)
    async def restore_config(self, ctx):
        """Restore configuration from a backup"""
        backups = [f for f in os.listdir() if f.startswith("config_backup_") and f.endswith(".json")]
        if not backups:
            embed = discord.Embed(title="No Backups", description="No backup files found.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return

        backup_list = "\n".join([f"{i+1}. {backup}" for i, backup in enumerate(backups)])
        embed = discord.Embed(title="Available Backups", description=f"```\n{backup_list}\n```\nEnter the number of the backup to restore:", color=discord.Color.blue())
        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            choice = int(msg.content) - 1
            if 0 <= choice < len(backups):
                restored_config = config_utils.restore_config(choice)
                if restored_config:
                    config_utils.write_config(restored_config)
                    embed = discord.Embed(title="Config Restored", description=f"Configuration restored from {backups[choice]}.", color=discord.Color.green())
                    await ctx.send(embed=embed)
                else:
                    embed = discord.Embed(title="Restore Failed", description="Failed to restore configuration.", color=discord.Color.red())
                    await ctx.send(embed=embed)
            else:
                embed = discord.Embed(title="Invalid Choice", description="Invalid choice.", color=discord.Color.red())
                await ctx.send(embed=embed)
        except asyncio.TimeoutError:
            embed = discord.Embed(title="Timeout", description="Restore operation timed out.", color=discord.Color.red())
            await ctx.send(embed=embed)
        except ValueError:
            embed = discord.Embed(title="Invalid Input", description="Invalid input.", color=discord.Color.red())
            await ctx.send(embed=embed)

    async def cleanup_old_backups(self):
        """Delete backups older than 30 days"""
        cutoff_date = datetime.now() - timedelta(days=30)
        for filename in os.listdir():
            if filename.startswith("config_backup_") and filename.endswith(".json"):
                file_date_str = filename[14:28]  # Extract date from filename
                file_date = datetime.strptime(file_date_str, "%Y%m%d_%H%M%S")
                if file_date < cutoff_date:
                    os.remove(filename)
                    self.logger.info(f"Deleted old backup: {filename}")

    @commands.command(name="validateconfig")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def validate_config(self, ctx):
        """Validate the current configuration"""
        config = config_utils.read_config()
        if config:
            validation_results = self.validate_config_details(config)
            if all(validation_results.values()):
                embed = discord.Embed(title="Config Validation", description="Configuration is valid.", color=discord.Color.green())
            else:
                invalid_fields = [f for f, valid in validation_results.items() if not valid]
                embed = discord.Embed(title="Config Validation", description=f"Configuration is invalid. Please check the following fields: {', '.join(invalid_fields)}", color=discord.Color.red())
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="Error", description="Failed to read configuration.", color=discord.Color.red())
            await ctx.send(embed=embed)

    def validate_config_details(self, config):
        validation_results = {}
        validation_results['email'] = config_utils.is_valid_email(config['account']['email'])
        validation_results['discord_id'] = config_utils.is_valid_discord_id(config['discord']['ownerId'])
        validation_results['webhook_url'] = config_utils.is_valid_url(config['discord']['webhookURL'])
        validation_results['officer_webhook_url'] = config_utils.is_valid_url(config['discord']['officerWebhookURL'])
        validation_results['debug_webhook_url'] = config_utils.is_valid_url(config['discord']['debugWebhookURL'])
        validation_results['prefix'] = config_utils.is_valid_prefix(config['discord']['prefix'])
        validation_results['command_role'] = config_utils.is_valid_role_name(config['discord']['commandRole'])
        validation_results['override_role'] = config_utils.is_valid_role_name(config['discord']['overrideRole'])
        return validation_results

    def redact_sensitive_info(self, config):
        redacted_config = json.loads(json.dumps(config))
        sensitive_keys = ['token', 'webhookURL', 'officerWebhookURL', 'debugWebhookURL']
        for key in sensitive_keys:
            if key in redacted_config['discord']:
                redacted_config['discord'][key] = '[REDACTED]'
        return redacted_config

async def setup(bot):
    await bot.add_cog(ConfigManagement(bot))