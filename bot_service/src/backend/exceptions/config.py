class ConfigurationError(Exception):
    """Custom exception for Invalid config type"""

    def __init__(self, message):
        """
        Initialize ConfigurationError with a message.
        """
        self.message = message
        super().__init__(self.message)
