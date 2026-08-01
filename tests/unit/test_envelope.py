from npc_planner.models.envelope import Envelope, ExcludedReason, Meta


def test_envelope_initialization() -> None:
    env = Envelope[list[str]](results=["alpha", "beta"])
    assert env.results == ["alpha", "beta"]
    assert env.query == {}
    assert env.context == {}
    assert env.excluded == []
    assert env.warnings == []
    assert env.meta.count == 0


def test_envelope_json_serialization() -> None:
    env = Envelope[list[str]](
        query={"type": "steel"},
        context={"ruleset": "vanilla_gen3"},
        results=["skarmory"],
        excluded=[ExcludedReason(key="gengar", reasons=["banned"])],
        warnings=["thin pool"],
        meta=Meta(count=1, elapsed_ms=12.5),
    )
    json_str = env.model_dump_json()
    assert '"type":"steel"' in json_str
    assert '"skarmory"' in json_str
    assert '"gengar"' in json_str


def test_envelope_json_deserialization() -> None:
    data = {
        "query": {},
        "context": {},
        "results": ["charizard"],
        "excluded": [],
        "warnings": [],
        "meta": {"count": 1, "elapsed_ms": 5.0},
    }
    env = Envelope[list[str]].model_validate(data)
    assert env.results == ["charizard"]
    assert env.meta.count == 1
