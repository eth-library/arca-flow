from dagster import Definitions, EnvVar, load_assets_from_modules

from arca.flow import assets
from arca.flow.sensors import (
    TestDataPathResource,
    _default_test_data_path,
    ingest_sip_job,
    xml_file_sensor,
)

all_assets = load_assets_from_modules([assets])

defs = Definitions(
    assets=all_assets,
    jobs=[ingest_sip_job],
    sensors=[xml_file_sensor],
    resources={
        "test_data_path": TestDataPathResource(
            path=EnvVar("DAGSTER_TEST_DATA_PATH").get_value(default=_default_test_data_path)
            or _default_test_data_path,
        ),
    },
)
