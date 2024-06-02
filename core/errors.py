
class BridgeBotException(Exception):
    """Base exception for BridgeBot."""
    pass


class InvalidConfig(BridgeBotException):
    """Raised when the config is invalid."""
    pass


def send_debug_message(*args, **kwargs) -> None:
    """Send a debug message to the debug channel."""
    from core.config import DiscordConfig
    if not DiscordConfig.debugWebhookURL:
        return
    try:
        import requests
    except ImportError:
        return
    requests.post(DiscordConfig.debugWebhookURL, json={"content": " ".join(args), **kwargs})
