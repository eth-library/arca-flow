"""Utility functions for Arca Flow."""

from dagster import MetadataValue

from arca.flow.pydantic_models import FileModel, FixityModel, IEModel


def collect_dc_metadata(ie_list: list[IEModel]) -> dict:
    """Collect Dublin Core metadata from a list of Intellectual Entities.

    Args:
        ie_list: List of Intellectual Entity models

    Returns:
        Dictionary containing aggregated Dublin Core metadata
    """
    dc_titles = [ie.dc.title[0] for ie in ie_list if ie.dc.title]
    dc_identifiers = []
    dc_creators = []
    dc_rights = []
    dc_types = []

    for ie in ie_list:
        dc_identifiers.extend(ie.dc.identifier)
        dc_creators.extend(ie.dc.creator)
        dc_rights.extend(ie.dc.rights)
        dc_types.extend(ie.dc.type)

    return {
        "IE Count": MetadataValue.int(len(ie_list)),
        "IE DC Titles": MetadataValue.json(dc_titles),
        "IE DC Identifiers": MetadataValue.json(dc_identifiers),
        "IE DC Creators": MetadataValue.json(dc_creators),
        "IE DC Rights": MetadataValue.json(dc_rights),
        "IE DC Types": MetadataValue.json(dc_types),
    }


def collect_fixity_details(
    all_fixities: list[FixityModel], files_by_id: dict[str, FileModel]
) -> list[dict]:
    """Collect detailed fixity information with associated file data.

    Args:
        all_fixities: List of fixity models
        files_by_id: Dictionary mapping file IDs to file models

    Returns:
        List of dictionaries containing fixity details with file information
    """
    fixity_details = []
    for fx in all_fixities:
        file = files_by_id.get(fx.file_id)
        if file:
            fixity_details.append(
                {
                    "type": fx.fixity_type.value,
                    "value": fx.fixity_value,
                    "file_id": fx.file_id,
                    "file_name": file.original_name,
                    "file_label": file.label,
                }
            )
    return fixity_details


def group_fixities_by_file(fixity_details: list[dict]) -> dict[str, dict]:
    """Group fixity information by file.

    Args:
        fixity_details: List of fixity details with file information

    Returns:
        Dictionary organizing fixities by file ID
    """
    fixities_by_file = {}
    for detail in fixity_details:
        file_id = detail["file_id"]
        if file_id not in fixities_by_file:
            fixities_by_file[file_id] = {
                "file_name": detail["file_name"],
                "file_label": detail["file_label"],
                "fixities": [],
            }
        fixities_by_file[file_id]["fixities"].append(
            {"type": detail["type"], "value": detail["value"]}
        )
    return fixities_by_file
