"""KSeF API client – token-based (simplest) authentication and invoice listing."""

import base64
import hashlib
import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

KSEF_API_URL = "https://ksef.podatki.gov.pl/api"
KSEF_TEST_API_URL = "https://ksef-test.podatki.gov.pl/api"


class KSeFAuthError(Exception):
    """Raised when authentication with the KSeF API fails."""

    pass


class KSeFAPIError(Exception):
    """Raised when a KSeF API call returns an unexpected response."""

    pass


def _sign_token(token: str, timestamp: str) -> str:
    """Return the signed token value required by the KSeF *InitialisedToken* endpoint.

    The algorithm is:
        base64( SHA-256( base64(token_bytes) + timestamp_bytes ) )
    """
    token_b64 = base64.b64encode(token.encode("utf-8"))
    combined = token_b64 + timestamp.encode("utf-8")
    digest = hashlib.sha256(combined).digest()
    return base64.b64encode(digest).decode("utf-8")


class KSeFClient:
    """Minimal KSeF REST API client that uses token-based authentication."""

    def __init__(self, nip: str, token: str, *, test: bool = False) -> None:
        """Initialise the client.

        Args:
            nip: Polish NIP number (10 digits) of the entity to authenticate as.
            token: Authorization token issued by the KSeF portal.
            test: When *True* the demo/test environment is used instead of production.
        """
        self.nip = nip
        self.token = token
        self.base_url = KSEF_TEST_API_URL if test else KSEF_API_URL
        self.session_token: Optional[str] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        """Execute an HTTP request against the KSeF API.

        Args:
            method: HTTP method (``GET``, ``POST`` …).
            path: API path, starting with ``/``.
            data: Optional request body (will be JSON-encoded).
            extra_headers: Additional HTTP headers to send.

        Returns:
            Parsed JSON response body.

        Raises:
            KSeFAPIError: On any HTTP error or unexpected response.
        """
        url = f"{self.base_url}{path}"
        body = json.dumps(data).encode("utf-8") if data is not None else None

        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)

        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8")
            raise KSeFAPIError(f"HTTP {exc.code} from {url}: {error_body}") from exc
        except urllib.error.URLError as exc:
            raise KSeFAPIError(f"Connection error: {exc.reason}") from exc

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate(self) -> None:
        """Authenticate using the token-based (simplest) method.

        Performs a two-step handshake:
        1. Requests an authorisation challenge from the API.
        2. Sends back the signed token together with the challenge.

        On success :attr:`session_token` is populated with the value
        returned by the API.

        Raises:
            KSeFAuthError: When authentication fails or the session token
                cannot be extracted from the response.
            KSeFAPIError: On any low-level HTTP/network error.
        """
        # Step 1 – request a challenge
        challenge_response = self._request(
            "POST",
            "/online/Session/AuthorisationChallenge",
            {
                "contextIdentifier": {
                    "type": "onip",
                    "identifier": self.nip,
                }
            },
        )

        challenge: str = challenge_response.get("challenge", "")
        timestamp: str = challenge_response.get("timestamp", "")

        if not challenge or not timestamp:
            raise KSeFAuthError(
                "Invalid authorisation challenge response: "
                f"challenge={challenge!r}, timestamp={timestamp!r}"
            )

        # Step 2 – initialise session with signed token
        signed = _sign_token(self.token, timestamp)
        session_response = self._request(
            "POST",
            "/online/Session/InitialisedToken",
            {
                "challenge": {
                    "authToken": {
                        "encoding": "Base64",
                        "keystore": {
                            "type": "kseftoken",
                            "token": signed,
                        },
                    },
                    "challenge": challenge,
                }
            },
        )

        session_token = (session_response.get("sessionToken") or {}).get("token")
        if not session_token:
            raise KSeFAuthError(
                "Session token not found in response: "
                + json.dumps(session_response, ensure_ascii=False)
            )

        self.session_token = session_token

    # ------------------------------------------------------------------
    # Invoice listing
    # ------------------------------------------------------------------

    def list_invoices(
        self,
        date_from: str,
        date_to: str,
        *,
        page_offset: int = 0,
        page_size: int = 100,
    ) -> List[Dict[str, Any]]:
        """Return a list of invoices from the KSeF API.

        Authenticates automatically if no session token is present.

        Args:
            date_from: Start of the date range in ISO-8601 format
                (e.g. ``"2023-01-01T00:00:00.000Z"``).
            date_to: End of the date range in ISO-8601 format
                (e.g. ``"2023-12-31T23:59:59.999Z"``).
            page_offset: Zero-based page offset (default ``0``).
            page_size: Number of results per page (default ``100``).

        Returns:
            List of invoice header dictionaries as returned by the API.

        Raises:
            KSeFAuthError: If authentication fails.
            KSeFAPIError: On any HTTP/network error.
        """
        if not self.session_token:
            self.authenticate()

        response = self._request(
            "POST",
            "/online/Invoice/KSeF",
            {
                "invoiceDate": {
                    "dateFrom": date_from,
                    "dateTo": date_to,
                },
                "pageOffset": page_offset,
                "pageSize": page_size,
            },
            extra_headers={"SessionToken": self.session_token},
        )

        return response.get("invoiceList", [])
