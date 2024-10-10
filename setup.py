import subprocess
import json
import os

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

CONFIG_VERSION = "1.0"

default_config = {
    "version": CONFIG_VERSION,
    "server": {
        "host": "mc.hypixel.net",
        "port": 25565
    },
    "account": {
        "email": ""
    },
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
    "settings": {
        "autoaccept": False,
        "dateLimit": 30,
        "extensions": []
    },
    "logging": {
        "enabled": False,
        "level": "INFO",
        "file": "guildbridge.log"
    },
    "encryption": {
        "enabled": False,
        "key": ""
    }
}

def install_modules():
    try:
        print("\nInstalling required Python modules from requirements.txt...")
        subprocess.check_call(["pip", "install", "-r", "requirements.txt"])

        print("\nInstalling discord.py module...")
        subprocess.check_call(["pip", "install", "discord.py"])

        print("\nInstalling mineflayer via npm...")
        subprocess.check_call(["npm", "install", "mineflayer"])

        print("\nAll required modules were installed successfully.")
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
        if section in config and field in config[section]:
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
        if section in config and field in config[section]:
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
            
            # Add any new fields from default_config that don't exist in old_config
            for key, value in default_config.items():
                if key not in new_config:
                    new_config[key] = value

        # Add more migration steps here for future versions

        print("Configuration migration completed.")
    
    return new_config

def get_user_input(config):
    print("\nPlease provide the following configuration details:\n")

    # Existing input collection code remains here...

    # Add encryption option
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

def read_config():
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        
        if config.get('encryption', {}).get('enabled', False):
            key = input("Enter the encryption key to decrypt the configuration: ").encode()
            config = decrypt_config(config, key)
        
        return config
    except IOError as e:
        print(f"Failed to read config.json: {e}")
        return None

def main():
    print(welcome_message)

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

if __name__ == "__main__":
    main()
    