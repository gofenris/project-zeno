import pytest
from experiments.gadm_utils import GadmLocation, parse_expected_output

# --- Passing test cases (should be equal) ---
passing_cases = [
    ({"gadm_id": "CHE.9"}, {"gadm_id": "CHE-9"}),
    ({"gadm_id": "CHE.9.1_1"}, {"gadm_id": "CHE-9-1.1"}),
    ({"gadm_id": "CHE.9", "name": "Glarus Süd"}, {"gadm_id": "CHE-9", "name": "Glarus Sud"}),
    ({"gadm_id": "IDN.26.4_1"}, {"gadm_id": "IDN-26-4"}),
    ({"gadm_id": "GBR.1.83_1"}, {"gadm_id": "GBR-1-83"}),
    ({"gadm_id": "DEU.2.44_1"}, {"gadm_id": "DEU-2-44"}),
    ({"gadm_id": "MWI.25.9_1"}, {"gadm_id": "MWI-25-9"}),
    ({"gadm_id": "PRT.15.12_1"}, {"gadm_id": "PRT-15-12"}),
    ({"gadm_id": "FRA.6.1_1"}, {"gadm_id": "FRA-6-1"}),
    ({"gadm_id": "NGA.21.33_1"}, {"gadm_id": "NGA-21-33"}),
]

failing_cases = [
    ({"gadm_id": "CHE.9.1_1"}, {"gadm_id": "CHE-9"}),
    ({"gadm_id": "IDN.26.4_1"}, {"gadm_id": "IDN"}),
    ({"gadm_id": "GBR.1.83_1"}, {"gadm_id": "GBR"}),
    ({"gadm_id": "RUS"}, {"gadm_id": "IDN"}),
    ({"gadm_id": "IDN"}, {"gadm_id": "IDN.21.16_1"}),
    ({"gadm_id": "THA-23"}, {"gadm_id": "BRA-25"}),
    ({"gadm_id": "ZWE.4.5_2"}, {"gadm_id": "ZWE-4-6"}),
    ({"gadm_id": "IDN.17.12_1"}, {"gadm_id": "IDN.21.16_1"}),
    ({"gadm_id": "ITA.10.10_1"}, {"gadm_id": "ITA.10.11_1"}),
    ({"gadm_id": "CHE.9", "name": "Glarus"}, {"gadm_id": "CHE.9", "name": "Glarus Süd"}),
]

@pytest.mark.parametrize("loc1_dict, loc2_dict", passing_cases)
def test_gadm_location_equal(loc1_dict, loc2_dict):
    loc1 = parse_expected_output([loc1_dict])[0]
    loc2 = parse_expected_output([loc2_dict])[0]
    assert loc1 == loc2

@pytest.mark.parametrize("loc1_dict, loc2_dict", passing_cases)
def test_gadm_location_not_equal(loc1_dict, loc2_dict):
    loc1 = parse_expected_output([loc1_dict])[0]
    loc2 = parse_expected_output([loc2_dict])[0]
    assert loc1 != loc2

