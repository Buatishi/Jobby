class CVParsingError(Exception):
    def __init__(self, message: str, code: str = "CV_PARSING_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code
