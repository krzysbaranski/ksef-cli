"""QR code generator for KSeF invoice verification."""

import base64
import io

KSEF_VERIFY_BASE_URL = "https://ksef.podatki.gov.pl/web/verify"


def get_verification_url(numer_ksef: str) -> str:
    """
    Generates the KSeF verification URL for an invoice.

    Args:
        numer_ksef: The KSeF reference number assigned after invoice submission

    Returns:
        The verification URL
    """
    return f"{KSEF_VERIFY_BASE_URL}/{numer_ksef}"


def generate_qr_code_png(url: str) -> bytes:
    """
    Generates a QR code image (PNG) for the given URL.

    Args:
        url: The URL to encode in the QR code

    Returns:
        PNG image as bytes
    """
    import qrcode

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def generate_qr_code_base64(url: str) -> str:
    """
    Generates a base64-encoded QR code PNG for the given URL.

    Args:
        url: The URL to encode in the QR code

    Returns:
        Base64-encoded PNG image string (without data URI prefix)
    """
    png_bytes = generate_qr_code_png(url)
    return base64.b64encode(png_bytes).decode("utf-8")
