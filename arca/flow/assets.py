# dagster_sip/assets.py

from dagster import MetadataValue, Output, asset

from arca.flow.mets_parser import parse_mets_to_sip
from arca.flow.pydantic_models import (
    FileModel,
    FixityModel,
    IEModel,
    RepresentationModel,
    SIPModel,
)
from arca.flow.utils import collect_dc_metadata, collect_fixity_details, group_fixities_by_file


@asset(config_schema={"file_paths": [str]})
def sip_asset(context) -> Output[SIPModel]:
    """
    Parses one or more METS XML files into a structured SIP (Submission Information Package) model.

    Args:
        context: The Dagster execution context containing operation configuration with file_paths.

    Returns:
        Output[SIPModel]: A Dagster Output containing:
            - value: Parsed SIPModel instance from the first file (primary SIP)
            - metadata: Dictionary containing:
                - File Paths: List of processed METS XML files
                - SIP ID: The unique identifier of the primary SIP
                - Intellectual Entity Count: Total number of IEs across all SIPs
                - IE IDs: List of all IE identifiers
    """
    file_paths = context.op_execution_context.op_config["file_paths"]
    if not file_paths:
        raise ValueError("At least one METS XML file path must be provided")

    # Parse the first file as the primary SIP
    primary_sip = parse_mets_to_sip(file_paths[0])
    all_ie_ids = [ie.ie_id for ie in primary_sip.intellectual_entities]

    # Process additional files if present
    if len(file_paths) > 1:
        for file_path in file_paths[1:]:
            additional_sip = parse_mets_to_sip(file_path)
            primary_sip.intellectual_entities.extend(additional_sip.intellectual_entities)
            all_ie_ids.extend([ie.ie_id for ie in additional_sip.intellectual_entities])

    return Output(
        value=primary_sip,
        metadata={
            "File Paths": MetadataValue.json(file_paths),
            "SIP ID": MetadataValue.text(primary_sip.sip_id),
            "Intellectual Entity Count": MetadataValue.int(len(primary_sip.intellectual_entities)),
            "IE IDs": MetadataValue.json(all_ie_ids),
        },
    )


@asset
def intellectual_entities(sip_asset: SIPModel) -> Output[list[IEModel]]:
    """Extract and process Intellectual Entity models from a SIP.

    Args:
        sip_asset: SIP model containing intellectual entities

    Returns:
        Output containing list of IEModel instances and their metadata
    """
    ie_list = sip_asset.intellectual_entities
    metadata = collect_dc_metadata(ie_list)

    return Output(value=ie_list, metadata=metadata)


@asset
def representations(intellectual_entities: list[IEModel]) -> Output[list[RepresentationModel]]:
    """
    Collects and processes all representations from a list of Intellectual Entities.
    A representation is a specific form of the intellectual content
    (e.g., preservation copy, access copy).

    Args:
        intellectual_entities (List[IEModel]): List of Intellectual Entity models
            to extract representations from.

    Returns:
        Output[List[RepresentationModel]]: A Dagster Output containing:
            - value: List of RepresentationModel instances
            - metadata: Dictionary containing:
                - Representation Count: Total number of representations
                - Representation IDs: List of unique representation identifiers
    """
    reps: list[RepresentationModel] = []
    for ie in intellectual_entities:
        reps.extend(ie.representations)

    # Collect representation IDs
    rep_ids = [rep.rep_id for rep in reps]

    return Output(
        value=reps,
        metadata={
            "Representation Count": MetadataValue.int(len(reps)),
            "Representation IDs": MetadataValue.json(rep_ids),
        },
    )


@asset
def files(representations: list[RepresentationModel]) -> Output[list[FileModel]]:
    """
    Extracts and processes all files from a list of representations.
    Collects file information including original names where available.

    Args:
        representations (List[RepresentationModel]): List of representation models
            to extract files from.

    Returns:
        Output[List[FileModel]]: A Dagster Output containing:
            - value: List of FileModel instances
            - metadata: Dictionary containing:
                - File Count: Total number of files across all representations
                - File Original Names: List of original filenames (excluding None values)
    """
    all_files: list[FileModel] = []
    for rep in representations:
        all_files.extend(rep.files)

    # Collect file original names, ignoring None
    file_names = [f.original_name for f in all_files if f.original_name]

    return Output(
        value=all_files,
        metadata={
            "File Count": MetadataValue.int(len(all_files)),
            "File Original Names": MetadataValue.json(file_names),
        },
    )


@asset
def fixities(files: list[FileModel]) -> Output[list[FixityModel]]:
    """Extract and process file fixity (checksum) information.

    Args:
        files: List of file models to process

    Returns:
        Output containing list of fixity models and metadata about
        fixity counts and organization by file
    """
    # Collect all fixities
    all_fixities: list[FixityModel] = []
    for f in files:
        all_fixities.extend(f.fixities)

    # Process fixity information
    files_by_id = {f.file_id: f for f in files}
    fixity_details = collect_fixity_details(all_fixities, files_by_id)
    fixities_by_file = group_fixities_by_file(fixity_details)

    return Output(
        value=all_fixities,
        metadata={
            "Fixity Count": MetadataValue.int(len(all_fixities)),
            "Fixities by File": MetadataValue.json(fixities_by_file),
            "All Fixities": MetadataValue.json(fixity_details),
        },
    )


# Load all assets from this module
all_assets = [
    sip_asset,
    intellectual_entities,
    representations,
    files,
    fixities,
]
