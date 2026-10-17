from scripts.evaluate import run


def test_reliability_benchmark_reduces_false_links():
    result = run(seed=26151)
    assert result["benchmark"]["cases"] == 60
    assert result["reliability_engine"]["false_link_rate"] < result["baseline"]["false_link_rate"]
    assert result["reliability_engine"]["precision"] > result["baseline"]["precision"]
    assert result["reliability_engine"]["false_positives"] == 0
