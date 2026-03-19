"""Tests for KSeF API client (ksef_cli.ksef_api)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from ksef_cli.ksef_api import (
    KSEF_API_URL,
    KSEF_TEST_API_URL,
    KSeFAPIError,
    KSeFAuthError,
    KSeFClient,
    _sign_token,
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
}

SESSION_RESPONSE = {
    "sessionToken": {
        "token": "SESSION_TOKEN_VALUE",
        "tokenExpiry": "2023-01-01T01:00:00.000Z",
    },
    "referenceNumber": "REF-001",
}

INVOICE_LIST_RESPONSE = {
    "invoiceList": [
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
    "numberOfElements": 2,
    "pageSize": 100,
    "pageOffset": 0,
}


# ---------------------------------------------------------------------------
# _sign_token
# ---------------------------------------------------------------------------


class TestSignToken:
    def test_returns_base64_string(self):
        result = _sign_token("my-token", "2023-01-01T00:00:00.000Z")
        import base64

        # Should be valid base64
        decoded = base64.b64decode(result)
        assert len(decoded) == 32  # SHA-256 digest is 32 bytes

    def test_different_tokens_produce_different_signatures(self):
        sig1 = _sign_token("token-a", "2023-01-01T00:00:00.000Z")
        sig2 = _sign_token("token-b", "2023-01-01T00:00:00.000Z")
        assert sig1 != sig2

    def test_different_timestamps_produce_different_signatures(self):
        sig1 = _sign_token("token", "2023-01-01T00:00:00.000Z")
        sig2 = _sign_token("token", "2023-06-01T00:00:00.000Z")
        assert sig1 != sig2

    def test_same_inputs_produce_same_signature(self):
        sig1 = _sign_token("token", "2023-01-01T00:00:00.000Z")
        sig2 = _sign_token("token", "2023-01-01T00:00:00.000Z")
        assert sig1 == sig2


# ---------------------------------------------------------------------------
# KSeFClient initialisation
# ---------------------------------------------------------------------------


class TestKSeFClientInit:
    def test_default_uses_production_url(self, client):
        assert client.base_url == KSEF_API_URL

    def test_test_flag_uses_test_url(self, test_client):
        assert test_client.base_url == KSEF_TEST_API_URL

    def test_session_token_initially_none(self, client):
        assert client.session_token is None

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
    def _mock_two_requests(self):
        """Return side_effect list simulating challenge then session responses."""
        challenge_cm = _make_urlopen_mock(CHALLENGE_RESPONSE)
        session_cm = _make_urlopen_mock(SESSION_RESPONSE)
        return [challenge_cm, session_cm]

    def test_sets_session_token_on_success(self, client):
        with patch("urllib.request.urlopen", side_effect=self._mock_two_requests()):
            client.authenticate()

        assert client.session_token == "SESSION_TOKEN_VALUE"

    def test_sends_nip_in_challenge_request(self, client):
        requests = []

        def capture_urlopen(req):
            requests.append(req)
            if len(requests) == 1:
                return _make_urlopen_mock(CHALLENGE_RESPONSE)
            return _make_urlopen_mock(SESSION_RESPONSE)

        with patch("urllib.request.urlopen", side_effect=capture_urlopen):
            client.authenticate()

        body = json.loads(requests[0].data.decode("utf-8"))
        assert body["contextIdentifier"]["identifier"] == "1234567890"
        assert body["contextIdentifier"]["type"] == "onip"

    def test_sends_challenge_in_initialised_token_request(self, client):
        requests = []

        def capture_urlopen(req):
            requests.append(req)
            if len(requests) == 1:
                return _make_urlopen_mock(CHALLENGE_RESPONSE)
            return _make_urlopen_mock(SESSION_RESPONSE)

        with patch("urllib.request.urlopen", side_effect=capture_urlopen):
            client.authenticate()

        body = json.loads(requests[1].data.decode("utf-8"))
        assert body["challenge"]["challenge"] == CHALLENGE_RESPONSE["challenge"]

    def test_missing_challenge_raises_auth_error(self, client):
        bad_challenge = {"challenge": "", "timestamp": ""}
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(bad_challenge)):
            with pytest.raises(KSeFAuthError, match="Invalid authorisation challenge"):
                client.authenticate()

    def test_missing_session_token_raises_auth_error(self, client):
        session_without_token = {"sessionToken": {}, "referenceNumber": "REF"}

        side_effects = [
            _make_urlopen_mock(CHALLENGE_RESPONSE),
            _make_urlopen_mock(session_without_token),
        ]
        with patch("urllib.request.urlopen", side_effect=side_effects):
            with pytest.raises(KSeFAuthError, match="Session token not found"):
                client.authenticate()


# ---------------------------------------------------------------------------
# KSeFClient.list_invoices
# ---------------------------------------------------------------------------


class TestKSeFClientListInvoices:
    def _mock_auth_and_invoices(self):
        return [
            _make_urlopen_mock(CHALLENGE_RESPONSE),
            _make_urlopen_mock(SESSION_RESPONSE),
            _make_urlopen_mock(INVOICE_LIST_RESPONSE),
        ]

    def test_returns_invoice_list(self, client):
        with patch("urllib.request.urlopen", side_effect=self._mock_auth_and_invoices()):
            invoices = client.list_invoices(
                date_from="2023-01-01T00:00:00.000Z",
                date_to="2023-12-31T23:59:59.999Z",
            )

        assert len(invoices) == 2
        assert invoices[0]["ksefReferenceNumber"] == "INV-001"

    def test_authenticates_automatically_when_no_session(self, client):
        assert client.session_token is None
        with patch("urllib.request.urlopen", side_effect=self._mock_auth_and_invoices()):
            client.list_invoices(
                date_from="2023-01-01T00:00:00.000Z",
                date_to="2023-12-31T23:59:59.999Z",
            )

        # session token should now be populated
        assert client.session_token == "SESSION_TOKEN_VALUE"

    def test_skips_auth_when_session_already_set(self, client):
        client.session_token = "EXISTING_TOKEN"
        invoice_cm = _make_urlopen_mock(INVOICE_LIST_RESPONSE)

        with patch("urllib.request.urlopen", return_value=invoice_cm) as mock_urlopen:
            client.list_invoices(
                date_from="2023-01-01T00:00:00.000Z",
                date_to="2023-12-31T23:59:59.999Z",
            )

        # Only one request should have been made (no auth)
        assert mock_urlopen.call_count == 1

    def test_sends_session_token_header(self, client):
        client.session_token = "MY_SESSION"
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
        assert req.get_header("Sessiontoken") == "MY_SESSION"

    def test_sends_date_range_in_body(self, client):
        client.session_token = "TOKEN"
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
        assert body["invoiceDate"]["dateFrom"] == "2023-01-01T00:00:00.000Z"
        assert body["invoiceDate"]["dateTo"] == "2023-12-31T23:59:59.999Z"

    def test_returns_empty_list_when_no_invoices(self, client):
        client.session_token = "TOKEN"
        empty_response = {"invoiceList": [], "numberOfElements": 0}

        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(empty_response)):
            invoices = client.list_invoices(
                date_from="2023-01-01T00:00:00.000Z",
                date_to="2023-12-31T23:59:59.999Z",
            )

        assert invoices == []

    def test_returns_empty_list_when_key_missing(self, client):
        client.session_token = "TOKEN"
        response_without_key = {"numberOfElements": 0}

        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(response_without_key)):
            invoices = client.list_invoices(
                date_from="2023-01-01T00:00:00.000Z",
                date_to="2023-12-31T23:59:59.999Z",
            )

        assert invoices == []


# ---------------------------------------------------------------------------
# CLI integration – list-invoices command
# ---------------------------------------------------------------------------


class TestListInvoicesCLI:
    def _mock_all(self):
        return [
            _make_urlopen_mock(CHALLENGE_RESPONSE),
            _make_urlopen_mock(SESSION_RESPONSE),
            _make_urlopen_mock(INVOICE_LIST_RESPONSE),
        ]

    def test_list_invoices_outputs_json(self):
        from click.testing import CliRunner

        from ksef_cli.cli import cli

        runner = CliRunner()
        with patch("urllib.request.urlopen", side_effect=self._mock_all()):
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

        assert result.exit_code == 0
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

        assert result.exit_code == 0
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
            if len(captured_urls) == 1:
                return _make_urlopen_mock(CHALLENGE_RESPONSE)
            if len(captured_urls) == 2:
                return _make_urlopen_mock(SESSION_RESPONSE)
            return _make_urlopen_mock(INVOICE_LIST_RESPONSE)

        runner = CliRunner()
        with patch("urllib.request.urlopen", side_effect=capture_urlopen):
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

        bad_challenge = {"challenge": "", "timestamp": ""}
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
