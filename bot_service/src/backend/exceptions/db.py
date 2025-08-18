class DBException(Exception):
    """Exception raised for database errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
