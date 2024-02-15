import json

from core.errors import InvalidConfig

__all__ = (
    "server",
    "discord",
    "redis",
    "settings",
)

config_format = settings = {
    "server": {
        "host": (str, "mc.hypixel.net"),
        "port": (int, 25565),
    },
    "account": {
        "email": (str,),
    },
    "discord": {
        "token": (str,),
        "channel": (int,),
        "officerChannel": (int, ""),
        "commandRole": (int, ""),
        "overrideRole": (int, ""),
        "ownerId": (int, ""),
        "prefix": (str, "!"),
    },
    "redis": {
        "host": (str, ""),
        "port": (int, ""),
        "password": (str, ""),
        "clientName": (str, ""),
        "recieveChannel": (str, ""),
        "sendChannel": (str, ""),
    },
    "settings": {
        "autoaccept": (bool, False)
    }
}


def validate_config(_config):
    for key, value in config_format.items():
        if _config.get(key) is None:
            # Check if anything is required
            for k, v in value.items():
                if len(v) == 1:
                    raise InvalidConfig(f"Missing required section '{key}'")
            _config[key] = {}
        for k, v in value.items():
            config_val = _config[key].get(k)
            if config_val is None or config_val == "":
                if len(v) == 1:
                    raise InvalidConfig(f"Missing required key '{k}' in '{key}'")
                else:
                    if v[1] is not None:
                        _config[key][k] = v[1]
            elif not isinstance(config_val, v[0]):
                if v[0] in (str, int):
                    try:
                        _config[key][k] = v[0](config_val)
                    except Exception:
                        pass
                    else:
                        continue
                raise InvalidConfig(
                    f"Invalid type for key '{k}' in '{key}', "
                    f"expected {v[0].__name__} but got {type(config_val).__name__}"
                )
    with open("config.json", "w") as f:
        json.dump(_config, f, indent=4)
    return _config


def generate_config():
    _config = {}
    for key, value in config_format.items():
        _config[key] = {}
        for k, v in value.items():
            if len(v) == 1:
                _config[key][k] = ""
            else:
                _config[key][k] = v[1]
    with open("config.json", "w") as f:
        json.dump(_config, f, indent=4)


try:
    with open("config.json", "r") as file:
        config = json.load(file)
except FileNotFoundError as e:
    generate_config()
    raise InvalidConfig(
        "No config file was found, so we generated one for you. Please set it up before continuing."
    ) from e
except json.JSONDecodeError as e:
    raise InvalidConfig("The config file is not a valid JSON file.") from e

validate_config(config)


class ConfigObject:
    def __init__(self, base_key: str):
        self.__base_key = base_key

    def __getitem__(self, item):
        return config[self.__base_key][item]

    def __setitem__(self, key, value):
        config[self.__base_key][key] = value
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)

    def __getattr__(self, item):
        return config[self.__base_key][item]

    def __iter__(self):
        return iter(self.__dict__)


server = ConfigObject("server")
account = ConfigObject("account")
discord = ConfigObject("discord")
redis = ConfigObject("redis")
settings = ConfigObject("settings")
