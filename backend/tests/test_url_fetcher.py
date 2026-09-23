"""
URL fetcher tests. SSRF protection is the security-critical part of
this module, these tests confirm every private, internal, or loopback
address class is rejected, using a mocked DNS resolution so they don't
depend on real network access or a live server.
"""
from unittest.mock import patch, MagicMock
import pytest
from app.url_fetcher import fetch_url_text, _validate_url, UnsafeUrlError, FetchError


def test_loopback_address_rejected():
    with pytest.raises(UnsafeUrlError):
        _validate_url("http://127.0.0.1/admin")


def test_localhost_hostname_rejected():
    """localhost resolves to a loopback address, the resolved IP is
    what's checked, not the literal string "localhost"."""
    with pytest.raises(UnsafeUrlError):
        _validate_url("http://localhost:8000/health")


def test_cloud_metadata_endpoint_rejected():
    """169.254.169.254 is the standard cloud metadata endpoint address
    (AWS, GCP, Azure), a classic, high-value SSRF target that must be
    blocked explicitly."""
    with pytest.raises(UnsafeUrlError):
        _validate_url("http://169.254.169.254/latest/meta-data/")


def test_private_range_10_rejected():
    with pytest.raises(UnsafeUrlError):
        _validate_url("http://10.0.0.5/internal")


def test_private_range_192_168_rejected():
    with pytest.raises(UnsafeUrlError):
        _validate_url("http://192.168.1.1/")


def test_private_range_172_16_rejected():
    with pytest.raises(UnsafeUrlError):
        _validate_url("http://172.16.0.1/")


def test_disallowed_scheme_rejected():
    with pytest.raises(UnsafeUrlError):
        _validate_url("ftp://example.com/file")


def test_file_scheme_rejected():
    with pytest.raises(UnsafeUrlError):
        _validate_url("file:///etc/passwd")


def test_hostname_that_resolves_to_private_ip_rejected():
    """
    The critical case: a hostname that looks like an ordinary public
    domain in the URL string, but resolves (via DNS, which an attacker
    controlling that domain's records could set up) to a private or
    internal IP. Checking only the string would miss this entirely,
    the resolved IP must be checked.
    """
    with patch("app.url_fetcher.socket.gethostbyname", return_value="127.0.0.1"):
        with pytest.raises(UnsafeUrlError):
            _validate_url("http://looks-like-a-normal-domain.com/")


def test_unresolvable_hostname_rejected():
    import socket as socket_module
    with patch("app.url_fetcher.socket.gethostbyname", side_effect=socket_module.gaierror("Name resolution failed")):
        with pytest.raises(UnsafeUrlError):
            _validate_url("http://this-does-not-resolve-at-all.invalid/")


def test_legitimate_public_url_fetches_successfully():
    with patch("app.url_fetcher.socket.gethostbyname", return_value="93.184.216.34"):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.encoding = "utf-8"
        mock_response.raw.read.return_value = b"<html><body><script>evil()</script><p>Hello world</p></body></html>"

        with patch("app.url_fetcher.requests.get", return_value=mock_response):
            result = fetch_url_text("http://example.com")
            assert "Hello world" in result
            assert "evil()" not in result


def test_non_html_content_type_rejected():
    with patch("app.url_fetcher.socket.gethostbyname", return_value="93.184.216.34"):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/octet-stream"}

        with patch("app.url_fetcher.requests.get", return_value=mock_response):
            with pytest.raises(FetchError):
                fetch_url_text("http://example.com/file.bin")


def test_oversized_response_rejected():
    from app.url_fetcher import MAX_RESPONSE_BYTES

    with patch("app.url_fetcher.socket.gethostbyname", return_value="93.184.216.34"):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.raw.read.return_value = b"x" * (MAX_RESPONSE_BYTES + 1)

        with patch("app.url_fetcher.requests.get", return_value=mock_response):
            with pytest.raises(FetchError):
                fetch_url_text("http://example.com")


def test_redirect_to_private_address_is_rejected_not_followed_blindly():
    """
    A URL can pass the initial validation and then redirect somewhere
    internal, the redirect destination must be re-validated, not
    followed automatically. This is why fetch_url_text() handles
    redirects manually (allow_redirects=False) instead of letting
    requests follow them.

    The mock resolves hostnames realistically: an IP-literal hostname
    (as the redirect target here is) resolves to itself, exactly as
    real socket.gethostbyname() does — a blanket mock returning the
    same public IP for every input, tried first, accidentally masked
    the very check this test exists to exercise.
    """
    def realistic_resolve(hostname):
        if hostname == "looks-safe-initially.com":
            return "93.184.216.34"
        return hostname  # IP literals resolve to themselves, as real DNS does

    with patch("app.url_fetcher.socket.gethostbyname", side_effect=realistic_resolve):
        redirect_response = MagicMock()
        redirect_response.status_code = 302
        redirect_response.headers = {"Location": "http://169.254.169.254/latest/meta-data/"}

        with patch("app.url_fetcher.requests.get", side_effect=[redirect_response]) as mock_get:
            with pytest.raises(UnsafeUrlError):
                fetch_url_text("http://looks-safe-initially.com")
            assert mock_get.call_count == 1


def test_too_many_redirects_rejected():
    with patch("app.url_fetcher.socket.gethostbyname", return_value="93.184.216.34"):
        redirect_response = MagicMock()
        redirect_response.status_code = 302
        redirect_response.headers = {"Location": "http://example.com/next"}

        with patch("app.url_fetcher.requests.get", return_value=redirect_response):
            with pytest.raises(FetchError):
                fetch_url_text("http://example.com/start")
