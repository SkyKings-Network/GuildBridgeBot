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
            await ctx.send(f"```json\n{formatted_config}\n```")
        else:
            await ctx.send("Failed to read configuration.")

    @commands.command(name="updateconfig")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(5, 60, commands.BucketType.user)
    async def update_config(self, ctx, key: str, value: str):
        """Queue a configuration update"""
        config = config_utils.read_config()
        if not config:
            await ctx.send("Failed to read configuration.")
            return

        keys = key.split('.')
        current = config
        for k in keys[:-1]:
            if k not in current:
                await ctx.send(f"Invalid key: {key}")
                return
            current = current[k]

        if keys[-1] not in current:
            await ctx.send(f"Invalid key: {key}")
            return

        # Validate the input using the appropriate validation function
        validator = getattr(config_utils, f"is_valid_{keys[-1]}", None)
        if validator and not validator(value):
            await ctx.send(f"Invalid value for {key}. Please check the format and try again.")
            return

        old_value = current[keys[-1]]
        self.pending_changes.setdefault(ctx.author.id, {})[key] = (old_value, value)

        sensitive_keys = ['token', 'webhookURL', 'officerWebhookURL', 'debugWebhookURL', 'ownerId']
        if any(sensitive_key in key for sensitive_key in sensitive_keys):
            await ctx.send(f"⚠️ Warning: You are modifying a sensitive setting ({key}). Please be cautious.")

        await ctx.send(f"Change queued: {key} = {value}")
        await ctx.send("Use `!saveconfig` when you're ready to apply and save all queued changes.")

    @commands.command(name="saveconfig")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def save_config(self, ctx):
        """Apply and save all queued configuration changes"""
        if ctx.author.id not in self.pending_changes or not self.pending_changes[ctx.author.id]:
            await ctx.send("No pending changes to save.")
            return

        changes = self.pending_changes[ctx.author.id]
        formatted_changes = "\n".join([f"{k}: {v[0]} -> {v[1]}" for k, v in changes.items()])
        await ctx.send(f"Pending changes:\n```\n{formatted_changes}\n```")

        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        self.otp_cache[ctx.author.id] = otp

        try:
            await ctx.author.send(f"Your OTP for confirming configuration changes is: {otp}")
            await ctx.send("An OTP has been sent to your DMs. Please enter it here to confirm the changes.")
        except discord.Forbidden:
            await ctx.send("Failed to send OTP via DM. Please enable DMs from server members and try again.")
            return

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=60.0)
        except asyncio.TimeoutError:
            await ctx.send("OTP confirmation timed out. Changes not saved.")
            return

        if msg.content != otp:
            await ctx.send("Invalid OTP. Changes not saved.")
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
        await ctx.send("Configuration updated and saved successfully.")
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
            await ctx.send("All pending changes have been cancelled.")
        else:
            await ctx.send("No pending changes to cancel.")

    @commands.command(name="showchanges")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(5, 60, commands.BucketType.user)
    async def show_changes(self, ctx):
        """Show all queued configuration changes"""
        if ctx.author.id in self.pending_changes and self.pending_changes[ctx.author.id]:
            changes = self.pending_changes[ctx.author.id]
            formatted_changes = "\n".join([f"{k}: {v[0]} -> {v[1]}" for k, v in changes.items()])
            await ctx.send(f"Pending changes:\n```\n{formatted_changes}\n```")
        else:
            await ctx.send("No pending changes.")

    @commands.command(name="backupconfig")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 300, commands.BucketType.guild)
    async def backup_config(self, ctx):
        """Create a backup of the current configuration"""
        backup_name = config_utils.backup_config()
        await ctx.send(f"Configuration backup created: {backup_name}")
        await self.cleanup_old_backups()

    @commands.command(name="restoreconfig")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 300, commands.BucketType.guild)
    async def restore_config(self, ctx):
        """Restore configuration from a backup"""
        backups = [f for f in os.listdir() if f.startswith("config_backup_") and f.endswith(".json")]
        if not backups:
            await ctx.send("No backup files found.")
            return

        backup_list = "\n".join([f"{i+1}. {backup}" for i, backup in enumerate(backups)])
        await ctx.send(f"Available backups:\n```\n{backup_list}\n```\nEnter the number of the backup to restore:")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            choice = int(msg.content) - 1
            if 0 <= choice < len(backups):
                restored_config = config_utils.restore_config(backups[choice])
                if restored_config:
                    config_utils.write_config(restored_config)
                    await ctx.send(f"Configuration restored from {backups[choice]}.")
                else:
                    await ctx.send("Failed to restore configuration.")
            else:
                await ctx.send("Invalid choice.")
        except asyncio.TimeoutError:
            await ctx.send("Restore operation timed out.")
        except ValueError:
            await ctx.send("Invalid input.")

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
                await ctx.send("Configuration is valid.")
            else:
                invalid_fields = [f for f, valid in validation_results.items() if not valid]
                await ctx.send(f"Configuration is invalid. Please check the following fields: {', '.join(invalid_fields)}")
        else:
            await ctx.send("Failed to read configuration.")

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