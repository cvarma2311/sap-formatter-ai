from src.agents.transformation_agent import resolve_transformations
from src.data_models import TransformationType


def test_probability_threshold_detected():
    t, issues = resolve_transformations("apply if probability > 0.8")
    assert any(cfg.function == TransformationType.PROBABILITY_THRESHOLD for cfg in t)
    cfg = next(cfg for cfg in t if cfg.function == TransformationType.PROBABILITY_THRESHOLD)
    assert cfg.params.get("threshold") == 0.8
    assert issues == []


def test_top_k_detected():
    t, _ = resolve_transformations("take top 2 candidates with min confidence 0.6 ties=keep")
    assert any(cfg.function == TransformationType.TOP_K for cfg in t)
    cfg = next(cfg for cfg in t if cfg.function == TransformationType.TOP_K)
    assert cfg.params.get("k") == 2
    assert cfg.params.get("min_confidence") == 0.6
    assert cfg.params.get("tie_handling") == "keep"


def test_softmax_detected():
    t, _ = resolve_transformations("normalize scores with softmax temperature 0.7")
    assert any(cfg.function == TransformationType.SOFTMAX for cfg in t)
    cfg = next(cfg for cfg in t if cfg.function == TransformationType.SOFTMAX)
    assert cfg.params.get("temperature") == 0.7
