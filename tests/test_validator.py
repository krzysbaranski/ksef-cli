"""Tests for KSeFValidator in ksef_cli.validator"""

import os
from unittest.mock import MagicMock, patch

import pytest

from ksef_cli.validator import KSeFValidator, ValidationError


class TestValidationError:
    """Tests for ValidationError dataclass"""

    def test_str_with_line_and_column(self):
        """Test ValidationError string representation with line and column"""
        err = ValidationError(line=10, column=5, message="test error", error_type="error")
        result = str(err)
        assert "Line 10" in result
        assert "Column 5" in result
        assert "test error" in result
        assert "ERROR" in result

    def test_str_with_line_no_column(self):
        """Test ValidationError string representation with line but no column"""
        err = ValidationError(line=10, column=None, message="test error", error_type="warning")
        result = str(err)
        assert "Line 10" in result
        assert "Column" not in result
        assert "WARNING" in result

    def test_str_without_location(self):
        """Test ValidationError string representation without location"""
        err = ValidationError(line=None, column=None, message="no location", error_type="fatal")
        result = str(err)
        assert "Line" not in result
        assert "no location" in result
        assert "FATAL" in result


class TestKSeFValidatorInit:
    """Tests for KSeFValidator initialization"""

    def test_init_default(self):
        """Test default initialization"""
        validator = KSeFValidator()
        assert validator._schema is None
        assert validator._schema_path is None
        assert validator._schema_errors == []

    def test_init_with_schema_path(self, tmp_path):
        """Test initialization with schema path"""
        schema_path = str(tmp_path / "schema.xsd")
        validator = KSeFValidator(schema_path=schema_path)
        assert validator._schema_path == schema_path


class TestKSeFValidatorLoadSchema:
    """Tests for _load_schema method"""

    def test_load_schema_returns_cached(self):
        """Test that already loaded schema is returned from cache"""
        validator = KSeFValidator()
        mock_schema = MagicMock()
        validator._schema = mock_schema

        result = validator._load_schema()

        assert result is mock_schema

    def test_load_schema_from_local_file(self, tmp_path):
        """Test loading schema from a local file"""
        # Create a minimal valid XSD schema
        xsd_content = """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="root" type="xs:string"/>
</xs:schema>"""
        schema_file = tmp_path / "schema.xsd"
        schema_file.write_text(xsd_content, encoding="utf-8")

        validator = KSeFValidator(schema_path=str(schema_file))
        result = validator._load_schema()

        assert result is not None

    def test_load_schema_download_failure(self):
        """Test handling of schema download failure"""
        validator = KSeFValidator()

        with patch("ksef_cli.validator.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = Exception("Connection refused")
            result = validator._load_schema()

        assert result is None
        assert len(validator._schema_errors) > 0
        assert "Failed to download schema" in validator._schema_errors[0]

    def test_load_schema_invalid_local_file(self, tmp_path):
        """Test handling of invalid XSD schema file"""
        bad_schema_file = tmp_path / "bad.xsd"
        bad_schema_file.write_text("not valid xsd", encoding="utf-8")

        validator = KSeFValidator(schema_path=str(bad_schema_file))
        result = validator._load_schema()

        assert result is None
        assert len(validator._schema_errors) > 0

    def test_load_schema_nonexistent_path_falls_back_to_download(self):
        """Test that nonexistent schema_path falls back to download"""
        validator = KSeFValidator(schema_path="/nonexistent/schema.xsd")

        with patch("ksef_cli.validator.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = Exception("Network error")
            result = validator._load_schema()

        assert result is None
        assert "Failed to download schema" in validator._schema_errors[0]

    def test_load_schema_successful_download(self):
        """Test that a successful schema download creates and caches the schema"""
        from io import BytesIO

        valid_xsd = b"""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="root" type="xs:string"/>
</xs:schema>"""

        validator = KSeFValidator()

        mock_response = MagicMock()
        mock_response.read.return_value = valid_xsd
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("ksef_cli.validator.urlopen", return_value=mock_response):
            result = validator._load_schema()

        assert result is not None
        assert validator._schema is result

    def test_load_schema_xsd_parse_error(self, tmp_path):
        """Test handling of XMLSchemaParseError during schema creation"""
        from lxml import etree

        valid_xsd = b"""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="root" type="xs:string"/>
</xs:schema>"""

        validator = KSeFValidator()

        mock_response = MagicMock()
        mock_response.read.return_value = valid_xsd
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("ksef_cli.validator.urlopen", return_value=mock_response):
            with patch("ksef_cli.validator.etree.XMLSchema") as mock_schema_cls:
                mock_schema_cls.side_effect = etree.XMLSchemaParseError("invalid schema")
                result = validator._load_schema()

        assert result is None
        assert len(validator._schema_errors) > 0
        assert "Schema parse error" in validator._schema_errors[0]


class TestKSeFValidatorValidateXml:
    """Tests for validate_xml method"""

    def _make_valid_xml(self) -> str:
        ns = "http://crd.gov.pl/wzor/2025/06/25/13775/"
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Faktura xmlns="{ns}">
  <Naglowek>
    <KodFormularza>FA</KodFormularza>
    <WariantFormularza>3</WariantFormularza>
  </Naglowek>
  <Podmiot1>
    <DaneIdentyfikacyjne>
      <NIP>5260250274</NIP>
      <Nazwa>Seller</Nazwa>
    </DaneIdentyfikacyjne>
  </Podmiot1>
  <Podmiot2>
    <DaneIdentyfikacyjne>
      <NIP>9492107026</NIP>
      <Nazwa>Buyer</Nazwa>
    </DaneIdentyfikacyjne>
  </Podmiot2>
  <Fa>
    <KodWaluty>PLN</KodWaluty>
    <P_1>2026-01-01</P_1>
    <P_2>FV/001</P_2>
    <P_15>123.00</P_15>
    <RodzajFaktury>VAT</RodzajFaktury>
    <FaWiersz>
      <NrWierszaFa>1</NrWierszaFa>
    </FaWiersz>
  </Fa>
</Faktura>"""

    def test_validate_xml_invalid_syntax(self):
        """Test validate_xml with malformed XML"""
        validator = KSeFValidator()
        is_valid, errors = validator.validate_xml("< invalid xml >")

        assert not is_valid
        assert len(errors) > 0
        assert errors[0].error_type == "fatal"

    def test_validate_xml_wrong_root_element(self):
        """Test validate_xml with wrong root element"""
        ns = "http://crd.gov.pl/wzor/2025/06/25/13775/"
        xml = f'<WrongRoot xmlns="{ns}"/>'

        validator = KSeFValidator()
        with patch.object(validator, "_load_schema", return_value=None):
            is_valid, errors = validator.validate_xml(xml)

        assert not is_valid
        assert any("Root element" in e.message for e in errors)

    def test_validate_xml_missing_sections(self):
        """Test validate_xml with missing required sections"""
        ns = "http://crd.gov.pl/wzor/2025/06/25/13775/"
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Faktura xmlns="{ns}">
</Faktura>"""

        validator = KSeFValidator()
        with patch.object(validator, "_load_schema", return_value=None):
            is_valid, errors = validator.validate_xml(xml)

        assert not is_valid
        assert any("Naglowek" in e.message for e in errors)

    def test_validate_xml_missing_fields(self):
        """Test validate_xml with missing required invoice fields"""
        ns = "http://crd.gov.pl/wzor/2025/06/25/13775/"
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Faktura xmlns="{ns}">
  <Naglowek/>
  <Podmiot1>
    <DaneIdentyfikacyjne>
      <NIP>5260250274</NIP>
    </DaneIdentyfikacyjne>
  </Podmiot1>
  <Podmiot2/>
  <Fa>
    <FaWiersz/>
  </Fa>
</Faktura>"""

        validator = KSeFValidator()
        with patch.object(validator, "_load_schema", return_value=None):
            is_valid, errors = validator.validate_xml(xml)

        assert not is_valid
        assert any("KodWaluty" in e.message for e in errors)

    def test_validate_xml_missing_invoice_lines(self):
        """Test validate_xml with no invoice line items"""
        ns = "http://crd.gov.pl/wzor/2025/06/25/13775/"
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Faktura xmlns="{ns}">
  <Naglowek/>
  <Podmiot1>
    <DaneIdentyfikacyjne>
      <NIP>5260250274</NIP>
    </DaneIdentyfikacyjne>
  </Podmiot1>
  <Podmiot2/>
  <Fa>
    <KodWaluty>PLN</KodWaluty>
    <P_1>2026-01-01</P_1>
    <P_2>FV/001</P_2>
    <P_15>100.00</P_15>
    <RodzajFaktury>VAT</RodzajFaktury>
  </Fa>
</Faktura>"""

        validator = KSeFValidator()
        with patch.object(validator, "_load_schema", return_value=None):
            is_valid, errors = validator.validate_xml(xml)

        assert not is_valid
        assert any("FaWiersz" in e.message for e in errors)

    def test_validate_xml_missing_seller_nip(self):
        """Test validate_xml with missing seller NIP"""
        ns = "http://crd.gov.pl/wzor/2025/06/25/13775/"
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Faktura xmlns="{ns}">
  <Naglowek/>
  <Podmiot1/>
  <Podmiot2/>
  <Fa>
    <KodWaluty>PLN</KodWaluty>
    <P_1>2026-01-01</P_1>
    <P_2>FV/001</P_2>
    <P_15>100.00</P_15>
    <RodzajFaktury>VAT</RodzajFaktury>
    <FaWiersz/>
  </Fa>
</Faktura>"""

        validator = KSeFValidator()
        with patch.object(validator, "_load_schema", return_value=None):
            is_valid, errors = validator.validate_xml(xml)

        assert not is_valid
        assert any("NIP" in e.message for e in errors)

    def test_validate_xml_invalid_nip_format(self):
        """Test validate_xml with invalid NIP format (wrong length)"""
        ns = "http://crd.gov.pl/wzor/2025/06/25/13775/"
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Faktura xmlns="{ns}">
  <Naglowek/>
  <Podmiot1>
    <DaneIdentyfikacyjne>
      <NIP>123</NIP>
    </DaneIdentyfikacyjne>
  </Podmiot1>
  <Podmiot2/>
  <Fa>
    <KodWaluty>PLN</KodWaluty>
    <P_1>2026-01-01</P_1>
    <P_2>FV/001</P_2>
    <P_15>100.00</P_15>
    <RodzajFaktury>VAT</RodzajFaktury>
    <FaWiersz/>
  </Fa>
</Faktura>"""

        validator = KSeFValidator()
        with patch.object(validator, "_load_schema", return_value=None):
            is_valid, errors = validator.validate_xml(xml)

        assert not is_valid
        assert any("Invalid NIP" in e.message for e in errors)

    def test_validate_xml_with_xsd_validation_errors(self):
        """Test validate_xml when XSD schema catches errors"""
        from lxml import etree

        xml = self._make_valid_xml()

        mock_schema = MagicMock(unsafe=True)
        mock_schema.assertValid.side_effect = etree.DocumentInvalid("Invalid document")
        mock_error = MagicMock()
        mock_error.line = 1
        mock_error.column = 1
        mock_error.message = "XSD error"
        mock_schema.error_log = [mock_error]

        validator = KSeFValidator()
        with patch.object(validator, "_load_schema", return_value=mock_schema):
            is_valid, errors = validator.validate_xml(xml)

        assert not is_valid
        assert any("XSD error" in e.message for e in errors)

    def test_validate_xml_schema_unavailable_warning(self):
        """Test validate_xml adds warning when schema is unavailable"""
        xml = self._make_valid_xml()

        validator = KSeFValidator()
        validator._schema_errors = ["schema download failed"]

        with patch.object(validator, "_load_schema", return_value=None):
            is_valid, errors = validator.validate_xml(xml)

        # Should be valid (no error-type errors) but have a warning
        warning_errors = [e for e in errors if e.error_type == "warning"]
        assert len(warning_errors) > 0
        assert "XSD schema unavailable" in warning_errors[0].message


class TestKSeFValidatorValidateFile:
    """Tests for validate_file method"""

    def test_validate_file_valid(self, tmp_path):
        """Test validate_file with a valid file"""
        ns = "http://crd.gov.pl/wzor/2025/06/25/13775/"
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Faktura xmlns="{ns}">
  <Naglowek/>
  <Podmiot1>
    <DaneIdentyfikacyjne>
      <NIP>5260250274</NIP>
    </DaneIdentyfikacyjne>
  </Podmiot1>
  <Podmiot2/>
  <Fa>
    <KodWaluty>PLN</KodWaluty>
    <P_1>2026-01-01</P_1>
    <P_2>FV/001</P_2>
    <P_15>100.00</P_15>
    <RodzajFaktury>VAT</RodzajFaktury>
    <FaWiersz/>
  </Fa>
</Faktura>"""
        xml_file = tmp_path / "invoice.xml"
        xml_file.write_text(xml, encoding="utf-8")

        validator = KSeFValidator()
        with patch.object(validator, "_load_schema", return_value=None):
            is_valid, errors = validator.validate_file(str(xml_file))

        # No fatal or error-type errors means valid
        assert all(e.error_type not in ("error", "fatal") for e in errors)

    def test_validate_file_not_found(self, tmp_path):
        """Test validate_file with non-existent file"""
        validator = KSeFValidator()
        is_valid, errors = validator.validate_file(str(tmp_path / "nonexistent.xml"))

        assert not is_valid
        assert len(errors) == 1
        assert errors[0].error_type == "fatal"
        assert "File not found" in errors[0].message

    def test_validate_file_read_error(self, tmp_path):
        """Test validate_file handles general read errors"""
        validator = KSeFValidator()

        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            is_valid, errors = validator.validate_file(str(tmp_path / "file.xml"))

        assert not is_valid
        assert len(errors) == 1
        assert errors[0].error_type == "fatal"
        assert "Failed to read file" in errors[0].message


class TestKSeFValidatorBasicStructure:
    """Tests for _validate_basic_structure method"""

    def test_valid_structure_returns_no_errors(self):
        """Test that a valid structure returns no errors"""
        from lxml import etree

        ns = "http://crd.gov.pl/wzor/2025/06/25/13775/"
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Faktura xmlns="{ns}">
  <Naglowek/>
  <Podmiot1>
    <DaneIdentyfikacyjne>
      <NIP>5260250274</NIP>
    </DaneIdentyfikacyjne>
  </Podmiot1>
  <Podmiot2/>
  <Fa>
    <KodWaluty>PLN</KodWaluty>
    <P_1>2026-01-01</P_1>
    <P_2>FV/001</P_2>
    <P_15>100.00</P_15>
    <RodzajFaktury>VAT</RodzajFaktury>
    <FaWiersz/>
  </Fa>
</Faktura>"""
        doc = etree.fromstring(xml.encode("utf-8"))
        validator = KSeFValidator()
        errors = validator._validate_basic_structure(doc)

        error_only = [e for e in errors if e.error_type == "error"]
        assert len(error_only) == 0

    def test_wrong_root_stops_early(self):
        """Test that wrong root element causes early return"""
        from lxml import etree

        xml = "<WrongRoot/>"
        doc = etree.fromstring(xml.encode("utf-8"))

        validator = KSeFValidator()
        errors = validator._validate_basic_structure(doc)

        assert len(errors) == 1
        assert "Root element" in errors[0].message
