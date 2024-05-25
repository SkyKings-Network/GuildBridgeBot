


class BridgeBotException(Exception):
    """Base exception for BridgeBot."""
    pass


class InvalidConfig(BridgeBotException):
    """Raised when the config is invalid."""
    pass


def send_debug_message(*args, **kwargs) -> None:
    """Send a debug message to the debug channel."""
    from core.config import discord as config
    if not config.debugWebhookURL:
        return
    import requests
    url = config.debugWebhookURL
    requests.post(url, json={"content": " ".join(args), **kwargs})

