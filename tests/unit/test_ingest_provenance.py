from npc_planner.db.session import create_connection, init_db
from npc_planner.ingest.provenance import (
    entity_confidence,
    record_field,
    uncertainties,
)


def test_record_field_and_entity_confidence() -> None:
    conn = create_connection(":memory:")
    init_db(conn)

    prov_id1 = record_field(
        conn=conn,
        entity_type="form",
        entity_key="skarmory",
        field_path="type_1",
        source_type="official_baseline",
        value="steel",
        confidence=1.0,
        source_file="forms.json",
    )
    prov_id2 = record_field(
        conn=conn,
        entity_type="form",
        entity_key="skarmory",
        field_path="base_hp",
        source_type="rom_extract",
        value=65,
        confidence=0.8,
        source_file="forms.json",
    )

    assert prov_id1 > 0
    assert prov_id2 > prov_id1

    conf = entity_confidence(conn, "form", "skarmory")
    assert conf == 0.8
    conn.close()


def test_uncertainties_query() -> None:
    conn = create_connection(":memory:")
    init_db(conn)

    record_field(
        conn=conn,
        entity_type="move",
        entity_key="custom_move",
        field_path="power",
        source_type="inferred",
        value=80,
        confidence=0.4,
    )
    record_field(
        conn=conn,
        entity_type="move",
        entity_key="tackle",
        field_path="power",
        source_type="official_baseline",
        value=40,
        confidence=1.0,
    )

    uncert = uncertainties(conn, min_confidence=0.5)
    assert len(uncert) == 1
    assert uncert[0]["entity_key"] == "custom_move"
    assert uncert[0]["confidence"] == 0.4
    conn.close()
