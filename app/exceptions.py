from .schemas import ErrorCode


class FXException(Exception):
    """Base exception for all domain errors in the FX service."""
    def __init__(self, error: ErrorCode, message: str, status_code: int = 400):
        self.error = error
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class InvalidInputException(FXException):
    def __init__(self, message: str):
        super().__init__(
            error=ErrorCode.INVALID_INPUT,
            message=message,
            status_code=400,
        )


class SameCurrencyException(FXException):
    def __init__(self, currency: str):
        super().__init__(
            error=ErrorCode.SAME_CURRENCY,
            message=f"Base and target currency are the same ('{currency}'). No conversion needed.",
            status_code=400,
        )


class UnsupportedCurrencyException(FXException):
    def __init__(self, currency: str):
        super().__init__(
            error=ErrorCode.UNSUPPORTED_CURRENCY,
            message=f"Currency '{currency}' is not supported or not recognized by the ECB.",
            status_code=404,
        )


class RateUnavailableException(FXException):
    def __init__(self, message: str):
        super().__init__(
            error=ErrorCode.RATE_UNAVAILABLE,
            message=message,
            status_code=404,
        )


class UpstreamTimeoutException(FXException):
    def __init__(self):
        super().__init__(
            error=ErrorCode.UPSTREAM_TIMEOUT,
            message="Exchange rate upstream service timed out.",
            status_code=504,
        )


class UpstreamErrorException(FXException):
    def __init__(self, detail: str = "Upstream service error"):
        super().__init__(
            error=ErrorCode.UPSTREAM_ERROR,
            message=f"Exchange rate upstream service failed: {detail}",
            status_code=502,
        )