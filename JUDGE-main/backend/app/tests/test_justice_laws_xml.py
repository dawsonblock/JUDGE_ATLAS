"""Unit tests for Justice Canada law parser and schema validator."""

from __future__ import annotations

import pytest
from app.ingestion.laws.justice_canada.parser import (
    parse_legis_index,
    parse_statute_xml,
)
from app.ingestion.laws.justice_canada.schema_validator import (
    SchemaValidationError,
    validate_index_xml,
    validate_statute_xml,
)


class TestSchemaValidatorIndex:
    """Tests for Legis.xml (master index) schema validation."""
    
    def test_validate_index_xml_valid(self):
        """Valid Legis.xml passes validation."""
        valid_xml = b"""<?xml version="1.0"?>
<ActsRegsList>
  <Acts>
    <Act>
      <UniqueId>C-46</UniqueId>
      <Language>eng</Language>
      <Title>Criminal Code</Title>
      <LinkToXML>https://laws-lois.justice.gc.ca/eng/XML/C-46.xml</LinkToXML>
      <LinkToHTMLToC>https://laws-lois.justice.gc.ca/eng/acts/C-46/index.html</LinkToHTMLToC>
      <OfficialNumber>C-46</OfficialNumber>
      <CurrentToDate>2026-03-17</CurrentToDate>
    </Act>
  </Acts>
</ActsRegsList>
"""
        assert validate_index_xml(valid_xml) is True


class TestParserLegisIndex:
    """Tests for parse_legis_index()."""
    
    def test_parse_legis_index_criminal_code(self):
        """Parse Legis.xml with Criminal Code."""
        xml = b"""<?xml version="1.0"?>
<ActsRegsList>
  <Acts>
    <Act>
      <UniqueId>C-46</UniqueId>
      <OfficialNumber>C-46</OfficialNumber>
      <Language>eng</Language>
      <LinkToXML>https://laws-lois.justice.gc.ca/eng/XML/C-46.xml</LinkToXML>
      <LinkToHTMLToC>https://laws-lois.justice.gc.ca/eng/acts/C-46/index.html</LinkToHTMLToC>
      <Title>Criminal Code</Title>
      <CurrentToDate>2026-03-17</CurrentToDate>
    </Act>
  </Acts>
</ActsRegsList>
"""
        records = parse_legis_index(xml)
        
        assert len(records) == 1
        assert records[0]["unique_id"] == "C-46"
        assert records[0]["language"] == "eng"
        assert records[0]["title"] == "Criminal Code"
        assert records[0]["law_type"] == "Act"
        assert "C-46.xml" in records[0]["link_to_xml"]


class TestParserStatuteXml:
    """Tests for parse_statute_xml()."""
    
    def test_parse_statute_xml_criminal_code(self):
        """Parse Criminal Code statute XML."""
        xml = b"""<?xml version="1.0"?>
<Statute xmlns:lims="http://justice.gc.ca/lims" 
         lims:id="114997" 
         lims:current-date="2026-03-02">
  <Identification>
    <ShortTitle>Criminal Code</ShortTitle>
    <Chapter>
      <ConsolidatedNumber official="yes">C-46</ConsolidatedNumber>
    </Chapter>
  </Identification>
  <Body>
    <Section>
      <Label>1</Label>
      <MarginalNote>Short title</MarginalNote>
      <Text>This Act may be cited as the Criminal Code.</Text>
    </Section>
    <Section>
      <Label>2</Label>
      <MarginalNote>Definitions</MarginalNote>
      <Text>In this Act, ...</Text>
    </Section>
  </Body>
</Statute>
"""
        record = parse_statute_xml(xml)
        
        assert record is not None
        assert record["statute_id"] == "114997"
        assert record["short_title"] == "Criminal Code"
        assert record["consolidated_number"] == "C-46"
        assert len(record["sections"]) == 2
        assert record["sections"][0]["label"] == "1"
        assert "Criminal Code" in record["sections"][0]["text"]


class TestFixtures:
    """Tests using Criminal Code fixtures."""
    
    def test_parse_legis_fixture(self):
        """Parse Legis.xml fixture."""
        fixture_path = "app/tests/fixtures/sources/legis_sample.xml"
        with open(fixture_path, "rb") as f:
            xml = f.read()
        
        records = parse_legis_index(xml)
        
        # Should have 2 records (eng + fra)
        assert len(records) == 2
        
        # First should be English
        assert records[0]["unique_id"] == "C-46"
        assert records[0]["language"] == "eng"
        assert records[0]["title"] == "Criminal Code"
        assert records[0]["law_type"] == "Act"
        
        # Second should be French
        assert records[1]["unique_id"] == "C-46"
        assert records[1]["language"] == "fra"
        assert records[1]["title"] == "Code criminel"
    
    def test_parse_criminal_code_fixture(self):
        """Parse Criminal Code statute fixture."""
        fixture_path = "app/tests/fixtures/sources/c-46_sample.xml"
        with open(fixture_path, "rb") as f:
            xml = f.read()
        
        record = parse_statute_xml(xml)
        
        assert record is not None
        assert record["statute_id"] == "114997"
        assert record["short_title"] == "Criminal Code"
        assert record["long_title"] == "An Act respecting the Criminal Law"
        assert record["consolidated_number"] == "C-46"
        assert record["current_date"] == "2026-03-02"
        
        # Should have 2 sections
        assert len(record["sections"]) == 2
        
        # First section
        assert record["sections"][0]["label"] == "1"
        assert record["sections"][0]["marginal_note"] == "Short title"
        assert "Criminal Code" in record["sections"][0]["text"]
        
        # Second section
        assert record["sections"][1]["label"] == "2"
        assert record["sections"][1]["marginal_note"] == "Definitions"
        assert "bodily harm" in record["sections"][1]["text"]
    
    def test_validate_legis_fixture(self):
        """Validate Legis.xml fixture schema."""
        fixture_path = "app/tests/fixtures/sources/legis_sample.xml"
        with open(fixture_path, "rb") as f:
            xml = f.read()
        
        assert validate_index_xml(xml) is True
    
    def test_validate_criminal_code_fixture(self):
        """Validate Criminal Code statute fixture schema."""
        fixture_path = "app/tests/fixtures/sources/c-46_sample.xml"
        with open(fixture_path, "rb") as f:
            xml = f.read()
        
        assert validate_statute_xml(xml, "C-46") is True
