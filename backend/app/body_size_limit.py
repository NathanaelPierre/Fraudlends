"""
Rejects requests with an unreasonably large body before any real work
happens on them.
"""
from starlette.responses import JSONResponse

MAX_BODY_SIZE_BYTES = 1_000_000


class BodySizeLimitMiddleware:
    def __init__(self, app, max_body_size: int = MAX_BODY_SIZE_BYTES):
        self.app = app
        self.max_body_size = max_body_size

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")

        if content_length is not None:
            try:
                length = int(content_length)
            except ValueError:
                length = None

            if length is not None and length > self.max_body_size:
                response = JSONResponse(
                    status_code=413,
                    content={"detail": f"Request body too large. Maximum allowed size is {self.max_body_size // 1000} KB."},
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)
