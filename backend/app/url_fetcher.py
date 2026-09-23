"""
Fetches the text content of a user-submitted URL, so a suspicious link
can be analyzed the same way pasted text is (registry check, indicator
extraction, domain analysis, eventually the AI layer) instead of
requiring the user to manually copy the page's content.

SECURITY: fetching an arbitrary user-submitted URL from the backend is
a real SSRF (Server-Side Request Forgery) risk, a malicious input
could point the server at an internal service (a cloud metadata
endpoint, an internal admin panel, a database's HTTP interface) that
would never be reachable from outside, and get the server to fetch and
return it. This module is built specifically to close that off:

1. Only http/https schemes are allowed at all.
2. The hostname is resolved and the resulting IP is checked (not just
   the hostname string) against private, loopback, link-local, and
   reserved ranges, checking the string alone is insufficient, since
   "localhost", a hex-encoded IP, and a hostname that resolves to a
   private IP via DNS would all otherwise slip through a naive
   string-based check.
3. A short connect/read timeout prevents a slow or hanging server from
   tying up a request indefinitely.
4. Response size is capped so a malicious or huge page can't exhaust
   memory.
5. Redirects are followed manually, re-validating the destination at
   each hop, a URL can pass the initial check and then redirect
   somewhere internal, which requests' automatic redirect handling
   would otherwise follow blindly.
"""
import ipaddress
import socket
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

ALLOWED_SCHEMES = {"http", "https"}
MAX_RESPONSE_BYTES = 500_000
REQUEST_TIMEOUT_SECONDS = 5
MAX_REDIRECTS = 3
MAX_EXTRACTED_TEXT_CHARS = 5000


class UnsafeUrlError(Exception):
    """Raised when a URL is rejected for pointing at a disallowed
    destination, never raised for ordinary network failures, which are
    a separate, expected case (see FetchError)."""


class FetchError(Exception):
    """Raised for ordinary failures fetching an otherwise-safe URL:
    timeout, connection refused, non-HTML content, etc."""


def _resolve_and_validate_host(hostname: str) -> str:
    """
    Resolves hostname to an IP and rejects it if that IP falls in any
    private, loopback, link-local, multicast, or reserved range.
    Checking the resolved IP (not the hostname string) is essential, a
    hostname such as "internal.example.com" that an attacker controls
    via DNS could resolve to 127.0.0.1 or an internal IP despite
    looking like an ordinary public domain in the URL itself.
    """
    try:
        resolved_ip = socket.gethostbyname(hostname)
    except socket.gaierror:
        raise UnsafeUrlError(f"Could not resolve hostname: {hostname}")

    ip_obj = ipaddress.ip_address(resolved_ip)
    if (
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_reserved
        or ip_obj.is_unspecified
    ):
        raise UnsafeUrlError(f"URL resolves to a disallowed address: {resolved_ip}")

    return resolved_ip


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"Only http/https URLs are allowed, got: {parsed.scheme}")
    if not parsed.hostname:
        raise UnsafeUrlError("URL has no hostname")
    _resolve_and_validate_host(parsed.hostname)


def fetch_url_text(url: str) -> str:
    """
    Returns the extracted, visible text content of the given URL.
    Raises UnsafeUrlError if the URL is rejected for security reasons,
    or FetchError for an ordinary failure (timeout, non-HTML content,
    HTTP error status). Callers should treat both as "could not
    analyze this URL" from the user's perspective, see
    app/routers/checks.py for how this is surfaced.
    """
    current_url = url
    for _ in range(MAX_REDIRECTS + 1):
        _validate_url(current_url)

        try:
            response = requests.get(
                current_url,
                timeout=REQUEST_TIMEOUT_SECONDS,
                allow_redirects=False,
                stream=True,
                headers={"User-Agent": "FraudLensBot/1.0 (link-safety-check)"},
            )
        except requests.RequestException as e:
            raise FetchError(f"Could not reach the URL: {e}")

        if response.status_code in (301, 302, 303, 307, 308):
            next_url = response.headers.get("Location")
            if not next_url:
                raise FetchError("Redirect response had no Location header")
            current_url = next_url
            continue

        if response.status_code != 200:
            raise FetchError(f"URL returned HTTP {response.status_code}")

        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            raise FetchError(f"URL content type is not text/HTML: {content_type}")

        raw_bytes = response.raw.read(MAX_RESPONSE_BYTES + 1, decode_content=True)
        if len(raw_bytes) > MAX_RESPONSE_BYTES:
            raise FetchError("URL content exceeded the maximum allowed size")

        html = raw_bytes.decode(response.encoding or "utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = " ".join(soup.get_text(separator=" ").split())
        return text[:MAX_EXTRACTED_TEXT_CHARS]

    raise FetchError(f"Too many redirects (limit {MAX_REDIRECTS})")
