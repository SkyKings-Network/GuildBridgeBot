# GuildBridgeBot

## To Do

- [ ] Improve minecraft -> discord speed
  - Possible use a queue instead of dispatching events
- [ ] Add requirements to autoaccept
- [ ] Make logs easier to read (less print statements)


## Initial Setup

Instructions are for Linux/Ubuntu machines

```shell
# Ensure we are in the home directory
cd ~

# Install nvm & node
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.38.0/install.sh | bash
source ~/.bashrc
nvm install 19.7.0

# Install pm2 for process management
npm install -g pm2

# Install python3
sudo apt-get update
sudo apt install python3-pip

# Clone the project
git clone https://github.com/Jacktheguys/GuildBridgeBot

# Create directories for bridge bots
mkdir bridges

# Create config file
mv GuildBridgeBot/example.config.json GuildBridgeBot/config.json
```


## Creating A New Bridge Bot

```shell
# Ensure we are in the home directory
cd ~

# Copy files for a new bridge bot
mkdir bridges/<NAME_OF_GUILD>
cp -r GuildBridgeBot/* bridges/<NAME_OF_GUILD>/
cd bridges/<NAME_OF_GUILD>

# Create a virtal environment
apt install python3.12-venv
python3 -m venv venv
source venv/bin/activate

# Install requirements
python3 -m pip install -U -r requirements.txt

# Update the config
nano config.json

# Then run the bot with pm2
pm2 start main.py --name <NAME_OF_GUILD>-BridgeBot --interpreter python3 --restart-delay=3000
```

## Updating A Bridge Bot

Coming Soon TM


## Setting up Redis [Optional & Advanced]

You can use Redis Pub/Sub to control the bridge bots programmatically from an external source.

This is useful when you want to set up automation for the bridge bots without modifying the original project.

Note that most users will never use this, and we will likely not provide support to you regarding this system.

Prerequisites:
- You have a redis server

Add the redis server's details to the config.json file, then make sure the following are set properly:
- `clientName` is set to something unique, such as your guild's name
- `recieveChannel` is set to the base channel you want to recieve messages from
  - Messages will be recieved on `{recieveChannel}:{clientName}`
- `sendChannel` is set to the channel that the controller is recieving messages on

You can then publish messages to the `{recieveChannel}:{clientName}` channel with the following format:
```json
{
    "type": "request",
    "source": "unique string identifying where the request came from, useful for multiple controllers",
    "uuid": "unique string identifying the request, so you can get a response",
    "endpoint": "'endpoint' of the bridge bot to call",
    "data": {
        "key": "value"
    }
}
```

The bridge bot will then respond with a message on the `sendChannel` with the following format:
```json
{
    "type": "response",
    "source": "clientName",
    "uuid": "same uuid as request",
    "data": {
        "success": false,
        "error": "error message, only present if success is false"
    }
}
```

If an unexpected error occurs, the bridge bot will log the error to console and respond with the following:
```json
{
    "type": "response",
    "source": "clientName",
    "uuid": "same uuid as request",
    "data": {
        "error": "details"
    }
}
```
Note the lack of a `success` key, as something internal raised an exception that wasn't supposed to.
