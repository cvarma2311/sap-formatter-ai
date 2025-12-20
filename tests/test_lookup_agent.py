from pathlib import Path

from src.agents.lookup_agent import parse_lookup_entries
from src.data_models import LookupRuleType, LookupSourceType


def test_lookup_agent_parses_defaults_and_expected(tmp_path: Path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("Quantity,unitCode,CharacteristicQuantity,CharacteristicQuantityTypeCode\n1,EA,GRM,NET_WEIGHT\n")

    desc = (
        "1.Default Quantity as 'EA' (Product->QuantityCharacteristic->Quantity) and unitCode as '1.0'\n"
        "2. Default CharacteristicQuantity as 'GRM' (Product->QuantityCharacteristic->CharacteristicQuantity) and Map the attribute value in unitCode\n"
        "3. Default CharacteristicQuantityTypeCode as 'NET_WEIGHT' (Product->QuantityCharacteristic->CharacteristicQuantityTypeCode)"
    )

    lookups = parse_lookup_entries(desc, csv_path=csv_path)
    assert len(lookups) >= 3

    defaults = [l for l in lookups if l.rule_type == LookupRuleType.DEFAULT]
    assert any(d.cond_value == "EA" for d in defaults)
    assert any(d.field in {"unitCode", "Quantity"} for d in defaults)
    assert all(d.source_type in {LookupSourceType.CSV_HINT, LookupSourceType.TABLE} for d in defaults)

    expected = [l for l in lookups if l.rule_type == LookupRuleType.EXPECTED]
    assert expected, "Expected at least one expected-value lookup entry"
    assert expected[0].expected_result == "ATTRIBUTE_VALUE"
