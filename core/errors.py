from core.config import discord as config


class BridgeBotException(Exception):
    """Base exception for BridgeBot."""
    pass


class InvalidConfig(BridgeBotException):
    """Raised when the config is invalid."""
    pass


def send_debug_message(*args, **kwargs) -> None:
    """Send a debug message to the debug channel."""
    import requests
    url = config.debugWebhookURL
    requests.post(url, json={"content": " ".join(args), **kwargs})


if not config.debugWebhookURL:
    send_debug_message = lambda *args, **kwargs: None
