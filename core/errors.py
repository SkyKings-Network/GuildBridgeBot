class BridgeBotException(Exception):
    """Base exception for BridgeBot."""
    pass


class InvalidConfig(BridgeBotException):
    """Raised when the config is invalid."""
    pass
