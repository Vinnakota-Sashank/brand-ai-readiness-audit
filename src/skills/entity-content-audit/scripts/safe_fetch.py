"""
safe_fetch.py - Zero-dependency SSRF-safe HTTP/HTTPS fetching utility.
Enforces strict redirect boundaries, IP validation per hop,
bounded decompression, and DNS TOCTOU pinning.
"""

import http.client
import ipaddress
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib

DEFAULT_USER_AGENT = "Brand-AI-Readiness-Audit/1.0.0"

BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _is_safe_host(hostname):
    try:
        # Prevent malformed hostnames from reaching DNS
        if not hostname or " " in hostname:
            return False, "Malformed hostname", []

        ip_info = socket.getaddrinfo(hostname, 80, proto=socket.IPPROTO_TCP)
        safe_ips = []
        for sf in ip_info:
            ip_obj = ipaddress.ip_address(sf[4][0])
            if getattr(ip_obj, "ipv4_mapped", None):
                ip_obj = ip_obj.ipv4_mapped
            is_blocked = False
            if (
                ip_obj.is_multicast
                or getattr(ip_obj, "is_reserved", False)
                or ip_obj.is_private
                or ip_obj.is_loopback
                or ip_obj.is_link_local
            ):
                is_blocked = True
            for blocked in BLOCKED_NETWORKS:
                if ip_obj in blocked:
                    is_blocked = True
                    break
            if is_blocked:
                return False, f"IP {sf[4][0]} is in blocked network", []
            safe_ips.append(sf)

        if not safe_ips:
            return False, "No valid public IPs resolved", []

        return True, "", safe_ips
    except Exception as e:
        return False, f"DNS resolution failed: {e}", []


def _connect_safe(safe_ips, port, timeout, source_address):
    sorted_ips = sorted(safe_ips, key=lambda sf: 0 if sf[0] == socket.AF_INET else 1)
    last_err = None
    for sf in sorted_ips:
        try:
            return socket.create_connection((sf[4][0], port), timeout, source_address)
        except (OSError, socket.error) as err:
            last_err = err
    raise urllib.error.URLError(f"Failed to connect to host: {last_err}")


class SafeHTTPConnection(http.client.HTTPConnection):
    def connect(self):
        is_safe, err, safe_ips = _is_safe_host(self.host)
        if not is_safe:
            raise urllib.error.URLError(f"SSRF blocked: {err}")
        self.sock = _connect_safe(safe_ips, self.port, self.timeout, self.source_address)


class SafeHTTPSConnection(http.client.HTTPSConnection):
    def connect(self):
        is_safe, err, safe_ips = _is_safe_host(self.host)
        if not is_safe:
            raise urllib.error.URLError(f"SSRF blocked: {err}")
        self.sock = _connect_safe(safe_ips, self.port, self.timeout, self.source_address)
        if self._tunnel_host:
            self.sock = self.sock
            self._tunnel()
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)


class SafeHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(SafeHTTPConnection, req)


class SafeHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(SafeHTTPSConnection, req, context=ssl.create_default_context())


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, max_redirects=5):
        self.max_redirects = max_redirects
        self.redirects = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.redirects += 1
        if self.redirects > self.max_redirects:
            raise urllib.error.URLError("Too many redirects")
        parsed = urllib.parse.urlparse(newurl)
        if parsed.scheme not in ("http", "https"):
            raise urllib.error.URLError(f"Disallowed redirect scheme: {parsed.scheme}")

        is_safe, err, _ = _is_safe_host(parsed.hostname)
        if not is_safe:
            raise urllib.error.URLError(f"SSRF blocked on redirect: {err}")

        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _decompress_bounded(response, max_bytes):
    encoding = response.headers.get("Content-Encoding", "").lower()
    if encoding == "gzip":
        decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
    elif encoding == "deflate":
        decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
    elif encoding == "zstd" or encoding == "br":
        raise ValueError(f"Unsupported encoding: {encoding}")
    else:
        return response.read(max_bytes)

    out = bytearray()
    while len(out) < max_bytes:
        chunk = response.read(8192)
        if not chunk:
            break
        try:
            remaining = max_bytes - len(out)
            decompressed = decompressor.decompress(chunk, max_length=remaining)
            out.extend(decompressed)
            if decompressor.unconsumed_tail or len(out) >= max_bytes:
                return bytes(out[:max_bytes])
        except Exception as e:
            raise ValueError(f"Decompression error: {e}") from e
    return bytes(out)


def safe_fetch(url, timeout=10, max_bytes=5 * 1024 * 1024, user_agent=None, method="GET", deadline=None):
    if deadline:
        remaining = deadline - time.monotonic()
        if remaining <= 0.1:
            return None, "", {}, "Global deadline exceeded"
        timeout = min(timeout, remaining)

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return None, "", {}, f"Disallowed scheme: {parsed.scheme}"

    opener = urllib.request.build_opener(SafeHTTPHandler(), SafeHTTPSHandler(), SafeRedirectHandler(max_redirects=5))

    ua = user_agent if user_agent else DEFAULT_USER_AGENT
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate",
    }
    req = urllib.request.Request(url, headers=headers, method=method)

    try:
        with opener.open(req, timeout=timeout) as response:
            status = response.status
            resp_headers = {k.lower(): v for k, v in response.getheaders()}

            if method == "HEAD":
                return status, "", resp_headers, ""

            try:
                content = _decompress_bounded(response, max_bytes)
            except ValueError as e:
                return status, "", resp_headers, str(e)

            try:
                charset = response.headers.get_content_charset() or "utf-8"
                html = content.decode(charset, errors="replace")
            except Exception:
                html = content.decode("utf-8", errors="replace")

            return status, html, resp_headers, ""
    except urllib.error.HTTPError as e:
        return e.code, "", {}, str(e)
    except Exception as e:
        return None, "", {}, str(e)


def safe_check_status(url, timeout=5, deadline=None):
    status, _, _, _ = safe_fetch(url, timeout=timeout, max_bytes=1024, method="HEAD", deadline=deadline)
    if status in (403, 405, 501):
        status, _, _, _ = safe_fetch(url, timeout=timeout, max_bytes=1024, method="GET", deadline=deadline)
    return status
