import os

import pytest
from dagster import materialize

from arca.flow.assets import files, fixities, intellectual_entities, representations, sip_asset


@pytest.fixture
def mets_file_path():
    """
    Returns the path to a static METS XML file stored in the repo.
    Used as a fixture for both single and multiple file tests.
    """
    # __file__ is the current Python file (test_sip_pipeline.py).
    # We go up one directory to 'test_data', then the 'mets_sample.xml'.
    return os.path.join(os.path.dirname(__file__), "test_data", "synthetic_sip.xml")


def test_sip_pipeline_single_file(mets_file_path):
    """
    This test runs the entire DAGSTER pipeline (assets)
    using a single METS XML file from the repo.
    """
    # We run 'materialize' with the relevant assets
    # and provide a run_config that assigns a single METS file path
    # to the sip_asset's file_paths configuration.

    result = materialize(
        assets=[sip_asset, intellectual_entities, representations, files, fixities],
        run_config={"ops": {"sip_asset": {"config": {"file_paths": [mets_file_path]}}}},
    )

    assert result.success

    # Retrieve the parsed SIPModel (Dagster >= 1.2.0 allows `asset_value`)
    sip_asset_value = result.asset_value("sip_asset")

    # Now we can assert on the content
    assert sip_asset_value is not None
    assert len(sip_asset_value.intellectual_entities) >= 1

    # Check all DC fields in the first IE
    first_ie = sip_asset_value.intellectual_entities[0]

    # Check DC title
    assert len(first_ie.dc.title) > 0
    print("IE Title:", first_ie.dc.title[0])

    # Check DC creator
    assert len(first_ie.dc.creator) > 0
    print("IE Creator:", first_ie.dc.creator[0])

    # Check DC rights
    assert len(first_ie.dc.rights) > 0
    print("IE Rights:", first_ie.dc.rights[0])

    # Check DC type
    assert len(first_ie.dc.type) >= 0  # Type might be empty but should exist

    # Check DC identifier
    assert len(first_ie.dc.identifier) > 0
    print("IE Identifier:", first_ie.dc.identifier[0])

    # Check metadata in the result
    sip_asset_value = result.asset_value("sip_asset")
    assert sip_asset_value is not None
    assert len(sip_asset_value.intellectual_entities) > 0

    # Check that SIP creation_date is set
    assert sip_asset_value.creation_date is not None
    assert sip_asset_value.creation_date.tzinfo is not None  # Ensure timezone is set

    # Test fixities
    files_value = result.asset_value("files")
    fixities_value = result.asset_value("fixities")

    assert files_value is not None
    assert fixities_value is not None

    # Check that we have files with fixities
    assert len(files_value) > 0
    assert len(fixities_value) > 0

    # Check that each file has required attributes
    for file in files_value:
        assert file.file_id is not None

    # Check that each fixity has a valid file reference
    for fixity in fixities_value:
        assert fixity.file_id is not None
        # Find the corresponding file
        matching_file = next((f for f in files_value if f.file_id == fixity.file_id), None)
        assert matching_file is not None, f"No matching file found for fixity {fixity.fixity_value}"

        # Verify fixity is in file's fixities list
        assert fixity in matching_file.fixities

        # Check fixity format
        assert fixity.fixity_type in ["MD5", "SHA-1", "SHA-256", "SHA-512"]
        assert len(fixity.fixity_value) > 0

    # Test fixities asset metadata
    fixities_events = result.get_asset_materialization_events()
    fixities_result = next(e for e in fixities_events if e.asset_key.path[-1] == "fixities")
    metadata = fixities_result.materialization.metadata

    assert "Fixity Count" in metadata
    assert "Fixities by File" in metadata
    assert "All Fixities" in metadata

    # Check that fixities are properly grouped by file
    fixities_by_file = metadata["Fixities by File"].value
    assert isinstance(fixities_by_file, dict)

    for _file_id, file_data in fixities_by_file.items():
        assert "file_name" in file_data
        assert "file_label" in file_data
        assert "fixities" in file_data
        assert isinstance(file_data["fixities"], list)
        for fixity in file_data["fixities"]:
            assert "type" in fixity
            assert "value" in fixity


def test_sip_pipeline_multiple_files(mets_file_path):
    """
    This test verifies that the pipeline can process multiple METS XML files
    and combine their Intellectual Entities correctly.
    """
    # Use the same file twice to test multiple file handling
    result = materialize(
        assets=[sip_asset, intellectual_entities, representations, files, fixities],
        run_config={
            "ops": {"sip_asset": {"config": {"file_paths": [mets_file_path, mets_file_path]}}}
        },
    )

    assert result.success

    # Get the SIP model and verify it contains combined IEs
    sip_asset_value = result.asset_value("sip_asset")
    assert sip_asset_value is not None

    # Since we used the same file twice, we should have double the IEs
    ie_count = len(sip_asset_value.intellectual_entities)
    assert ie_count > 0 and ie_count % 2 == 0, "IE count should be even when using same file twice"

    # Check metadata
    sip_events = result.get_asset_materialization_events()
    sip_result = next(e for e in sip_events if e.asset_key.path[-1] == "sip_asset")
    metadata = sip_result.materialization.metadata

    # Verify file paths in metadata
    file_paths = metadata["File Paths"].value
    assert len(file_paths) == 2
    assert file_paths[0] == mets_file_path
    assert file_paths[1] == mets_file_path

    # Verify IE count in metadata matches actual count
    assert metadata["Intellectual Entity Count"].value == ie_count
