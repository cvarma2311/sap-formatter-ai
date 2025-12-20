from src.agents.transformation_agent import resolve_transformations
from src.data_models import TransformationType


def get_cfg(transformations, func):
    return next(cfg for cfg in transformations if cfg.function == func)


def test_pad_left_no_params():
    t, _ = resolve_transformations("pad left to 4")
    cfg = get_cfg(t, TransformationType.PAD_LEFT)
    # Params not extracted yet; ensure function detected
    assert cfg.function == TransformationType.PAD_LEFT


def test_pad_right_detected():
    t, _ = resolve_transformations("pad right to 3")
    cfg = get_cfg(t, TransformationType.PAD_RIGHT)
    assert cfg.function == TransformationType.PAD_RIGHT


def test_substring_detected():
    t, _ = resolve_transformations("take first 5 characters")
    cfg = get_cfg(t, TransformationType.SUBSTRING)
    assert cfg.function == TransformationType.SUBSTRING
