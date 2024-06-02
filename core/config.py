import json

from core.errors import InvalidConfig

__all__ = (
    "ServerConfig",
    "AccountConfig",
    "DiscordConfig",
    "RedisConfig",
    "SettingsConfig",
    "ExtensionConfig",
)

config = {}


class ConfigKey:
    def __init__(self, type: type, default=...):
        self.type = type
        self.default = (default or "") if default is not ... else ""
        self.required = default is ...
        self._parent = None
        self.key = None

    def validate(self, value):
        print(self.key, value)
        if not value:
            if self.required:
                raise ValueError(f"Missing required key '{self.key}'")
        elif not isinstance(value, self.type):
            try:
                value = self.type(value)
                print(value, self.type)
            except Exception:
                raise TypeError(f"Expected {self.type.__name__} for '{self.key}' but got {type(value).__name__}")
        return value


class _ConfigObject(type):
    def __new__(cls, name, bases, attrs, **kwargs):
        if kwargs.get("base_key") is None:
            raise ValueError("base_key is required in class init")
        # get all class attrs that are ConfigKey instances
        keys = {k: v for k, v in attrs.items() if isinstance(v, ConfigKey)}
        # pass them off to the class init
        obj = super().__new__(cls, name, bases, attrs)
        obj.keys = keys
        obj.BASE_KEY = kwargs["base_key"]
        # validate the config
        for key, value in keys.items():
            value.key = key
            if key in ("keys", "BASE_KEY"):
                raise ValueError(f"Invalid key name '{key}'")
            if key not in config:
                config[key] = value.default
            else:
                value.validate(config[key])
            setattr(obj, key, config[key])
            print(key, config[key])
        return obj


class ConfigObject(metaclass=_ConfigObject, base_key=""):
    keys: dict[str, ConfigKey]
    BASE_KEY: str

    @classmethod
    def __getitem__(cls, item):
        return config[cls.BASE_KEY][item]

    @classmethod
    def __setitem__(cls, key, value):
        cls.keys[key].validate(value)
        config[cls.BASE_KEY][key] = value
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)

    @classmethod
    def __getattr__(cls, item):
        return config[cls.BASE_KEY][item]

    @classmethod
    def __iter__(cls):
        return iter(config[cls.BASE_KEY])

    @classmethod
    def get(cls, key):
        return config[cls.BASE_KEY].get(key)

    @classmethod
    def validate(cls, _config: dict):
        data = _config.get(cls.BASE_KEY)
        if data is None:
            # check if anything is required
            for k, v in cls.keys.items():
                if v.required:
                    raise InvalidConfig(f"Missing required section '{cls.BASE_KEY}'")
            _config[cls.BASE_KEY] = {}
        for k, v in cls.keys.items():
            config_val = data.get(k)
            val = v.validate(config_val)
            data[k] = val
        with open("config.json", "w") as f:
            json.dump(_config, f, indent=4)


class ServerConfig(ConfigObject, base_key="server"):
    host: str = ConfigKey(str, "mc.hypixel.net")
    port: int = ConfigKey(int, 25565)


class AccountConfig(ConfigObject, base_key="account"):
    email: str = ConfigKey(str)


class DiscordConfig(ConfigObject, base_key="discord"):
    token: str = ConfigKey(str)
    channel: int = ConfigKey(int)
    officerChannel: int | None = ConfigKey(int, None)
    commandRole: int | None = ConfigKey(int, None)
    overrideRole: int | None = ConfigKey(int, None)
    ownerId: int | None = ConfigKey(int, None)
    prefix: str = ConfigKey(str, "!")
    webhookURL: str | None = ConfigKey(str, None)
    officerWebhookURL: str | None = ConfigKey(str, None)
    debugWebhookURL: str | None = ConfigKey(str, None)


class RedisConfig(ConfigObject, base_key="redis"):
    host: str | None = ConfigKey(str, None)
    port: int = ConfigKey(int, 6379)
    password: str | None = ConfigKey(str, None)
    clientName: str | None = ConfigKey(str, None)
    recieveChannel: str | None = ConfigKey(str, None)
    sendChannel: str | None = ConfigKey(str, None)


class SettingsConfig(ConfigObject, base_key="settings"):
    autoaccept: bool = ConfigKey(bool, False)
    extensions: list[str] = ConfigKey(list, [])


_config_objects = [ServerConfig, AccountConfig, DiscordConfig, RedisConfig, SettingsConfig]


def validate_config(_config: dict):
    for section in _config_objects:
        section.validate(_config)
    return _config


def generate_config():
    _config = {}
    for section in _config_objects:
        _config[section.BASE_KEY] = {}
        for k, v in section.keys.items():
            _config[section.BASE_KEY][k] = v.default or ""
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
print("Config loaded successfully!")
print(SettingsConfig.extensions)


class ExtensionConfig(ConfigObject, base_key=""):
    """
    This class is used for extensions to store their config data.

    Example:
    ```
    class MyExtensionConfig(ExtensionConfig, base_key="my_extension"):
        my_key = ConfigKey(str, "default value")
    ```

    This will create a section in the config file called `my_extension` with a key `my_key`,
    as well as perform data validation automatically.

    To access the data:
    ```
    # As a dictionary
    MyExtensionConfig["my_key"]

    # With attribute access
    MyExtensionConfig.my_key
    ```
    """
