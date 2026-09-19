"""Finite HTTP operations; credentials never follow redirects."""
import json
import random
import time
import urllib.error
import urllib.parse
import urllib.request


class ApiError(Exception):
    def __init__(self, status, message, data=None):
        self.status, self.data = status, data or {}
        super().__init__(message)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_url(url):
    parts = urllib.parse.urlsplit(url)
    if parts.username or parts.password or parts.fragment:
        raise ValueError('Use a clean invitation URL without embedded credentials or fragment.')
    if parts.scheme != 'https' and not (parts.scheme == 'http' and parts.hostname in ('127.0.0.1', 'localhost', '::1')):
        raise ValueError('Use HTTPS, or HTTP on localhost for development.')
    return parts


def request(url, *, method='GET', body=None, token=None, timeout=60):
    validate_url(url)
    headers = {'Accept': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    encoded = None
    if body is not None:
        headers['Content-Type'] = 'application/json'
        encoded = json.dumps(body).encode()
    opener = urllib.request.build_opener(NoRedirect)
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=encoded, headers=headers, method=method)
            with opener.open(req, timeout=timeout) as response:
                data = response.read()
                return json.loads(data) if data else None
        except urllib.error.HTTPError as error:
            try:
                data = json.loads(error.read())
            except (ValueError, OSError):
                data = {}
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise ApiError(error.code, data.get('message', f'HTTP request failed ({error.code}).'), data) from None
            try:
                delay = min(5, max(0, float(error.headers.get('Retry-After', '1'))))
            except ValueError:
                delay = 1
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt == 2:
                raise ApiError(0, 'Connection failed. Retry the same command; saved requests will be reused.') from None
            delay = 2 ** attempt
        time.sleep(delay + random.random() * .2)
