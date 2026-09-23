"""
Standard security response headers, added to every response.
"""

DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        is_docs_path = any(path.startswith(p) for p in DOCS_PATHS)

        async def send_with_security_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-content-type-options", b"nosniff"))
                headers.append((b"x-frame-options", b"DENY"))
                if not is_docs_path:
                    headers.append((b"content-security-policy", b"default-src 'none'"))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_security_headers)
