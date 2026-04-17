"""
METS XML Parser for OAIS-compliant SIP objects.

Parses METS XML files into structured SIP models following OAIS standards.
Supports Dublin Core metadata, PREMIS preservation metadata, and file fixity.
"""

import logging
import xml.etree.ElementTree as Et
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
from xml.etree.ElementTree import Element

from pydantic import ValidationError

from arca.flow.pydantic_models import (
    DublinCore,
    FileModel,
    FixityModel,
    FixityType,
    IEModel,
    RepresentationModel,
    RepresentationType,
    SIPModel,
)

logger = logging.getLogger(__name__)

NAMESPACES = {
    "mets": "http://www.loc.gov/METS/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "xlink": "http://www.w3.org/1999/xlink",
    "premis": "http://www.loc.gov/premis/v3",
}


class METSParsingError(Exception):
    """Raised when METS XML parsing fails."""

    pass


def _get_text(element: Element | None) -> str | None:
    """Extract stripped text from an XML element."""
    if element is not None and element.text:
        return element.text.strip()
    return None


def _find_premis_object(element: Element) -> Element | None:
    """Navigate to PREMIS object element within a metadata wrapper."""
    md_wrap = element.find(".//mets:mdWrap", NAMESPACES)
    if md_wrap is None:
        return None

    mdtype = md_wrap.get("MDTYPE")
    if mdtype not in ("PREMIS:OBJECT", "PREMIS"):
        return None

    xml_data = md_wrap.find(".//mets:xmlData", NAMESPACES)
    if xml_data is None:
        return None

    return xml_data.find(".//premis:object", NAMESPACES)


def _parse_premis_metadata(element: Element) -> dict[str, str]:
    """Extract file metadata from a PREMIS object element."""
    premis_obj = _find_premis_object(element)
    if premis_obj is None:
        return {}

    result = {}

    original_name = _get_text(premis_obj.find("premis:originalName", NAMESPACES))
    if original_name:
        result["fileOriginalName"] = original_name
        result["label"] = original_name

    obj_chars = premis_obj.find("premis:objectCharacteristics", NAMESPACES)
    if obj_chars is not None:
        size = _get_text(obj_chars.find("premis:size", NAMESPACES))
        if size:
            result["fileSize"] = size

        format_elem = obj_chars.find(".//premis:format", NAMESPACES)
        if format_elem is not None:
            format_name = _get_text(format_elem.find(".//premis:formatName", NAMESPACES))
            if format_name:
                result["fileMIMEType"] = format_name

        for fixity in obj_chars.findall("premis:fixity", NAMESPACES):
            algorithm = _get_text(fixity.find("premis:messageDigestAlgorithm", NAMESPACES))
            digest = _get_text(fixity.find("premis:messageDigest", NAMESPACES))
            if algorithm and digest and "fixityType" not in result:
                result["fixityType"] = algorithm
                result["fixityValue"] = digest

        creating_app = obj_chars.find("premis:creatingApplication", NAMESPACES)
        if creating_app is not None:
            date_created = _get_text(
                creating_app.find("premis:dateCreatedByApplication", NAMESPACES)
            )
            if date_created:
                result["fileCreationDate"] = date_created

    storage = premis_obj.find(".//premis:storage", NAMESPACES)
    if storage is not None:
        content_loc = storage.find("premis:contentLocation", NAMESPACES)
        if content_loc is not None:
            loc_value = _get_text(content_loc.find("premis:contentLocationValue", NAMESPACES))
            if loc_value:
                result["fileOriginalPath"] = loc_value

    pres_level = premis_obj.find("premis:preservationLevel", NAMESPACES)
    if pres_level is not None:
        pres_type = _get_text(pres_level.find("premis:preservationLevelType", NAMESPACES))
        if pres_type:
            result["preservationType"] = pres_type

        pres_value = _get_text(pres_level.find("premis:preservationLevelValue", NAMESPACES))
        if pres_value:
            result["usageType"] = pres_value

    for sig_prop in premis_obj.findall("premis:significantProperties", NAMESPACES):
        prop_type = _get_text(sig_prop.find("premis:significantPropertiesType", NAMESPACES))
        prop_value = _get_text(sig_prop.find("premis:significantPropertiesValue", NAMESPACES))
        if prop_type and prop_value:
            result[prop_type] = prop_value

    return result


def _parse_premis_fixities(element: Element) -> list[dict[str, str]]:
    """Extract all fixity records from a PREMIS object element."""
    premis_obj = _find_premis_object(element)
    if premis_obj is None:
        return []

    obj_chars = premis_obj.find("premis:objectCharacteristics", NAMESPACES)
    if obj_chars is None:
        return []

    fixities = []
    for fixity in obj_chars.findall("premis:fixity", NAMESPACES):
        algorithm = _get_text(fixity.find("premis:messageDigestAlgorithm", NAMESPACES))
        digest = _get_text(fixity.find("premis:messageDigest", NAMESPACES))
        if algorithm and digest:
            fixities.append({"fixityType": algorithm, "fixityValue": digest})

    return fixities


def _parse_dc_metadata(dmd_sec: Element) -> DublinCore:
    """Extract Dublin Core metadata from a METS dmdSec element."""
    md_wrap = dmd_sec.find("mets:mdWrap", NAMESPACES)
    if md_wrap is None:
        return DublinCore()

    xml_data = md_wrap.find("mets:xmlData", NAMESPACES)
    if xml_data is None:
        return DublinCore()

    dc_record = xml_data.find("dc:record", NAMESPACES)
    if dc_record is None:
        return DublinCore()

    def collect_field(field_name: str) -> list[str]:
        return [
            text
            for el in dc_record.findall(f"dc:{field_name}", NAMESPACES)
            if (text := _get_text(el))
        ]

    return DublinCore(
        title=collect_field("title"),
        creator=collect_field("creator"),
        type=collect_field("type"),
        identifier=collect_field("identifier"),
        rights=collect_field("rights"),
    )


def _parse_file_element(
    file_el: Element,
    amd_map: dict[str, dict[str, str]],
    root: Element,
) -> FileModel:
    """Parse a METS file element into a FileModel with fixity data."""
    file_id = file_el.get("ID", str(uuid4()))
    file_dmdid = file_el.get("DMDID", "")
    file_admid = file_el.get("ADMID", "")
    file_data = amd_map.get(file_admid, {})

    size_bytes = 0
    try:
        size_bytes = int(file_data.get("fileSize", 0))
    except (ValueError, TypeError):
        logger.warning(f"Invalid file size for {file_id}, using 0")

    file_model = FileModel(
        file_id=file_id,
        label=file_data.get("label", file_id),
        mime_type=file_data.get("fileMIMEType", "application/octet-stream"),
        original_name=file_data.get("fileOriginalName", file_id),
        original_path=file_data.get("fileOriginalPath"),
        size_bytes=size_bytes,
        dmd_ids=file_dmdid.split(),
        adm_ids=file_admid.split(),
    )

    if file_admid:
        amd_sec = root.find(f'.//mets:amdSec[@ID="{file_admid}"]', NAMESPACES)
        if amd_sec is not None:
            tech_md = amd_sec.find(".//mets:techMD", NAMESPACES)
            if tech_md is not None:
                file_model.fixities = _build_fixity_models(tech_md, file_id)

    return file_model


def _build_fixity_models(tech_md: Element, file_id: str) -> list[FixityModel]:
    """Convert PREMIS fixity data into FixityModel instances."""
    fixities = []
    for fix_data in _parse_premis_fixities(tech_md):
        try:
            fix_type = FixityType(fix_data["fixityType"].upper())
            fix_value = fix_data.get("fixityValue")
            if fix_value:
                fixities.append(
                    FixityModel(
                        fixity_type=fix_type,
                        fixity_value=fix_value,
                        file_id=file_id,
                    )
                )
        except (ValueError, KeyError) as e:
            logger.warning(f"Invalid fixity data for file {file_id}: {e}")
    return fixities


def _determine_representation_type(pres_type: str) -> RepresentationType:
    """Map PREMIS preservation level type to RepresentationType."""
    pres_type_upper = pres_type.upper()
    if pres_type_upper in ("PRESERVATION_MASTER", "PRESERVATION"):
        return RepresentationType.PRESERVATION
    if pres_type_upper in ("DERIVATIVE_COPY", "ACCESS", "DERIVATIVE"):
        return RepresentationType.ACCESS
    if pres_type_upper in ("ORIGINAL", "SUBMISSION"):
        return RepresentationType.ORIGINAL
    return RepresentationType.ACCESS


def _parse_metadata_sections(
    root: Element,
) -> tuple[dict[str, DublinCore], dict[str, dict[str, str]]]:
    """Extract descriptive and administrative metadata from METS."""
    dmd_map = {}
    for dmd_sec in root.findall("mets:dmdSec", NAMESPACES):
        dmd_id = dmd_sec.get("ID")
        if dmd_id:
            dmd_map[dmd_id] = _parse_dc_metadata(dmd_sec)

    amd_map = {}
    for amd_sec in root.findall("mets:amdSec", NAMESPACES):
        amd_id = amd_sec.get("ID")
        if amd_id:
            tech_md = amd_sec.find("mets:techMD", NAMESPACES)
            if tech_md is not None:
                amd_map[amd_id] = _parse_premis_metadata(tech_md)

    return dmd_map, amd_map


def _process_file_sections(
    root: Element, amd_map: dict[str, dict[str, str]]
) -> list[RepresentationModel]:
    """Extract file groups into representation models."""
    file_sec = root.find("mets:fileSec", NAMESPACES)
    if file_sec is None:
        return []

    representations = []
    for file_grp in file_sec.findall("mets:fileGrp", NAMESPACES):
        rep_id = file_grp.get("ID", "rep-unknown")
        admid = file_grp.get("ADMID", "")

        rep_data = _get_representation_metadata(root, admid)
        usage_type = _determine_representation_type(rep_data.get("preservationType", ""))

        rep_model = RepresentationModel(
            rep_id=rep_id,
            label=rep_data.get("label") or f"Representation {rep_id}",
            usage_type=usage_type,
            creation_date=datetime.now(UTC),
        )

        for file_el in file_grp.findall("mets:file", NAMESPACES):
            try:
                rep_model.files.append(_parse_file_element(file_el, amd_map, root))
            except (METSParsingError, ValidationError) as e:
                logger.error(f"Failed to parse file in representation {rep_id}: {e}")

        if rep_model.files:
            representations.append(rep_model)
        else:
            logger.warning(f"Skipping representation {rep_id}: no valid files")

    return representations


def _get_representation_metadata(root: Element, admid: str) -> dict[str, str]:
    """Get PREMIS metadata for a representation by its ADMID."""
    if not admid:
        return {}

    amd_sec = root.find(f'.//mets:amdSec[@ID="{admid}"]', NAMESPACES)
    if amd_sec is None:
        return {}

    tech_md = amd_sec.find(".//mets:techMD", NAMESPACES)
    if tech_md is None:
        return {}

    premis_data = _parse_premis_metadata(tech_md)
    result: dict[str, str] = {}
    if (label := premis_data.get("label")) is not None:
        result["label"] = label
    if (ptype := premis_data.get("preservationType")) is not None:
        result["preservationType"] = ptype
    return result


def _build_ie_model(
    sip_id: str,
    dmd_map: dict[str, DublinCore],
    amd_map: dict[str, dict[str, str]],
    representations: list[RepresentationModel],
) -> IEModel:
    """Create an IEModel from metadata and representations."""
    if "ie-dmd" not in dmd_map:
        raise METSParsingError("Missing required ie-dmd section")

    ie_dmd_data = dmd_map["ie-dmd"]
    if not any([ie_dmd_data.title, ie_dmd_data.identifier, ie_dmd_data.type]):
        raise METSParsingError("Missing required Dublin Core metadata")

    ie_id = sip_id.replace("SIP-", "IE-")
    ie_amd_data = amd_map.get("ie-amd", {})

    dc_model = DublinCore(
        title=ie_dmd_data.title or ["Untitled"],
        creator=ie_dmd_data.creator,
        type=ie_dmd_data.type,
        identifier=ie_dmd_data.identifier or [ie_id],
        rights=ie_dmd_data.rights,
    )

    return IEModel(
        ie_id=ie_id,
        dc=dc_model,
        ie_entity_type=ie_amd_data.get("IEEntityType", "unknown"),
        representations=representations,
    )


def _extract_sip_metadata(root: Element, xml_path: str | Path) -> tuple[str, str]:
    """Extract SIP ID and submitting agent from METS header."""
    sip_id = root.get("OBJID", f"SIP-{Path(xml_path).stem}")

    submitting_agent = "Unknown"
    header = root.find("mets:metsHdr", NAMESPACES)
    if header is not None:
        agent = header.find('.//mets:agent[@ROLE="CREATOR"]', NAMESPACES)
        if agent is not None:
            submitting_agent = _get_text(agent.find(".//mets:name", NAMESPACES)) or "Unknown"

    return sip_id, submitting_agent


def parse_mets_to_sip(xml_path: str | Path) -> SIPModel:
    """
    Parse a METS XML file into a validated SIP model.

    Raises METSParsingError for structural or validation errors.
    """
    logger.info(f"Parsing METS file: {xml_path}")

    try:
        tree = Et.parse(xml_path)
        root = tree.getroot()
    except (OSError, Et.ParseError) as e:
        raise METSParsingError(f"Failed to parse XML file: {e}") from e

    try:
        sip_id, submitting_agent = _extract_sip_metadata(root, xml_path)
        dmd_map, amd_map = _parse_metadata_sections(root)
        representations = _process_file_sections(root, amd_map)
        ie_model = _build_ie_model(sip_id, dmd_map, amd_map, representations)

        return SIPModel(
            sip_id=sip_id,
            submitting_agent=submitting_agent,
            creation_date=datetime.now(UTC),
            intellectual_entities=[ie_model],
        )
    except METSParsingError:
        raise
    except Exception as e:
        raise METSParsingError(f"Failed to parse METS structure: {e}") from e
