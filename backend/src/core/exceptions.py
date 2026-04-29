class AppError(Exception):
    """Base error for application-level exceptions."""


class EmailAlreadyExists(AppError):
    pass


class InvalidCredentials(AppError):
    pass


class InvalidSessionToken(AppError):
    pass


class UnsupportedImageFormat(AppError):
    pass


class OllamaUnavailable(AppError):
    pass


class OllamaResponseError(AppError):
    pass


class VLMResponseInvalid(AppError):
    pass


class BillNotFound(AppError):
    pass


class BillItemNotFound(AppError):
    pass


class BillNotEditable(AppError):
    """Raised when a write is attempted on a finalized (reviewed) bill."""


class BillNotExtracted(AppError):
    """Raised when finalize is called before extraction has produced data."""


class SplitParticipantNotFound(AppError):
    pass


class SplitParticipantConflict(AppError):
    """Raised when a participant name collides within a split."""


class InvalidInsightsRange(AppError):
    """Raised when an insights query receives an unusable date range."""
