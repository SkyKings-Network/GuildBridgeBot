from datetime import datetime
import json
import os
import re
import shutil

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
    "logging": {"enabled": False, "level": "INFO", "file": "guildbridge.log"}
}

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

def validate_input(prompt, validator, error_message, allow_empty=False):
    while True:
        user_input = input(prompt)
        if allow_empty and user_input == "":
            return user_input
        if validator(user_input):
            return user_input
        print(error_message)

def write_config(config):
    try:        
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
        return backup_name

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
        
        return config
    except IOError as e:
        print(f"Failed to read config.json: {e}")
        return None
