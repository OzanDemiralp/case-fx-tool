from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from .router import router
from .exceptions import FXException
from .schemas import ErrorCode

app = FastAPI(title="MangoLab FX Case")

app.include_router(router)

@app.exception_handler(FXException)
async def fx_exception_handler(request: Request, exc: FXException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error.value, "message": exc.message}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    first_error = exc.errors()[0]
    field = first_error.get("loc", ["unknown"])[-1]
    msg = first_error.get("msg", "Invalid parameter")
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": ErrorCode.INVALID_INPUT.value,
            "message": f"Invalid '{field}': {msg}"
        }
    )