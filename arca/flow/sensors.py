"""
Dagster sensors for automated METS XML processing.

This module implements the monitoring and triggering system for the METS XML
processing pipeline. It watches for new XML files and automatically initiates
the processing workflow when files are detected.

Components:
    - xml_file_sensor: Monitors test_data directory for XML files
    - ingest_sip_job: Job definition for processing detected files
    - TestDataPathResource: ConfigurableResource for test data path

Configuration:
    - Monitoring interval: 30 seconds
    - Default status: Running
    - Target directory: test_data in the project root
    - File pattern: *.xml

The sensor system provides:
    - Automated workflow triggering
    - File-specific run configuration
    - Error handling and skip conditions
    - Run deduplication through run keys
    - Configurable monitoring behavior

Usage:
    The sensor runs automatically when the Dagster daemon is active:
    ```bash
    dagster dev
    ```
"""

from pathlib import Path

from dagster import (
    ConfigurableResource,
    DefaultSensorStatus,
    RunConfig,
    RunRequest,
    SensorEvaluationContext,
    SkipReason,
    define_asset_job,
    sensor,
)

from .assets import all_assets

# Define the asset materialization job that processes METS XML files into SIPs
# This job ensures all assets are processed in the correct dependency order
# Config is provided by the sensor, or via the Dagster UI launchpad for manual runs
ingest_sip_job = define_asset_job(
    "ingest_sip_job",
    selection=all_assets,
)

# Default test data path for local development (relative to source)
_default_test_data_path = str(Path(__file__).parent / "tests" / "test_data")


class TestDataPathResource(ConfigurableResource):
    """
    Resource providing the test data directory path.

    Uses EnvVar so the environment variable is resolved at runtime rather than
    code load time. This is important for K8s deployments where the env var
    may differ between the code server and run pods.

    Configuration:
        - Local dev: Uses default path relative to source
        - K8s: Set DAGSTER_TEST_DATA_PATH=/arca/flow/tests/test_data
    """

    path: str


@sensor(job=ingest_sip_job, minimum_interval_seconds=30, default_status=DefaultSensorStatus.RUNNING)
def xml_file_sensor(
    context: SensorEvaluationContext,
    test_data_path: TestDataPathResource,
):
    """
    Monitors the test_data directory for XML files and triggers asset materialization.

    Args:
        context: Sensor evaluation context provided by Dagster.
        test_data_path: Resource providing the test data directory path.
    """
    data_path = Path(test_data_path.path)

    if not data_path.exists():
        yield SkipReason(f"Test data directory {data_path} does not exist")
        return

    # Get all XML files in the directory
    xml_files = [f for f in data_path.glob("*.xml")]

    if not xml_files:
        yield SkipReason("No XML files found in the test data directory")
        return

    # Create a run request for each XML file
    for xml_file in xml_files:
        yield RunRequest(
            run_key=f"xml_file_{xml_file.name}",
            run_config=RunConfig(
                ops={"sip_asset": {"config": {"file_paths": [str(xml_file.absolute())]}}}
            ),
        )
