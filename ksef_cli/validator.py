"""XML Validator for KSeF invoices using XSD schema."""

import os
from dataclasses import dataclass
from io import BytesIO
from typing import List, Optional, Tuple
from urllib.request import urlopen

from lxml import etree


@dataclass
class ValidationError:
    """Represents a single validation error."""

    line: Optional[int]
    column: Optional[int]
    message: str
    error_type: str  # 'error', 'warning', 'fatal'

    def __str__(self) -> str:
        location = ""
        if self.line is not None:
            location = f"Line {self.line}"
            if self.column is not None:
                location += f", Column {self.column}"
            location += ": "
        return f"[{self.error_type.upper()}] {location}{self.message}"


class KSeFValidator:
    """Validator for KSeF FA-3 invoices using XSD schema."""

    SCHEMA_URL = "http://crd.gov.pl/wzor/2025/06/25/13775/schemat.xsd"
    NAMESPACE = "http://crd.gov.pl/wzor/2025/06/25/13775/"

    def __init__(self, schema_path: Optional[str] = None):
        """
        Initialize the validator.

        Args:
            schema_path: Optional path to local XSD schema file.
                        If not provided, schema will be downloaded from official URL.
        """
        self._schema: Optional[etree.XMLSchema] = None
        self._schema_path = schema_path
        self._schema_errors: List[str] = []

    def _load_schema(self) -> Optional[etree.XMLSchema]:
        """Load and parse the XSD schema."""
        if self._schema is not None:
            return self._schema

        try:
            if self._schema_path and os.path.exists(self._schema_path):
                # Load from local file
                with open(self._schema_path, "rb") as f:
                    schema_doc = etree.parse(f)
            else:
                # Try to download from official URL
                try:
                    with urlopen(self.SCHEMA_URL, timeout=30) as response:
                        schema_content = response.read()
                    schema_doc = etree.parse(BytesIO(schema_content))
                except Exception as e:
                    self._schema_errors.append(f"Failed to download schema: {e}")
                    return None

            self._schema = etree.XMLSchema(schema_doc)
            return self._schema

        except etree.XMLSchemaParseError as e:
            self._schema_errors.append(f"Schema parse error: {e}")
            return None
        except Exception as e:
            self._schema_errors.append(f"Failed to load schema: {e}")
            return None

    def validate_xml(self, xml_content: str) -> Tuple[bool, List[ValidationError]]:
        """
        Validate XML content against the KSeF FA-3 schema.

        Args:
            xml_content: XML string to validate

        Returns:
            Tuple of (is_valid, list of validation errors)
        """
        errors: List[ValidationError] = []

        # Parse XML
        try:
            doc = etree.fromstring(xml_content.encode("utf-8"))
        except etree.XMLSyntaxError as e:
            errors.append(
                ValidationError(
                    line=e.lineno,
                    column=e.offset,
                    message=str(e),
                    error_type="fatal",
                )
            )
            return False, errors

        # Basic structure validation (without XSD)
        basic_errors = self._validate_basic_structure(doc)
        errors.extend(basic_errors)

        # XSD validation (if schema available)
        schema = self._load_schema()
        if schema is not None:
            try:
                schema.assertValid(doc)
            except etree.DocumentInvalid:
                for error in schema.error_log:
                    errors.append(
                        ValidationError(
                            line=error.line,
                            column=error.column,
                            message=error.message,
                            error_type="error",
                        )
                    )
        elif self._schema_errors:
            # Add warning about schema unavailability
            errors.append(
                ValidationError(
                    line=None,
                    column=None,
                    message=f"XSD schema unavailable: {'; '.join(self._schema_errors)}. "
                    "Only basic structure validation performed.",
                    error_type="warning",
                )
            )

        is_valid = all(e.error_type != "error" and e.error_type != "fatal" for e in errors)
        return is_valid, errors

    def validate_file(self, xml_path: str) -> Tuple[bool, List[ValidationError]]:
        """
        Validate XML file against the KSeF FA-3 schema.

        Args:
            xml_path: Path to XML file

        Returns:
            Tuple of (is_valid, list of validation errors)
        """
        try:
            with open(xml_path, encoding="utf-8") as f:
                xml_content = f.read()
            return self.validate_xml(xml_content)
        except FileNotFoundError:
            return False, [
                ValidationError(
                    line=None,
                    column=None,
                    message=f"File not found: {xml_path}",
                    error_type="fatal",
                )
            ]
        except Exception as e:
            return False, [
                ValidationError(
                    line=None, column=None, message=f"Failed to read file: {e}", error_type="fatal"
                )
            ]

    def _validate_basic_structure(self, doc: etree._Element) -> List[ValidationError]:
        """Perform basic structure validation without XSD."""
        errors: List[ValidationError] = []
        ns = {"ns": self.NAMESPACE}

        # Check root element
        expected_tag = f"{{{self.NAMESPACE}}}Faktura"
        if doc.tag != expected_tag:
            errors.append(
                ValidationError(
                    line=None,
                    column=None,
                    message=f"Root element must be 'Faktura' in namespace {self.NAMESPACE}",
                    error_type="error",
                )
            )
            return errors

        # Check required sections
        required_sections = [
            (".//ns:Naglowek", "Naglowek (Header)"),
            (".//ns:Podmiot1", "Podmiot1 (Seller)"),
            (".//ns:Podmiot2", "Podmiot2 (Buyer)"),
            (".//ns:Fa", "Fa (Invoice data)"),
        ]

        for xpath, name in required_sections:
            if doc.find(xpath, ns) is None:
                errors.append(
                    ValidationError(
                        line=None,
                        column=None,
                        message=f"Missing required section: {name}",
                        error_type="error",
                    )
                )

        # Check required invoice fields
        required_fields = [
            (".//ns:Fa/ns:KodWaluty", "KodWaluty (Currency code)"),
            (".//ns:Fa/ns:P_1", "P_1 (Issue date)"),
            (".//ns:Fa/ns:P_2", "P_2 (Invoice number)"),
            (".//ns:Fa/ns:P_15", "P_15 (Gross amount)"),
            (".//ns:Fa/ns:RodzajFaktury", "RodzajFaktury (Invoice type)"),
        ]

        for xpath, name in required_fields:
            elem = doc.find(xpath, ns)
            if elem is None or not elem.text:
                errors.append(
                    ValidationError(
                        line=None,
                        column=None,
                        message=f"Missing or empty required field: {name}",
                        error_type="error",
                    )
                )

        # Check for at least one invoice line
        lines = doc.findall(".//ns:FaWiersz", ns)
        if not lines:
            errors.append(
                ValidationError(
                    line=None,
                    column=None,
                    message="Invoice must have at least one line item (FaWiersz)",
                    error_type="error",
                )
            )

        # Check seller NIP
        seller_nip = doc.find(".//ns:Podmiot1//ns:NIP", ns)
        if seller_nip is None or not seller_nip.text:
            errors.append(
                ValidationError(
                    line=None,
                    column=None,
                    message="Seller (Podmiot1) must have NIP",
                    error_type="error",
                )
            )
        elif len(seller_nip.text) != 10 or not seller_nip.text.isdigit():
            errors.append(
                ValidationError(
                    line=None,
                    column=None,
                    message=f"Invalid NIP format: {seller_nip.text} (must be 10 digits)",
                    error_type="error",
                )
            )

        return errors
