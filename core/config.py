import json
from typing import Any, Dict, Union, List

from core.errors import InvalidConfig

__all__ = (
    "ServerConfig",
    "AccountConfig",
    "DiscordConfig",
    "RedisConfig",
    "SettingsConfig",
    "ConfigKey",
    "ExtensionConfig",
    "DataConfig",
)

_completed_init = False
_fnf = False
try:
    with open("config.json", "r") as file:
        config = json.load(file)
except FileNotFoundError as e:
    config = {}
    _fnf = True
except json.JSONDecodeError as e:
    raise InvalidConfig("The config file is not a valid JSON file.") from e


class ConfigKey:
    def __init__(self, type: type, default=..., *, list_type: type = None):
        if type is not list and list_type:
            raise ValueError("list_type is only valid when type is list")
        self.type = type
        self.default = default if default is not ... else ""
        self.required = default is ...
        self.basekey = None
        self.key = None
        self.list_type = list_type

    def validate(self, value):
        if not value:
            if self.required:
                raise InvalidConfig(f"Missing required key '{self.key}' in section '{self.basekey}'")
            return self.default
        elif not isinstance(value, self.type):
            try:
                value = self.type(value)
            except Exception:
                raise TypeError(
                    f"Expected {self.type.__name__} for '{self.key}' in section '{self.basekey}' "
                    f"but got {type(value).__name__}"
                    )
        if isinstance(value, list) and self.list_type:
            for index, item in enumerate(value):
                if not isinstance(item, self.list_type):
                    try:
                        value[index] = self.list_type(item)
                    except Exception:
                        raise TypeError(
                            f"Expected {self.list_type.__name__} for '{self.key}.{index}' in section '{self.basekey}' "
                            f"but got {type(item).__name__}"
                        )
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
        data = config.get(obj.BASE_KEY)
        if data is not None:
            for key, value in keys.items():
                value.key = key
                value.basekey = obj.BASE_KEY
                if key in ("keys", "BASE_KEY"):
                    raise InvalidConfig(f"Invalid key name '{key}' in section '{obj.BASE_KEY}'")
                if key not in data:
                    if value.required:
                        raise InvalidConfig(f"Missing required key '{key}' in section '{obj.BASE_KEY}'")
                    data[key] = value.default
                else:
                    data[key] = value.validate(data[key])
                setattr(obj, key, data[key])
        elif _completed_init and keys:
            # add all keys n stuff
            config[obj.BASE_KEY] = {}
            for k, v in keys.items():
                config[obj.BASE_KEY][k] = v.default
                setattr(obj, k, v.default)
            with open("config.json", "w") as f:
                json.dump(config, f, indent=4)
            # check if anything is required
            for k, v in keys.items():
                if v.required:
                    raise InvalidConfig(
                        f"Missing required section '{obj.BASE_KEY}'. "
                        f"It has been automatically added to the config file, "
                        f"please update the settings."
                        )
        return obj

    @classmethod
    def __getitem__(cls, item: str) -> Any:
        raise NotImplementedError

    @classmethod
    def __setitem__(cls, key: str, value: Any):
        raise NotImplementedError

    @classmethod
    def __getattr__(cls, item: str) -> Any:
        raise NotImplementedError

    @classmethod
    def __iter__(cls) -> Any:
        raise NotImplementedError

    @classmethod
    def get(cls, key: str) -> Any:
        raise NotImplementedError

    @classmethod
    def validate(cls, _config: Dict) -> None:
        raise NotImplementedError


class ConfigObject(metaclass=_ConfigObject, base_key=""):
    keys: Dict[str, ConfigKey]
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
    def __setattr__(cls, key, value):
        cls[key] = value

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
            data = _config[cls.BASE_KEY]

        for k, v in cls.keys.items():
            print(k, v)
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

class DataConfig(ConfigObject, base_key="data"):
    current_version: str = ConfigKey(str, "")
    latest_version: str = ConfigKey(str, "")

class DiscordConfig(ConfigObject, base_key="discord"):
    token: str = ConfigKey(str)
    channel: int = ConfigKey(int)
    allowCrosschat: List[int] = ConfigKey(list, [], list_type=int)
    officerChannel: Union[int, None] = ConfigKey(int, None)
    allowOfficerCrosschat: List[int] = ConfigKey(list, [], list_type=int)
    commandRole: Union[int, None] = ConfigKey(int, None)
    overrideRole: Union[int, None] = ConfigKey(int, None)
    ownerId: Union[int, None] = ConfigKey(int, None)
    prefix: str = ConfigKey(str, "!")
    webhookURL: Union[str, None] = ConfigKey(str, None)
    officerWebhookURL: Union[str, None] = ConfigKey(str, None)
    debugWebhookURL: Union[str, None] = ConfigKey(str, None)
    serverName: Union[str, None] = ConfigKey(str, None)
    ignoreCrosschatWarning: bool = ConfigKey(bool, False)


class RedisConfig(ConfigObject, base_key="redis"):
    host: Union[str, None] = ConfigKey(str, None)
    port: int = ConfigKey(int, 6379)
    password: Union[str, None] = ConfigKey(str, None)
    clientName: Union[str, None] = ConfigKey(str, None)
    recieveChannel: Union[str, None] = ConfigKey(str, None)
    sendChannel: Union[str, None] = ConfigKey(str, None)


class SettingsConfig(ConfigObject, base_key="settings"):
    autoaccept: bool = ConfigKey(bool, False)
    dateLimit: int = ConfigKey(int, 30)
    extensions: List[str] = ConfigKey(list, [], list_type=str)


_config_objects = [ServerConfig, AccountConfig, DiscordConfig, RedisConfig, SettingsConfig, DataConfig]


def validate_config(_config: Dict):
    for section in _config_objects:
        section.validate(_config)
    return _config


def generate_config():
    _config = {}
    for section in _config_objects:
        _config[section.BASE_KEY] = {}
        for k, v in section.keys.items():
            _config[section.BASE_KEY][k] = v.default if v.default not in (..., None) else ""
    with open("config.json", "w") as f:
        json.dump(_config, f, indent=4)


if _fnf:
    generate_config()
    raise InvalidConfig(
        "No config file was found, so we generated one for you. Please set it up before continuing."
    )
validate_config(config)
_completed_init = True


class ExtensionConfig(ConfigObject, base_key=""):
    """
    This class is used for extensions to store their config data.

    Example:
    ```
    class MyExtensionConfig(ExtensionConfig, base_key="my_extension"):
        my_key: str = ConfigKey(str, "default value")
        my_number: int = ConfigKey(int)  # required, no default value
        my_optional: str = ConfigKey(str, None)  # optional, with blank default (will be equivilant to "" in json)
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

    Gimmics:
    - A blank string (`""`) is considered a null-value during validation.
    - If a config section is missing, it will automatically be added to the config file.
        New keys will not be added, and will need to be entered manually.
    """
