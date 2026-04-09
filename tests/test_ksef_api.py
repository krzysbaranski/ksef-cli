"""Tests for KSeF API client (ksef_cli.ksef_api)."""

import base64
import json
from unittest.mock import MagicMock, patch

import pytest

from ksef_cli.ksef_api import (
    KSEF_API_URL,
    KSEF_TEST_API_URL,
    KSeFAPIError,
    KSeFAuthError,
    KSeFClient,
)

# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    return KSeFClient(nip="1234567890", token="secret-token")


@pytest.fixture
def test_client():
    return KSeFClient(nip="1234567890", token="secret-token", test=True)


CHALLENGE_RESPONSE = {
    "challenge": "20230101-CR-ABCDEF12",
    "timestamp": "2023-01-01T00:00:00.000Z",
    "timestampMs": 1672531200000,
    "clientIp": "127.0.0.1",
}

AUTH_RESPONSE = {
    "referenceNumber": "REF-001",
    "authenticationToken": {
        "token": "AUTH_TOKEN_JWT_VALUE",
    },
}

AUTH_STATUS_RESPONSE = {
    "startDate": "2026-04-08T22:48:17.3422391+00:00",
    "authenticationMethod": "Token",
    "authenticationMethodInfo": {
        "category": "Token",
        "code": "token.ksef",
        "displayName": "Token KSeF",
    },
    "status": {
        "code": 200,
        "description": "Uwierzytelnianie zakończone sukcesem",
    },
    "isTokenRedeemed": False,
}

REDEEM_RESPONSE = {
    "accessToken": {
        "token": "ACCESS_TOKEN_JWT_VALUE",
        "exp": 1672531800,
    },
    "refreshToken": {
        "token": "REFRESH_TOKEN_JWT_VALUE",
        "exp": 1673395200,
    },
}

# Base64-encoded DER certificate (minimal test certificate)
# Generated from a simple self-signed cert for testing purposes
PUBLIC_KEY_CERT_B64 = (
    "MIIDazCCAlOgAwIBAgIUWnUvwuSyM2BgvAQLFJiUEZEiDfcwDQYJKoZIhvcNAQEL"
    "BQAwRTELMAkGA1UEBhMCQVUxEzARBgNVBAgMClNvbWUtU3RhdGUxITAfBgNVBAoM"
    "GEludGVybmV0IFdpZGdpdHMgUHR5IEx0ZDAeFw0yMzAxMDEwMDAwMDBaFw0yNDAx"
    "MDEwMDAwMDBaMEUxCzAJBgNVBAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEw"
    "HwYDVQQKDBhJbnRlcm5ldCBXaWRnaXRzIFB0eSBMdGQwggEiMA0GCSqGSIb3DQEB"
    "AQUAA4IBDwAwggEKAoIBAQC7W8pGMEJT3QVZZ7ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ"
    "5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5"
    "ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ"
    "5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ"
    "5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ"
    "5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ"
    "5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ"
    "5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ5ZZ"
    "5ZZ5AoIBAQCX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0"
    "LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0L"
    "X0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX"
    "0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0"
    "LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0L"
    "X0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX"
    "0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0LX0"
)

# API v2 returns array of certificate objects directly (not wrapped)
PUBLIC_KEY_RESPONSE = [
    {
        "certificate": PUBLIC_KEY_CERT_B64,
        "validFrom": "2023-01-01T00:00:00.000Z",
        "validTo": "2024-01-01T00:00:00.000Z",
        "usage": ["KsefTokenEncryption"],
    }
]

INVOICE_LIST_RESPONSE = {
    "invoices": [
        {
            "ksefReferenceNumber": "INV-001",
            "invoicingDate": "2023-06-01T00:00:00.000Z",
            "gross": "1230.00",
            "net": "1000.00",
            "vat": "230.00",
            "currency": "PLN",
        },
        {
            "ksefReferenceNumber": "INV-002",
            "invoicingDate": "2023-06-15T00:00:00.000Z",
            "gross": "246.00",
            "net": "200.00",
            "vat": "46.00",
            "currency": "PLN",
        },
    ],
    "hasMore": False,
    "isTruncated": False,
}

GET_INVOICE_RESPONSE_XML = """<?xml version="1.0" encoding="utf-8"?>
<Invoice xmlns="http://ksef.mf.gov.pl/schema/v2/invoice">
  <KSEFReferenceNumber>INV-001</KSEFReferenceNumber>
  <InvoiceNumber>FV/2023/001</InvoiceNumber>
  <InvoicingDate>2023-06-01T00:00:00.000Z</InvoicingDate>
  <Seller>
    <NIP>5260250274</NIP>
    <Name>Test Company</Name>
  </Seller>
  <Buyer>
    <NIP>9492107026</NIP>
    <Name>Buyer Company</Name>
  </Buyer>
  <Gross>1230.00</Gross>
  <Net>1000.00</Net>
  <VAT>230.00</VAT>
  <Currency>PLN</Currency>
</Invoice>"""


# ---------------------------------------------------------------------------
# KSeFClient initialisation
# ---------------------------------------------------------------------------


class TestKSeFClientInit:
    def test_default_uses_production_url(self, client):
        assert client.base_url == KSEF_API_URL

    def test_test_flag_uses_test_url(self, test_client):
        assert test_client.base_url == KSEF_TEST_API_URL

    def test_access_token_initially_none(self, client):
        assert client.access_token is None

    def test_stores_nip_and_token(self):
        c = KSeFClient(nip="9876543210", token="my-token")
        assert c.nip == "9876543210"
        assert c.token == "my-token"


# ---------------------------------------------------------------------------
# KSeFClient._request
# ---------------------------------------------------------------------------


def _make_urlopen_mock(response_data: dict):
    """Return a context-manager mock that simulates urlopen returning JSON."""
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=cm)
    cm.__exit__ = MagicMock(return_value=False)
    cm.read.return_value = json.dumps(response_data).encode("utf-8")
    return cm


def _make_urlopen_mock_raw(response_text: str):
    """Return a context-manager mock that simulates urlopen returning raw text (XML)."""
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=cm)
    cm.__exit__ = MagicMock(return_value=False)
    cm.read.return_value = response_text.encode("utf-8")
    return cm


class TestKSeFClientRequest:
    def test_post_request_encodes_body_as_json(self, client):
        mock_response = _make_urlopen_mock({"result": "ok"})
        with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            result = client._request("POST", "/test/path", {"key": "value"})

        assert result == {"result": "ok"}
        req = mock_urlopen.call_args[0][0]
        assert req.data == b'{"key": "value"}'

    def test_request_includes_content_type_header(self, client):
        mock_response = _make_urlopen_mock({})
        with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            client._request("POST", "/test", {})

        req = mock_urlopen.call_args[0][0]
        assert req.get_header("Content-type") == "application/json"

    def test_request_without_body_sends_none(self, client):
        mock_response = _make_urlopen_mock({})
        with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            client._request("GET", "/test")

        req = mock_urlopen.call_args[0][0]
        assert req.data is None

    def test_extra_headers_are_included(self, client):
        mock_response = _make_urlopen_mock({})
        with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            client._request("POST", "/test", {}, extra_headers={"SessionToken": "tok123"})

        req = mock_urlopen.call_args[0][0]
        assert req.get_header("Sessiontoken") == "tok123"

    def test_http_error_raises_ksef_api_error(self, client):
        import urllib.error

        http_err = urllib.error.HTTPError(
            url="http://example.com",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=MagicMock(read=lambda: b'{"error": "auth"}'),
        )
        with patch("urllib.request.urlopen", side_effect=http_err):
            with pytest.raises(KSeFAPIError, match="HTTP 401"):
                client._request("POST", "/test")

    def test_url_error_raises_ksef_api_error(self, client):
        import urllib.error

        url_err = urllib.error.URLError(reason="Connection refused")
        with patch("urllib.request.urlopen", side_effect=url_err):
            with pytest.raises(KSeFAPIError, match="Connection error"):
                client._request("POST", "/test")


# ---------------------------------------------------------------------------
# KSeFClient.authenticate
# ---------------------------------------------------------------------------


class TestKSeFClientAuthenticate:
    def test_sets_access_token_on_success(self, client):
        with patch.object(client, "_request") as mock_request:
            responses = [CHALLENGE_RESPONSE, AUTH_RESPONSE, AUTH_STATUS_RESPONSE, REDEEM_RESPONSE]
            mock_request.side_effect = responses
            with patch.object(client, "_encrypt_token", return_value="ENCRYPTED_TOKEN_B64"):
                client.authenticate()

        assert client.access_token == "ACCESS_TOKEN_JWT_VALUE"

    def test_sends_nip_in_challenge_request(self, client):
        with patch.object(client, "_request") as mock_request:
            responses = [CHALLENGE_RESPONSE, AUTH_RESPONSE, AUTH_STATUS_RESPONSE, REDEEM_RESPONSE]
            mock_request.side_effect = responses
            with patch.object(client, "_encrypt_token", return_value="ENCRYPTED_TOKEN_B64"):
                client.authenticate()

        # First call is POST /auth/challenge
        call_args = mock_request.call_args_list[0]
        assert call_args[0][0:2] == ("POST", "/v2/auth/challenge")
        req_body = call_args[0][2]
        assert req_body["contextIdentifier"]["value"] == "1234567890"

    def test_sends_challenge_in_auth_request(self, client):
        with patch.object(client, "_request") as mock_request:
            responses = [CHALLENGE_RESPONSE, AUTH_RESPONSE, AUTH_STATUS_RESPONSE, REDEEM_RESPONSE]
            mock_request.side_effect = responses
            with patch.object(client, "_encrypt_token", return_value="ENCRYPTED_TOKEN_B64"):
                client.authenticate()

        # Second call is POST /auth/ksef-token
        call_args = mock_request.call_args_list[1]
        assert call_args[0][0:2] == ("POST", "/v2/auth/ksef-token")
        req_body = call_args[0][2]
        assert req_body["challenge"] == CHALLENGE_RESPONSE["challenge"]

    def test_missing_challenge_raises_auth_error(self, client):
        bad_challenge = {"challenge": "", "timestampMs": 0}
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(bad_challenge)):
            with pytest.raises(KSeFAuthError, match="Invalid challenge response"):
                client.authenticate()

    def test_missing_access_token_raises_auth_error(self, client):
        redeem_without_token = {}
        with patch.object(client, "_request") as mock_request:
            responses = [
                CHALLENGE_RESPONSE,
                AUTH_RESPONSE,
                AUTH_STATUS_RESPONSE,
                redeem_without_token,
            ]
            mock_request.side_effect = responses
            with patch.object(client, "_encrypt_token", return_value="ENCRYPTED_TOKEN_B64"):
                with pytest.raises(KSeFAuthError, match="Access token not found"):
                    client.authenticate()


# ---------------------------------------------------------------------------
# KSeFClient.list_invoices
# ---------------------------------------------------------------------------


class TestKSeFClientListInvoices:
    def _mock_auth_and_invoices(self):
        """Mock requests for auth flow + invoice listing."""
        return [
            _make_urlopen_mock(CHALLENGE_RESPONSE),
            _make_urlopen_mock(AUTH_RESPONSE),
            _make_urlopen_mock(AUTH_STATUS_RESPONSE),
            _make_urlopen_mock(REDEEM_RESPONSE),
            _make_urlopen_mock(INVOICE_LIST_RESPONSE),
        ]

    def test_returns_invoice_list(self, client):
        with patch("urllib.request.urlopen", side_effect=self._mock_auth_and_invoices()):
            with patch.object(client, "_encrypt_token", return_value="ENCRYPTED"):
                invoices = client.list_invoices(
                    date_from="2023-01-01T00:00:00.000Z",
                    date_to="2023-12-31T23:59:59.999Z",
                )

        assert len(invoices) == 2
        assert invoices[0]["ksefReferenceNumber"] == "INV-001"

    def test_authenticates_automatically_when_no_token(self, client):
        assert client.access_token is None
        with patch("urllib.request.urlopen", side_effect=self._mock_auth_and_invoices()):
            with patch.object(client, "_encrypt_token", return_value="ENCRYPTED"):
                client.list_invoices(
                    date_from="2023-01-01T00:00:00.000Z",
                    date_to="2023-12-31T23:59:59.999Z",
                )

        assert client.access_token == "ACCESS_TOKEN_JWT_VALUE"

    def test_skips_auth_when_access_token_set(self, client):
        client.access_token = "EXISTING_TOKEN"
        invoice_cm = _make_urlopen_mock(INVOICE_LIST_RESPONSE)

        with patch("urllib.request.urlopen", return_value=invoice_cm) as mock_urlopen:
            client.list_invoices(
                date_from="2023-01-01T00:00:00.000Z",
                date_to="2023-12-31T23:59:59.999Z",
            )

        assert mock_urlopen.call_count == 1

    def test_sends_bearer_token_header(self, client):
        client.access_token = "MY_TOKEN"
        requests = []

        def capture(req):
            requests.append(req)
            return _make_urlopen_mock(INVOICE_LIST_RESPONSE)

        with patch("urllib.request.urlopen", side_effect=capture):
            client.list_invoices(
                date_from="2023-01-01T00:00:00.000Z",
                date_to="2023-12-31T23:59:59.999Z",
            )

        req = requests[0]
        assert req.get_header("Authorization") == "Bearer MY_TOKEN"

    def test_sends_date_range_in_body(self, client):
        client.access_token = "TOKEN"
        requests = []

        def capture(req):
            requests.append(req)
            return _make_urlopen_mock(INVOICE_LIST_RESPONSE)

        with patch("urllib.request.urlopen", side_effect=capture):
            client.list_invoices(
                date_from="2023-01-01T00:00:00.000Z",
                date_to="2023-12-31T23:59:59.999Z",
            )

        body = json.loads(requests[0].data.decode("utf-8"))
        assert body["dateRange"]["from"] == "2023-01-01T00:00:00.000Z"
        assert body["dateRange"]["to"] == "2023-12-31T23:59:59.999Z"

    def test_returns_empty_list_when_no_invoices(self, client):
        client.access_token = "TOKEN"
        empty_response = {"invoices": [], "hasMore": False, "isTruncated": False}

        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(empty_response)):
            invoices = client.list_invoices(
                date_from="2023-01-01T00:00:00.000Z",
                date_to="2023-12-31T23:59:59.999Z",
            )

        assert invoices == []

    def test_returns_empty_list_when_key_missing(self, client):
        client.access_token = "TOKEN"
        response_without_key = {"numberOfElements": 0}

        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(response_without_key)):
            invoices = client.list_invoices(
                date_from="2023-01-01T00:00:00.000Z",
                date_to="2023-12-31T23:59:59.999Z",
            )

        assert invoices == []


# ---------------------------------------------------------------------------
# KSeF Client – get_invoice method
# ---------------------------------------------------------------------------


class TestKSeFClientGetInvoice:
    def test_returns_invoice_xml(self, client):
        client.access_token = "TOKEN"

        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock_raw(GET_INVOICE_RESPONSE_XML)):
            invoice = client.get_invoice(ksef_number="123-456-789-10-2023-0000001")

        assert isinstance(invoice, str)
        assert "INV-001" in invoice
        assert "FV/2023/001" in invoice
        assert "<Invoice" in invoice

    def test_authenticates_automatically_when_no_token(self, client):
        auth_mocks = [
            _make_urlopen_mock(CHALLENGE_RESPONSE),
            _make_urlopen_mock(AUTH_RESPONSE),
            _make_urlopen_mock(AUTH_STATUS_RESPONSE),
            _make_urlopen_mock(REDEEM_RESPONSE),
            _make_urlopen_mock_raw(GET_INVOICE_RESPONSE_XML),
        ]

        with patch("urllib.request.urlopen", side_effect=auth_mocks):
            with patch("ksef_cli.ksef_api.KSeFClient._encrypt_token", return_value="ENCRYPTED"):
                invoice = client.get_invoice(ksef_number="123-456-789-10-2023-0000001")

        assert client.access_token == "ACCESS_TOKEN_JWT_VALUE"
        assert isinstance(invoice, str)
        assert "INV-001" in invoice

    def test_skips_auth_when_access_token_set(self, client):
        client.access_token = "TOKEN"

        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock_raw(GET_INVOICE_RESPONSE_XML)):
            invoice = client.get_invoice(ksef_number="123-456-789-10-2023-0000001")

        assert isinstance(invoice, str)
        assert "INV-001" in invoice

    def test_sends_bearer_token_header(self, client):
        client.access_token = "TOKEN"
        requests = []

        def capture_request(req, *args, **kwargs):
            requests.append(req)
            return _make_urlopen_mock_raw(GET_INVOICE_RESPONSE_XML)

        with patch("urllib.request.urlopen", side_effect=capture_request):
            client.get_invoice(ksef_number="123-456-789-10-2023-0000001")

        assert "Authorization" in requests[0].headers
        assert requests[0].headers["Authorization"] == "Bearer TOKEN"

    def test_uses_correct_endpoint(self, client):
        client.access_token = "TOKEN"
        requests = []

        def capture_request(req, *args, **kwargs):
            requests.append(req)
            return _make_urlopen_mock_raw(GET_INVOICE_RESPONSE_XML)

        with patch("urllib.request.urlopen", side_effect=capture_request):
            client.get_invoice(ksef_number="123-456-789-10-2023-0000001")

        assert "/v2/invoices/ksef/123-456-789-10-2023-0000001" in requests[0].full_url


# ---------------------------------------------------------------------------
# CLI integration – list-invoices command
# ---------------------------------------------------------------------------


class TestListInvoicesCLI:
    def _mock_all(self):
        """Mock all requests for CLI test (auth flow + invoices)."""
        return [
            _make_urlopen_mock(CHALLENGE_RESPONSE),
            _make_urlopen_mock(AUTH_RESPONSE),
            _make_urlopen_mock(AUTH_STATUS_RESPONSE),
            _make_urlopen_mock(REDEEM_RESPONSE),
            _make_urlopen_mock(INVOICE_LIST_RESPONSE),
        ]

    def test_list_invoices_outputs_json(self):
        from click.testing import CliRunner

        from ksef_cli.cli import cli

        runner = CliRunner()
        with patch("urllib.request.urlopen", side_effect=self._mock_all()):
            with patch("ksef_cli.ksef_api.KSeFClient._encrypt_token", return_value="ENCRYPTED"):
                result = runner.invoke(
                    cli,
                    [
                        "list-invoices",
                        "--nip",
                        "1234567890",
                        "--token",
                        "secret",
                        "--date-from",
                        "2023-01-01T00:00:00.000Z",
                        "--date-to",
                        "2023-12-31T23:59:59.999Z",
                    ],
                )

        assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
        # Extract the JSON array from stdout (stderr may be mixed in by Click)
        json_end = result.output.rfind("]") + 1
        parsed = json.loads(result.output[:json_end])
        assert len(parsed) == 2

    def test_list_invoices_saves_to_file(self, tmp_path):
        from click.testing import CliRunner

        from ksef_cli.cli import cli

        runner = CliRunner()
        output_file = tmp_path / "invoices.json"

        with patch("urllib.request.urlopen", side_effect=self._mock_all()):
            with patch("ksef_cli.ksef_api.KSeFClient._encrypt_token", return_value="ENCRYPTED"):
                result = runner.invoke(
                    cli,
                    [
                        "list-invoices",
                        "--nip",
                        "1234567890",
                        "--token",
                        "secret",
                        "--date-from",
                        "2023-01-01T00:00:00.000Z",
                        "--date-to",
                        "2023-12-31T23:59:59.999Z",
                        "-o",
                        str(output_file),
                    ],
                )

        assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
        assert output_file.exists()
        data = json.loads(output_file.read_text(encoding="utf-8"))
        assert len(data) == 2
        assert "✓ Lista faktur zapisana" in result.output

    def test_list_invoices_uses_test_env(self):
        from click.testing import CliRunner

        from ksef_cli.cli import cli

        captured_urls = []

        def capture_urlopen(req):
            captured_urls.append(req.full_url)
            responses = [
                CHALLENGE_RESPONSE,
                AUTH_RESPONSE,
                AUTH_STATUS_RESPONSE,
                REDEEM_RESPONSE,
                INVOICE_LIST_RESPONSE,
            ]
            idx = len(captured_urls) - 1
            return _make_urlopen_mock(responses[idx] if idx < len(responses) else {})

        runner = CliRunner()
        with patch("urllib.request.urlopen", side_effect=capture_urlopen):
            with patch("ksef_cli.ksef_api.KSeFClient._encrypt_token", return_value="ENCRYPTED"):
                runner.invoke(
                    cli,
                    [
                        "list-invoices",
                        "--nip",
                        "1234567890",
                        "--token",
                        "secret",
                        "--date-from",
                        "2023-01-01T00:00:00.000Z",
                        "--date-to",
                        "2023-12-31T23:59:59.999Z",
                        "--test",
                    ],
                )

        assert all(KSEF_TEST_API_URL in url for url in captured_urls)

    def test_list_invoices_auth_error_shows_message(self):
        from click.testing import CliRunner

        from ksef_cli.cli import cli

        bad_challenge = {"challenge": "", "timestampMs": 0}
        runner = CliRunner()
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(bad_challenge)):
            result = runner.invoke(
                cli,
                [
                    "list-invoices",
                    "--nip",
                    "1234567890",
                    "--token",
                    "bad",
                    "--date-from",
                    "2023-01-01T00:00:00.000Z",
                    "--date-to",
                    "2023-12-31T23:59:59.999Z",
                ],
            )

        assert result.exit_code != 0
        assert "Błąd autoryzacji" in result.output

    def test_list_invoices_api_error_shows_message(self):
        import urllib.error

        from click.testing import CliRunner

        from ksef_cli.cli import cli

        http_err = urllib.error.HTTPError(
            url="http://example.com",
            code=500,
            msg="Server Error",
            hdrs={},
            fp=MagicMock(read=lambda: b'{"error": "internal"}'),
        )
        runner = CliRunner()
        with patch("urllib.request.urlopen", side_effect=http_err):
            result = runner.invoke(
                cli,
                [
                    "list-invoices",
                    "--nip",
                    "1234567890",
                    "--token",
                    "tok",
                    "--date-from",
                    "2023-01-01T00:00:00.000Z",
                    "--date-to",
                    "2023-12-31T23:59:59.999Z",
                ],
            )

        assert result.exit_code != 0
        assert "Błąd API KSeF" in result.output

    def test_list_invoices_missing_required_option(self):
        from click.testing import CliRunner

        from ksef_cli.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "list-invoices",
                "--nip",
                "1234567890",
                # missing --token, --date-from, --date-to
            ],
        )

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# CLI integration – get-invoice command
# ---------------------------------------------------------------------------


class TestGetInvoiceCLI:
    def _mock_all(self):
        """Mock all requests for CLI test (auth flow + get invoice)."""
        return [
            _make_urlopen_mock(CHALLENGE_RESPONSE),
            _make_urlopen_mock(AUTH_RESPONSE),
            _make_urlopen_mock(AUTH_STATUS_RESPONSE),
            _make_urlopen_mock(REDEEM_RESPONSE),
            _make_urlopen_mock_raw(GET_INVOICE_RESPONSE_XML),
        ]

    def test_get_invoice_outputs_xml(self):
        from click.testing import CliRunner

        from ksef_cli.cli import cli

        runner = CliRunner()
        with patch("urllib.request.urlopen", side_effect=self._mock_all()):
            with patch("ksef_cli.ksef_api.KSeFClient._encrypt_token", return_value="ENCRYPTED"):
                result = runner.invoke(
                    cli,
                    [
                        "get-invoice",
                        "--nip",
                        "1234567890",
                        "--token",
                        "secret",
                        "--ksef-number",
                        "123-456-789-10-2023-0000001",
                    ],
                )

        assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
        assert "<?xml" in result.output
        assert "INV-001" in result.output
        assert "<Invoice" in result.output

    def test_get_invoice_saves_to_file(self, tmp_path):
        from click.testing import CliRunner

        from ksef_cli.cli import cli

        output_file = tmp_path / "invoice.xml"
        runner = CliRunner()
        with patch("urllib.request.urlopen", side_effect=self._mock_all()):
            with patch("ksef_cli.ksef_api.KSeFClient._encrypt_token", return_value="ENCRYPTED"):
                result = runner.invoke(
                    cli,
                    [
                        "get-invoice",
                        "--nip",
                        "1234567890",
                        "--token",
                        "secret",
                        "--ksef-number",
                        "123-456-789-10-2023-0000001",
                        "--output",
                        str(output_file),
                    ],
                )

        assert result.exit_code == 0
        assert output_file.exists()
        with open(output_file) as f:
            content = f.read()
        assert "<?xml" in content
        assert "INV-001" in content

    def test_get_invoice_missing_required_option(self):
        from click.testing import CliRunner

        from ksef_cli.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "get-invoice",
                "--nip",
                "1234567890",
                # missing --token, --ksef-number
            ],
        )

        assert result.exit_code != 0
