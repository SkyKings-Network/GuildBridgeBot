import signal
import subprocess
import json
import os
import re
import shutil
from datetime import datetime
import time
import uuid
import getpass

from utils.config_utils import (is_valid_discord_id, is_valid_email, is_valid_port, 
                                is_valid_prefix, is_valid_role_name, is_valid_url,
                                validate_input, is_config_valid, read_config, write_config, 
                                backup_config, migrate_config, restore_config, default_config)

# ASCII art of SKYKINGS
ascii_art = r"""
 _______  _                 _       _________ _        _______  _______ 
(  ____ \| \    /\|\     /|| \    /\\__   __/( (    /|(  ____ \(  ____ \
| (    \/|  \  / /( \   / )|  \  / /   ) (   |  \  ( || (    \/| (    \/
| (_____ |  (_/ /  \ (_) / |  (_/ /    | |   |   \ | || |      | (_____ 
(_____  )|   _ (    \   /  |   _ (     | |   | (\ \) || | ____ (_____  )
      ) ||  ( \ \    ) (   |  ( \ \    | |   | | \   || | \_  )      ) |
/\____) ||  /  \ \   | |   |  /  \ \___) (___| )  \  || (___) |/\____) |
\_______)|_/    \/   \_/   |_/    \/\_______/|/    )_)(_______)\_______)
                                                                        
"""

welcome_message = f"""
╔════════════════════════════════════════════╗
  Welcome to the GuildBridgeBot Setup Wizard!
╚════════════════════════════════════════════╝

{ascii_art}

GuildBridgeBot seamlessly connects Hypixel Minecraft guilds with Discord, offering:
- Real-time message relay
- Event notifications (joins, leaves, promotions)
- Command handling via Discord
- Auto-accept guild invites
- Customizable bot messages

This setup will guide you through configuring your bot and installing dependencies. 
Let's get started!
"""

def install_modules():
    try:
        with open(os.devnull, 'w') as devnull:
            # Installing Python modules from requirements.txt
            print("\nInstalling required Python modules from requirements.txt...")
            subprocess.check_call(["pip", "install", "-r", "requirements.txt"], stdout=devnull, stderr=subprocess.STDOUT)
            print("Python modules installed.\n")

            # Installing discord.py
            print("Installing discord.py module...")
            subprocess.check_call(["pip", "install", "discord.py"], stdout=devnull, stderr=subprocess.STDOUT)
            print("discord.py installed.\n")

            # Installing mineflayer via npm
            print("Installing mineflayer via npm...")
            subprocess.check_call(["npm", "install", "mineflayer"], stdout=devnull, stderr=subprocess.STDOUT)
            print("mineflayer installed.\n")

        print("All required modules were installed successfully.")
    
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while installing modules: {e}")
        exit(1)

def get_user_input(config):
    print("\nPlease provide the following configuration details:\n")

    config['account']['email'] = validate_input(
        f"Enter your account email: ",
        is_valid_email,
        "Invalid email format. Please try again.",
        allow_empty=False
    ) or config['account']['email']

    config['discord']['token'] = getpass.getpass("Enter Discord bot token: ")
    while not (len(config['discord']['token']) > 50 and all(c.isalnum() or c in '.-_' for c in config['discord']['token'])):
        print("Invalid Discord bot token. It should be a long string of letters, numbers, and some special characters.")
        config['discord']['token'] = getpass.getpass("Enter Discord bot token: ")

    config['discord']['channel'] = validate_input(
        "Enter Discord channel ID: ",
        is_valid_discord_id,
        "Invalid Discord channel ID. It should be a 17-19 digit number."
    )

    config['discord']['officerChannel'] = validate_input(
        "Enter Officer Discord channel ID: ",
        is_valid_discord_id,
        "Invalid Discord channel ID. It should be a 17-19 digit number."
    )

    config['discord']['commandRole'] = validate_input(
        "Enter Discord command role: ",
        is_valid_role_name,
        "Invalid role name. It should be 1-100 printable characters."
    )

    config['discord']['overrideRole'] = validate_input(
        "Enter Discord override role: ",
        is_valid_role_name,
        "Invalid role name. It should be 1-100 printable characters."
    )

    config['discord']['ownerId'] = validate_input(
        "Enter Discord owner ID: ",
        is_valid_discord_id,
        "Invalid Discord owner ID. It should be a 17-19 digit number."
    )

    config['discord']['prefix'] = validate_input(
        f"Enter Discord command prefix (default: {config['discord']['prefix']}): ",
        is_valid_prefix,
        "Invalid prefix. It should be a single printable character.",
        allow_empty=True
    ) or config['discord']['prefix']

    config['discord']['webhookURL'] = validate_input(
        "Enter Discord webhook URL: ",
        is_valid_url,
        "Invalid webhook URL. It should be a valid Discord webhook URL."
    )

    config['discord']['officerWebhookURL'] = validate_input(
        "Enter Officer Discord webhook URL: ",
        is_valid_url,
        "Invalid webhook URL. It should be a valid Discord webhook URL."
    )

    config['discord']['serverName'] = input("Enter Discord server name: ")

    debug_mode = input("Do you want to enable debug mode? (yes/no, default: no): ").lower()
    if debug_mode == "yes":
        config['discord']['debugWebhookURL'] = validate_input(
            "Enter Debug Webhook URL: ",
            is_valid_url,
            "Invalid webhook URL. It should be a valid Discord webhook URL."
        )

    redis_integration = input("Do you want to enable Redis integration? (yes/no, default: no): ").lower()
    if redis_integration == "yes":
        config['redis']['enabled'] = True
        config['redis']['host'] = input(f"Enter Redis host (default: {config['redis']['host']}): ") or config['redis']['host']
        config['redis']['port'] = validate_input(
            f"Enter Redis port (default: {config['redis']['port']}): ",
            is_valid_port,
            "Invalid port number. It should be between 1 and 65535.",
            allow_empty=True
        ) or config['redis']['port']
        config['redis']['password'] = input("Enter Redis password (optional): ")
        config['redis']['clientName'] = input("Enter Redis client name: ") or f"GuildBridgeBot-{uuid.uuid4().hex[:8]}"
        config['redis']['receiveChannel'] = input("Enter Redis receive channel: ") or "guildbridge_receive"
        config['redis']['sendChannel'] = input("Enter Redis send channel: ") or "guildbridge_send"

    config['settings']['autoaccept'] = input("Enable autoaccept? (true/false, default: false): ").lower() == "true"
    config['settings']['dateLimit'] = int(input(f"Enter date limit (default: {config['settings']['dateLimit']} days): ") or config['settings']['dateLimit'])

    logging_enabled = input("Do you want to enable logging? (yes/no, default: no): ").lower()
    if logging_enabled == "yes":
        config['logging']['enabled'] = True
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        while True:
            log_level = input(f"Enter log level ({', '.join(log_levels)}), default: INFO: ").upper() or "INFO"
            if log_level in log_levels:
                config['logging']['level'] = log_level
                break
            print("Invalid log level. Please try again.")
        config['logging']['file'] = input("Enter log file name (default: guildbridge.log): ") or "guildbridge.log"
        
    return config

def print_summary(config):
    print("\nConfiguration Summary:")
    print(json.dumps(config, indent=2))
    print("\nPlease review the configuration above.")
    confirm = input("Is this configuration correct? (yes/no): ").lower()
    return confirm == 'yes'

def main():
    print(welcome_message)

    time.sleep(5)

    if os.path.exists("config.json"):
        existing_config = read_config()
        if existing_config:
            existing_config = migrate_config(existing_config)
            if is_config_valid(existing_config):
                print("Existing valid configuration found.")
                reset = input("Do you want to reset the configuration? (yes/no): ").lower()
                if reset != 'yes':
                    print("Exiting setup without changes.")
                    return
            else:
                print("Existing configuration is invalid or outdated. Starting fresh setup.")
        else:
            print("Failed to read existing configuration. Starting fresh setup.")
    else:
        print("No existing configuration found. Starting fresh setup.")

    backup_config()
    install_modules()

    config = default_config.copy()
    config = get_user_input(config)

    if print_summary(config):
        write_config(config)
        print("\nSetup completed successfully!")
    else:
        print("\nSetup cancelled. Configuration not saved.")
        restore = input("Do you want to restore a previous configuration? (yes/no): ").lower()
        if restore == 'yes':
            restored_config = restore_config()
            if restored_config:
                restored_config = migrate_config(restored_config)
                write_config(restored_config)
                print("Previous configuration restored and migrated if necessary.")
            else:
                print("Restoration cancelled.")

def signal_handler(sig, frame):
    print("\nSetup cancelled.")
    print("No changes made.")
    exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    main()