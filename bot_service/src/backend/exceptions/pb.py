class EvalException(Exception):
    """Exception raised for evaluation errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
