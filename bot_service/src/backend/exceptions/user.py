class UserExists(Exception):
    """Custom exception for Invalid config type"""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class InactiveUser(Exception):
    """Custom exception for Invalid config type"""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
