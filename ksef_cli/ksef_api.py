"""KSeF API client – token-based authentication and invoice listing (API v2)."""

import base64
import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import load_der_x509_certificate

KSEF_API_URL = "https://api.ksef.mf.gov.pl"
KSEF_TEST_API_URL = "https://api-test.ksef.mf.gov.pl"

# RSA-OAEP encryption timeout and retry settings
AUTH_STATUS_POLL_INTERVAL = 1.0  # seconds
AUTH_STATUS_MAX_POLLS = 300  # ~5 minutes total


class KSeFAuthError(Exception):
    """Raised when authentication with the KSeF API fails."""

    pass


class KSeFAPIError(Exception):
    """Raised when a KSeF API call returns an unexpected response."""

    pass


class KSeFClient:
    """KSeF REST API client using token-based authentication (API v2).

    Supports KSeF token authentication with RSA-OAEP encryption.
    """

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
        self.access_token: Optional[str] = None
        self._public_key: Optional[Any] = None

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

    def _get_public_key(self) -> Any:
        """Retrieve KSeF RSA public key for token encryption.

        Returns:
            Public key object from cryptography library.

        Raises:
            KSeFAPIError: If retrieval fails.
        """
        if self._public_key:
            return self._public_key

        # Query /v2/security/public-key-certificates
        response = self._request("GET", "/v2/security/public-key-certificates")
        if not isinstance(response, list) or not response:
            raise KSeFAPIError("No certificates in public key response")

        # Find the certificate for KsefTokenEncryption (for token auth)
        cert_b64 = None
        for cert_obj in response:
            if "KsefTokenEncryption" in cert_obj.get("usage", []):
                cert_b64 = cert_obj.get("certificate", "")
                break

        if not cert_b64:
            raise KSeFAPIError("No KsefTokenEncryption certificate found in response")

        # Decode Base64 DER to bytes and load certificate
        try:
            cert_der = base64.b64decode(cert_b64)
            cert_data = load_der_x509_certificate(cert_der)
            self._public_key = cert_data.public_key()
            return self._public_key
        except Exception as exc:
            raise KSeFAPIError(f"Failed to load certificate: {exc}") from exc

    def _encrypt_token(self, challenge_timestamp_ms: int) -> str:
        """Encrypt token with challenge timestamp using RSA-OAEP.

        Args:
            challenge_timestamp_ms: Challenge timestamp in milliseconds from API.

        Returns:
            Base64-encoded encrypted token.

        Raises:
            KSeFAPIError: If encryption fails.
        """
        try:
            public_key = self._get_public_key()
            token_with_timestamp = f"{self.token}|{challenge_timestamp_ms}"
            plaintext = token_with_timestamp.encode("utf-8")

            ciphertext = public_key.encrypt(
                plaintext,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )
            return base64.b64encode(ciphertext).decode("utf-8")
        except Exception as exc:
            raise KSeFAPIError(f"Token encryption failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate(self) -> None:
        """Authenticate using KSeF token with RSA-OAEP encryption.

        Performs the following steps:
        1. Request auth challenge (POST /auth/challenge)
        2. Encrypt token with challenge timestamp (RSA-OAEP)
        3. Submit encrypted token (POST /auth/ksef-token)
        4. Poll authentication status (GET /auth/{referenceNumber})
        5. Redeem authentication token (POST /auth/token/redeem)

        On success :attr:`access_token` is populated.

        Raises:
            KSeFAuthError: When authentication fails.
            KSeFAPIError: On any HTTP/network error.
        """
        # Step 1 – Request auth challenge
        challenge_resp = self._request(
            "POST",
            "/v2/auth/challenge",
            {"contextIdentifier": {"type": "Nip", "value": self.nip}},
        )

        challenge: str = challenge_resp.get("challenge", "")
        timestamp_ms: int = challenge_resp.get("timestampMs", 0)

        if not challenge or not timestamp_ms:
            raise KSeFAuthError(
                f"Invalid challenge response: challenge={challenge!r}, "
                f"timestampMs={timestamp_ms!r}"
            )

        # Step 2 & 3 – Encrypt token and submit authentication request
        encrypted_token = self._encrypt_token(timestamp_ms)
        auth_req = {
            "challenge": challenge,
            "contextIdentifier": {"type": "Nip", "value": self.nip},
            "encryptedToken": encrypted_token,
        }
        auth_resp = self._request("POST", "/v2/auth/ksef-token", auth_req)

        reference_number: str = auth_resp.get("referenceNumber", "")
        auth_token: str = (auth_resp.get("authenticationToken") or {}).get("token", "")

        if not reference_number or not auth_token:
            raise KSeFAuthError(
                f"Invalid auth response: referenceNumber={reference_number!r}, "
                f"authenticationToken={auth_token!r}"
            )

        # Step 4 – Poll authentication status until complete
        self._wait_for_auth_completion(reference_number, auth_token)

        # Step 5 – Redeem authentication token for access token
        redeem_resp = self._request(
            "POST",
            "/v2/auth/token/redeem",
            {},
            extra_headers={"Authorization": f"Bearer {auth_token}"},
        )

        access_token: str = redeem_resp.get("accessToken", {}).get("token", "")
        if not access_token:
            raise KSeFAuthError(
                "Access token not found in redeem response: "
                + json.dumps(redeem_resp, ensure_ascii=False)
            )

        self.access_token = access_token

    def _wait_for_auth_completion(self, reference_number: str, auth_token: str) -> None:
        """Poll authentication status until completion or timeout.

        Args:
            reference_number: Reference number from auth request.
            auth_token: Temporary authentication token (Bearer).

        Raises:
            KSeFAuthError: If authentication fails or times out.
        """
        for poll_count in range(AUTH_STATUS_MAX_POLLS):
            try:
                status_resp = self._request(
                    "GET",
                    f"/v2/auth/{reference_number}",
                    extra_headers={"Authorization": f"Bearer {auth_token}"},
                )
            except KSeFAPIError as exc:
                # If we get HTTP error during polling, wait and retry
                if poll_count < AUTH_STATUS_MAX_POLLS - 1:
                    time.sleep(AUTH_STATUS_POLL_INTERVAL)
                    continue
                raise KSeFAuthError(f"Authentication status check failed: {exc}") from exc

            # Check for success via status.code
            status_obj = status_resp.get("status", {})
            status_code = status_obj.get("code", 0)

            # Success (status code 200)
            if status_code == 200:
                return

            # Still processing (status code 100)
            if status_code == 100:
                time.sleep(AUTH_STATUS_POLL_INTERVAL)
                continue

            # Error
            raise KSeFAuthError(
                f"Authentication failed with status code {status_code}: "
                + json.dumps(status_resp, ensure_ascii=False)
            )

        raise KSeFAuthError("Authentication status polling timeout (5 minutes)")

    # ------------------------------------------------------------------
    # Invoice listing
    # ------------------------------------------------------------------

    def list_invoices(
        self,
        date_from: str,
        date_to: str,
        *,
        subject_type: str = "Subject1",
        invoicing_mode: str = "Online",
        form_type: str = "FA",
        page_offset: int = 0,
        page_size: int = 100,
    ) -> List[Dict[str, Any]]:
        """Return a list of invoices from the KSeF API.

        Authenticates automatically if no access token is present.

        Args:
            date_from: Start of the date range in ISO-8601 format
                (e.g. ``"2023-01-01T00:00:00.000Z"``).
            date_to: End of the date range in ISO-8601 format
                (e.g. ``"2023-12-31T23:59:59.999Z"``).
            subject_type: Entity type for filtering (default ``"Subject1"`` = seller).
                Options: ``"Subject1"`` (seller), ``"Subject2"`` (buyer),
                ``"Subject3"``, ``"SubjectAuthorized"``.
            invoicing_mode: Invoicing mode (default ``"Online"``).
                Examples: ``"Online"``, ``"Offline"``.
            form_type: Invoice form type (default ``"FA"``).
                Examples: ``"FA"`` (FA-3), ``"FVAt"``, ``"RO"``, ``"ZO"``.
            page_offset: Zero-based page offset (default ``0``).
            page_size: Number of results per page (default ``100``).

        Returns:
            List of invoice metadata dictionaries.

        Raises:
            KSeFAuthError: If authentication fails.
            KSeFAPIError: On any HTTP/network error.
        """
        if not self.access_token:
            self.authenticate()

        # Build request body with required fields
        request_body: Dict[str, Any] = {
            "subjectType": subject_type,
            "pageOffset": page_offset,
            "pageSize": page_size,
            "dateRange": {
                "dateType": "PermanentStorage",
                "from": date_from,
                "to": date_to,
            },
        }

        # Add optional filters only if specified
        if invoicing_mode:
            request_body["invoicingMode"] = invoicing_mode
        if form_type:
            request_body["formType"] = form_type

        response = self._request(
            "POST",
            "/v2/invoices/query/metadata",
            request_body,
            extra_headers={"Authorization": f"Bearer {self.access_token}"},
        )

        return response.get("invoiceMetadata", [])
