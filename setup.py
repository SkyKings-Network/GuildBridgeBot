import signal
import subprocess
import json
import os
import re
import shutil
from datetime import datetime
import time
import uuid
from cryptography.fernet import Fernet
import getpass

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

CONFIG_VERSION = "1.1"

default_config = {
    "version": CONFIG_VERSION,
    "server": {"host": "mc.hypixel.net", "port": 25565},
    "account": {"email": ""},
    "discord": {
        "token": "",
        "channel": "",
        "officerChannel": "",
        "commandRole": "",
        "overrideRole": "",
        "ownerId": "",
        "prefix": "!",
        "webhookURL": "",
        "officerWebhookURL": "",
        "debugWebhookURL": "",
        "serverName": ""
    },
    "redis": {
        "enabled": False,
        "host": "",
        "port": 6379,
        "password": "",
        "clientName": "",
        "receiveChannel": "",
        "sendChannel": ""
    },
    "settings": {"autoaccept": False, "dateLimit": 30, "extensions": []},
    "logging": {"enabled": False, "level": "INFO", "file": "guildbridge.log"},
    "encryption": {"enabled": False, "key": ""}
}

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

def validate_input(prompt, validator, error_message, allow_empty=False):
    while True:
        user_input = input(prompt)
        if allow_empty and user_input == "":
            return user_input
        if validator(user_input):
            return user_input
        print(error_message)

def is_valid_email(email):
    return re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email) is not None

def is_valid_discord_id(discord_id):
    return discord_id.isdigit() and 17 <= len(discord_id) <= 19

def is_valid_url(url):
    return re.match(r"^https://(?:ptb\.|canary\.)?discord(?:app)?\.com/api/webhooks/\d+/[\w-]+$", url) is not None

def is_valid_port(port):
    return port.isdigit() and 1 <= int(port) <= 65535

def is_valid_prefix(prefix):
    return len(prefix) == 1 and prefix.isprintable()

def is_valid_role_name(role):
    return 1 <= len(role) <= 100 and all(c.isprintable() for c in role)

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

    encrypt_config = input("Do you want to encrypt sensitive information in the config? (yes/no, default: no): ").lower() == 'yes'
    if encrypt_config:
        config['encryption']['enabled'] = True
        config['encryption']['key'] = generate_encryption_key().decode()
        print("Encryption key generated. Please keep it safe!")
        
    return config

def write_config(config):
    try:
        if config['encryption']['enabled']:
            config = encrypt_config(config, config['encryption']['key'].encode())
        
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)
        print("\nConfiguration successfully saved to config.json.")
    except IOError as e:
        print(f"Failed to write config.json: {e}")

def backup_config():
    if os.path.exists("config.json"):
        backup_name = f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        shutil.copy("config.json", backup_name)
        print(f"Existing configuration backed up as {backup_name}")

def restore_config():
    backups = [f for f in os.listdir() if f.startswith("config_backup_") and f.endswith(".json")]
    if not backups:
        print("No backup files found.")
        return None

    print("Available backups:")
    for i, backup in enumerate(backups, 1):
        print(f"{i}. {backup}")

    choice = input("Enter the number of the backup to restore (or 'c' to cancel): ")
    if choice.lower() == 'c':
        return None

    try:
        choice = int(choice) - 1
        if 0 <= choice < len(backups):
            with open(backups[choice], 'r') as f:
                return json.load(f)
        else:
            print("Invalid choice.")
            return None
    except ValueError:
        print("Invalid input.")
        return None

def print_summary(config):
    print("\nConfiguration Summary:")
    safe_config = config.copy()
    safe_config['discord']['token'] = '********' if safe_config['discord']['token'] else ''
    safe_config['redis']['password'] = '********' if safe_config['redis']['password'] else ''
    print(json.dumps(safe_config, indent=2))
    print("\nPlease review the configuration above.")
    confirm = input("Is this configuration correct? (yes/no): ").lower()
    return confirm == 'yes'


def is_config_valid(config):
    required_fields = [
        config['account']['email'],
        config['discord']['token'],
        config['discord']['channel'],
        config['discord']['officerChannel'],
        config['discord']['ownerId'],
        config['discord']['webhookURL'],
        config['discord']['officerWebhookURL']
    ]
    return all(required_fields)

def encrypt_config(config, key):
    f = Fernet(key)
    sensitive_fields = [
        ('discord', 'token'),
        ('discord', 'webhookURL'),
        ('discord', 'officerWebhookURL'),
        ('discord', 'debugWebhookURL'),
        ('redis', 'password')
    ]
    for section, field in sensitive_fields:
        if section in config and field in config[section] and config[section][field]:
            config[section][field] = f.encrypt(config[section][field].encode()).decode()
    return config

def decrypt_config(config, key):
    f = Fernet(key)
    sensitive_fields = [
        ('discord', 'token'),
        ('discord', 'webhookURL'),
        ('discord', 'officerWebhookURL'),
        ('discord', 'debugWebhookURL'),
        ('redis', 'password')
    ]
    for section, field in sensitive_fields:
        if section in config and field in config[section] and config[section][field]:
            try:
                config[section][field] = f.decrypt(config[section][field].encode()).decode()
            except:
                print(f"Warning: Unable to decrypt {section}.{field}. It may not be encrypted.")
    return config

def generate_encryption_key():
    return Fernet.generate_key()

def migrate_config(old_config):
    current_version = old_config.get('version', '0.0')
    new_config = old_config.copy()

    if current_version != CONFIG_VERSION:
        print(f"Migrating configuration from version {current_version} to {CONFIG_VERSION}")

        # Version 0.0 to 1.0 migration
        if current_version == '0.0':
            new_config['version'] = '1.0'
            new_config['encryption'] = {'enabled': False, 'key': ''}
            
        # Version 1.0 to 1.1 migration
        if current_version == '1.0':
            new_config['version'] = '1.1'
            new_config['discord']['debugWebhookURL'] = ''
            
        # Add any new fields from default_config that don't exist in old_config
        for key, value in default_config.items():
            if key not in new_config:
                new_config[key] = value
            elif isinstance(value, dict):
                for subkey, subvalue in value.items():
                    if subkey not in new_config[key]:
                        new_config[key][subkey] = subvalue

        print("Configuration migration completed.")
    
    return new_config

def read_config():
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        
        if config.get('encryption', {}).get('enabled', False):
            key = getpass.getpass("Enter the encryption key to decrypt the configuration: ").encode()
            config = decrypt_config(config, key)
        
        return config
    except IOError as e:
        print(f"Failed to read config.json: {e}")
        return None

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