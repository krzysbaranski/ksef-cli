# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ksef-cli** is a Python CLI tool for the KSeF (Krajowy System e-Faktur) — Poland's National Electronic Invoice System. It generates invoices in FA (3) format and provides token-based authentication with the KSeF API v2.

- **Python**: 3.13+
- **Package manager**: Poetry
- **Key dependencies**: Click (CLI), Pydantic (validation), cryptography (RSA-OAEP), lxml (XML), ReportLab (PDF)

## Available Commands

| Command | Purpose |
|---------|---------|
| `list-invoices` | Query invoices from KSeF API with filters |
| `get-invoice` | Download specific invoice XML by KSeF number |
| `interactive` | Generate invoice interactively (prompt-based) |
| `validate` | Validate invoice XML format |
| `visualize` | Convert invoice XML to PDF |

## Common Development Commands

```bash
# Install dependencies and package in development mode
poetry install

# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_ksef_api.py -v

# Run single test
poetry run pytest tests/test_ksef_api.py::TestKSeFClientInit::test_default_uses_production_url -v

# Format code (Black)
poetry run black ksef_cli/ tests/

# Lint code (Flake8)
poetry run flake8 ksef_cli/ tests/

# Sort imports (isort)
poetry run isort ksef_cli/ tests/

# Type checking (mypy)
poetry run mypy ksef_cli/

# Security scanning
poetry run bandit -r ksef_cli/

# Run the CLI locally
poetry run ksef-cli --help
poetry run ksef-cli list-invoices --help
poetry run ksef-cli get-invoice --help
```

## Architecture

### Authentication Flow (KSeF API v2)

Token-based authentication with RSA-OAEP encryption:

1. **POST /v2/auth/challenge** — Request authentication challenge
   - Input: `{"contextIdentifier": {"type": "Nip", "value": nip}}`
   - Returns: `challenge` and `timestampMs`

2. **GET /v2/security/public-key-certificates** — Fetch RSA public key
   - Retrieves array of certificates with `KsefTokenEncryption` usage type
   - Certificates are Base64-encoded DER format

3. **Encrypt token** — RSA-OAEP with SHA-256
   - Plaintext: `{token}|{timestampMs}`
   - Ciphertext returned as Base64

4. **POST /v2/auth/ksef-token** — Submit encrypted token
   - Input: `{"challenge": ..., "contextIdentifier": {"type": "Nip", "value": nip}, "encryptedToken": ...}`
   - Returns: `referenceNumber` and temporary `authenticationToken`

5. **GET /v2/auth/{referenceNumber}** — Poll authentication status
   - Returns `status.code`: 200 = success, 100 = still processing
   - Polls with 1-second intervals, max 5 minutes

6. **POST /v2/auth/token/redeem** — Redeem for JWT access token
   - Sends temporary authentication token as Bearer
   - Returns JWT `accessToken` for subsequent API calls

### Invoice Query

**POST /v2/invoices/query/metadata** — Query invoices with JWT access token

Required filters:
- `subjectType`: "Subject1" (seller), "Subject2" (buyer), "Subject3", "SubjectAuthorized"
- `dateRange.dateType`: "PermanentStorage" (date type for filtering)
- `dateRange.from/to`: ISO-8601 timestamps

Optional filters (all configurable via CLI):
- `invoicingMode`: "Online", "Offline", etc.
- `formType`: "FA", "FVAt", "RO", "ZO", etc.
- `amount`: `{"type": "Netto|Brutto", "from": float, "to": float}`
- `currencyCodes`: List of currency codes (e.g., ["PLN", "EUR"])
- `invoiceTypes`: List of invoice types (e.g., ["Vat"])
- `hasAttachment`: Boolean

### Get Single Invoice

**GET /v2/invoices/ksef/{ksefNumber}** — Retrieve specific invoice by KSeF number (XML)

- Path parameter: `ksefNumber` (35-36 characters)
- Returns: Full invoice XML document (application/xml content-type)
- Response header: `x-ms-meta-hash` contains SHA-256 hash of invoice (Base64)
- Error codes:
  - 21164: Invoice not found
  - 21165: Invoice processed but not yet available
  - 21405: Input validation error

**Rate limit**: 20 requests per hour per token

### Code Structure

**ksef_cli/ksef_api.py** — KSeF API client
- `KSeFClient` class: Main client with authentication and invoice operations
- `_request()`: Low-level HTTP request handler (uses urllib)
- `_get_public_key()`: Fetches and caches RSA public key
- `_encrypt_token()`: RSA-OAEP encryption with MGF1-SHA256
- `authenticate()`: Full 6-step auth flow
- `_wait_for_auth_completion()`: Polling with exponential backoff
- `list_invoices()`: Query invoices with configurable filters
- `get_invoice()`: Retrieve specific invoice by KSeF number

**ksef_cli/cli.py** — Click CLI commands
- `list-invoices`: Query invoices with filters
  - Required: `-n/--nip`, `-t/--token`, `--date-from`, `--date-to`
  - Optional filters: `--subject-type` (default "Subject1"), `--date-type` (default "PermanentStorage"), `--invoicing-mode`, `--form-type`, `--amount-type`, `--amount-from`, `--amount-to`, `--currency` (multiple), `--invoice-type` (multiple), `--has-attachment`
  - Pagination: `--page-offset` (default 0), `--page-size` (default 100)
  - Debug: `--debug` flag prints HTTP method, URL, request body, and response JSON to stderr
  - Environment: `--test` flag uses test API (https://api-test.ksef.mf.gov.pl)
  - Output: `-o/--output` for file output, stdout default (JSON format)
- `get-invoice`: Retrieve specific invoice by KSeF number
  - Required: `-n/--nip`, `-t/--token`, `-k/--ksef-number`
  - Environment: `--test` flag uses test API
  - Debug: `--debug` flag enables debug output to stderr
  - Output: `-o/--output` for file output, stdout default (JSON format)

**tests/test_ksef_api.py** — Unit tests (36 tests)
- Tests for `_request()`, authentication flow, invoice listing, invoice retrieval
- Uses mocking for HTTP requests and certificate handling
- Fixtures for challenge, auth, and redeem responses
- Test classes: TestKSeFClientInit, TestKSeFClientRequest, TestKSeFClientAuthenticate, TestKSeFClientListInvoices, TestKSeFClientGetInvoice, TestListInvoicesCLI, TestGetInvoiceCLI

## Key Technical Notes

### Context Identifier Format
- **Field names**: `type` and `value` (not `type` and `identifier`)
- **Type value**: "Nip" (uppercase, not "onip")
- **Value**: 10-digit Polish NIP number

### Status Polling
- Success is `status.code == 200`, not `processingCode == "0"`
- Response includes full authentication metadata and `isTokenRedeemed` flag

### Optional Filters
- `invoicingMode` and `formType` default to None in API (not hardcoded to "Online"/"FA")
- Only include optional filters in request if explicitly specified
- Amount filter requires both `type` and at least one of `from`/`to`

### Certificate Handling
- API returns array of certificate objects directly (not wrapped in `{"certificates": []}`)
- Look for certificate with `"KsefTokenEncryption"` in `usage` array
- Certificate is Base64-encoded DER (not PEM) — decode with `base64.b64decode()` then use `load_der_x509_certificate()`

### Debug Mode
- CLI flag `--debug` enables debug output to stderr
- Prints HTTP method, full URL, request body (if any), extra headers, and JSON response
- Useful for troubleshooting API issues and verifying correct request format

### Testing
- Tests mock `_encrypt_token()` since real DER certificates can't be easily generated in fixtures
- Tests use `patch.object(client, "_request")` to mock API responses
- All 36 tests must pass before pushing changes

## Environment Setup

For development with real KSeF API:
- Token: Generate from https://ap.ksef.mf.gov.pl/web/tokens/generate-token (production) or test portal
- Token format: `data....|nip-xxxxxxx|....`
- Use `--test` flag for test environment (https://api-test.ksef.mf.gov.pl)

For testing:
- No real credentials needed; all HTTP calls are mocked
- Fixtures contain sample challenge and auth responses

## Practical Workflows

### Download Invoice from KSeF

```bash
# 1. List invoices from last month
poetry run ksef-cli list-invoices -n 1234567890 -t $TOKEN \
  --date-from "2026-03-01T00:00:00.000Z" \
  --date-to "2026-03-31T23:59:59.999Z" \
  --output faktury_marzec.json

# 2. Take ksefReferenceNumber from JSON, download XML
poetry run ksef-cli get-invoice -n 1234567890 -t $TOKEN \
  -k "123-456-789-10-2026-0000001" \
  -o pobrana_faktura.xml

# 3. Visualize downloaded invoice
poetry run ksef-cli visualize -i pobrana_faktura.xml -o pobrana_faktura.pdf
```

### Filter and Download Specific Invoices

```bash
# High-value VAT invoices only
poetry run ksef-cli list-invoices -n 1234567890 -t $TOKEN \
  --date-from "2026-01-01T00:00:00.000Z" \
  --date-to "2026-12-31T23:59:59.999Z" \
  --subject-type Subject1 \
  --invoice-type Vat \
  --amount-type Brutto \
  --amount-from 1000 \
  --output high_value_invoices.json
```

### Debug Authentication and API Issues

```bash
# Enable debug output to stderr (logging to 2> redirects to file)
poetry run ksef-cli list-invoices -n 1234567890 -t $TOKEN \
  --date-from "2026-01-01T00:00:00.000Z" \
  --date-to "2026-12-31T23:59:59.999Z" \
  --debug 2> debug.log

# Check what's happening at the HTTP level
cat debug.log
```

## Style and Standards

- **Code style**: Black (line length 100), isort (profile: black)
- **Type hints**: Required for public functions
- **Linting**: Flake8
- **Security**: Bandit for security scanning
- **Test coverage**: Minimum 80% (pytest-cov)
