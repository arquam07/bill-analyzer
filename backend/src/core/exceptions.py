class AppError(Exception):
    """Base error for application-level exceptions."""


class EmailAlreadyExists(AppError):
    pass


class UsernameAlreadyExists(AppError):
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


class UserNotFound(AppError):
    pass


class BillHasNoTotal(AppError):
    """Bill total is null — cannot compute split amounts."""


class SplitRequestNotFound(AppError):
    pass


class SplitRequestNotPending(AppError):
    """Accept/reject attempted on a non-pending request."""


class SplitRequestNotRecipient(AppError):
    """User tried to accept/reject a request they didn't receive."""


class SplitRequestAlreadyExists(AppError):
    """A pending request for this bill+pair already exists."""


class SplitWithSelf(AppError):
    """User tried to split a bill with themselves."""


class SplitItemsInvalid(AppError):
    """One or more bill_item_ids don't belong to the bill or have no price."""


class FriendRequestNotFound(AppError):
    pass


class FriendRequestNotPending(AppError):
    """Accept/reject attempted on a non-pending friend request."""


class FriendRequestNotRecipient(AppError):
    """User tried to accept/reject a friend request they didn't receive."""


class FriendRequestAlreadyExists(AppError):
    """A pending friendship already exists between these users."""


class AlreadyFriends(AppError):
    pass
