"""Tests for QR code generator in ksef_cli.qr_generator"""

import base64

import pytest

from ksef_cli.qr_generator import (
    KSEF_VERIFY_BASE_URL,
    generate_qr_code_base64,
    generate_qr_code_png,
    get_verification_url,
)


class TestGetVerificationUrl:
    """Tests for get_verification_url function"""

    def test_returns_correct_url(self):
        """Test that verification URL is correctly formed"""
        numer_ksef = "5260250274-20230215-ABC123456789-AB"
        url = get_verification_url(numer_ksef)
        assert url == f"{KSEF_VERIFY_BASE_URL}/{numer_ksef}"

    def test_url_contains_base_url(self):
        """Test that the URL starts with the KSeF verify base URL"""
        url = get_verification_url("TEST123")
        assert url.startswith("https://ksef.podatki.gov.pl/web/verify/")

    def test_url_contains_ksef_number(self):
        """Test that the URL contains the provided KSeF number"""
        numer_ksef = "9876543210-20240101-XYZ999-CD"
        url = get_verification_url(numer_ksef)
        assert numer_ksef in url

    def test_url_format(self):
        """Test full URL format"""
        numer_ksef = "1234567890-20230101-ABCDEF-GH"
        url = get_verification_url(numer_ksef)
        assert url == f"https://ksef.podatki.gov.pl/web/verify/{numer_ksef}"


class TestGenerateQrCodePng:
    """Tests for generate_qr_code_png function"""

    def test_returns_bytes(self):
        """Test that the function returns bytes"""
        url = "https://ksef.podatki.gov.pl/web/verify/TEST123"
        result = generate_qr_code_png(url)
        assert isinstance(result, bytes)

    def test_returns_valid_png(self):
        """Test that the output is a valid PNG image"""
        url = "https://ksef.podatki.gov.pl/web/verify/TEST123"
        result = generate_qr_code_png(url)
        # PNG files start with a specific magic number
        assert result[:8] == b"\x89PNG\r\n\x1a\n"

    def test_non_empty_output(self):
        """Test that the output is non-empty"""
        url = "https://ksef.podatki.gov.pl/web/verify/TEST123"
        result = generate_qr_code_png(url)
        assert len(result) > 0

    def test_different_urls_different_qr_codes(self):
        """Test that different URLs produce different QR codes"""
        url1 = "https://ksef.podatki.gov.pl/web/verify/NUMBER1"
        url2 = "https://ksef.podatki.gov.pl/web/verify/NUMBER2"
        result1 = generate_qr_code_png(url1)
        result2 = generate_qr_code_png(url2)
        assert result1 != result2

    def test_same_url_same_qr_code(self):
        """Test that same URL produces same QR code"""
        url = "https://ksef.podatki.gov.pl/web/verify/TEST123"
        result1 = generate_qr_code_png(url)
        result2 = generate_qr_code_png(url)
        assert result1 == result2


class TestGenerateQrCodeBase64:
    """Tests for generate_qr_code_base64 function"""

    def test_returns_string(self):
        """Test that the function returns a string"""
        url = "https://ksef.podatki.gov.pl/web/verify/TEST123"
        result = generate_qr_code_base64(url)
        assert isinstance(result, str)

    def test_returns_valid_base64(self):
        """Test that the output is valid base64"""
        url = "https://ksef.podatki.gov.pl/web/verify/TEST123"
        result = generate_qr_code_base64(url)
        # Should not raise an exception
        decoded = base64.b64decode(result)
        assert len(decoded) > 0

    def test_decoded_is_valid_png(self):
        """Test that the decoded base64 is a valid PNG"""
        url = "https://ksef.podatki.gov.pl/web/verify/TEST123"
        result = generate_qr_code_base64(url)
        decoded = base64.b64decode(result)
        assert decoded[:8] == b"\x89PNG\r\n\x1a\n"

    def test_non_empty_output(self):
        """Test that the output is non-empty"""
        url = "https://ksef.podatki.gov.pl/web/verify/TEST123"
        result = generate_qr_code_base64(url)
        assert len(result) > 0


class TestKSeFVerifyBaseUrl:
    """Tests for the KSEF_VERIFY_BASE_URL constant"""

    def test_base_url_is_correct(self):
        """Test that the base URL is the correct KSeF verification URL"""
        assert KSEF_VERIFY_BASE_URL == "https://ksef.podatki.gov.pl/web/verify"

    def test_base_url_uses_https(self):
        """Test that the base URL uses HTTPS"""
        assert KSEF_VERIFY_BASE_URL.startswith("https://")
