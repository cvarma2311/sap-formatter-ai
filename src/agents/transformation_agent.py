import re
from typing import List, Tuple

from src.data_models import TransformationConfig, TransformationType
from src.normalization.transformation_normalizer import normalize_transformations

# Regex helpers
PAD_EXPLICIT = re.compile(r"pad(?:\s+left)?\s*(?:to)?\s*(\d+)", re.IGNORECASE)
PAD_RIGHT_EXPLICIT = re.compile(r"pad\s+right\s*(?:to)?\s*(\d+)", re.IGNORECASE)
PAD_CHAR = re.compile(r"pad(?:\s+left|\s+right)?\s+(?:with|using)\s+'(.+?)'", re.IGNORECASE)
SUBSTRING_EXPLICIT = re.compile(r"(?:first|substring)\s*(\d+)", re.IGNORECASE)
PROB_THRESHOLD = re.compile(r"(?:probability|confidence)\s*(?:>|>=|above|over)\s*([0-9.]+)", re.IGNORECASE)
TOP_K = re.compile(r"top\s*(\d+)|top-k\s*(\d+)", re.IGNORECASE)
TOP_K_MIN_CONF = re.compile(r"(?:min|minimum)\s+(?:confidence|probability)\s*([0-9.]+)", re.IGNORECASE)
TOP_K_TIE = re.compile(r"(?:tie|ties)\s*(?:=|is)?\s*(keep|drop|flag)", re.IGNORECASE)
SOFTMAX = re.compile(r"softmax|normalize\s+scores", re.IGNORECASE)
TEMPERATURE = re.compile(r"temperature\s*([0-9.]+)", re.IGNORECASE)
ROUND_DIGITS = re.compile(r"round\s+(?:to\s+)?(\d+)", re.IGNORECASE)
ADD_NUM = re.compile(r"add\s+([0-9.]+)", re.IGNORECASE)
SUB_NUM = re.compile(r"subtract\s+([0-9.]+)", re.IGNORECASE)
MUL_NUM = re.compile(r"multiply\s+(?:by\s+)?([0-9.]+)", re.IGNORECASE)
DIV_NUM = re.compile(r"divide\s+(?:by\s+)?([0-9.]+)", re.IGNORECASE)


def extract_transformation_fragments(description: str) -> List[str]:
    desc = description.lower()
    fragments: List[str] = []
    if "not blank" in desc or "required" in desc:
        fragments.append("not blank")
    if "trim" in desc:
        fragments.append("trim")
    if "upper" in desc:
        fragments.append("upper")
    if "lower" in desc:
        fragments.append("lower")
    if "concat" in desc or "concatenate" in desc:
        fragments.append("concat")
    if "is text" in desc or "is_text" in desc:
        fragments.append("is text")
    if "is number" in desc or "is_number" in desc:
        fragments.append("is number")
    if PAD_EXPLICIT.search(description):
        fragments.append("pad left")
    if "pad right" in desc or re.search(r"pad\s+right", description, re.IGNORECASE):
        fragments.append("pad right")
    if SUBSTRING_EXPLICIT.search(description):
        fragments.append("substring")
    if "round" in desc:
        fragments.append("round")
    if "add " in desc:
        fragments.append("add")
    if "subtract" in desc:
        fragments.append("subtract")
    if "multiply" in desc:
        fragments.append("multiply")
    if "divide" in desc:
        fragments.append("divide")
    if "coalesce" in desc or "first non-null" in desc:
        fragments.append("coalesce")
    return fragments


def resolve_transformations(description: str) -> Tuple[List[TransformationConfig], List[str]]:
    """
    Returns transformations and issues (needs_review reasons).
    """
    fragments = extract_transformation_fragments(description)
    normalized_types, unknown = normalize_transformations(fragments)
    configs: List[TransformationConfig] = [TransformationConfig(function=t) for t in normalized_types]
    issues = [f"Unrecognized transformation fragment: {frag}" for frag in unknown]
    desc = description.lower()

    # Probabilistic
    if m := PROB_THRESHOLD.search(desc):
        try:
            threshold = float(m.group(1))
        except ValueError:
            threshold = None
        configs.append(
            TransformationConfig(
                function=TransformationType.PROBABILITY_THRESHOLD,
                params={"threshold": threshold} if threshold is not None else {},
            )
        )
    if m := TOP_K.search(desc):
        groups = m.groups()
        k_val = next((g for g in groups if g), None)
        try:
            k = int(k_val) if k_val else None
        except ValueError:
            k = None
        params = {}
        if k is not None:
            params["k"] = k
        if mconf := TOP_K_MIN_CONF.search(desc):
            try:
                params["min_confidence"] = float(mconf.group(1))
            except ValueError:
                pass
        if mtie := TOP_K_TIE.search(desc):
            tie_val = mtie.group(1).lower()
            params["tie_handling"] = tie_val  # keep|drop|flag
        configs.append(TransformationConfig(function=TransformationType.TOP_K, params=params))
    if SOFTMAX.search(desc):
        temp_val = None
        if tm := TEMPERATURE.search(desc):
            try:
                temp_val = float(tm.group(1))
            except ValueError:
                temp_val = None
        configs.append(
            TransformationConfig(
                function=TransformationType.SOFTMAX,
                params={"temperature": temp_val} if temp_val is not None else {},
            )
        )

    # Pad params
    pad_char = None
    if m := PAD_CHAR.search(description):
        pad_char = m.group(1)
    if PAD_EXPLICIT.search(description):
        try:
            pad_len = int(PAD_EXPLICIT.search(description).group(1))
        except Exception:
            pad_len = None
        for cfg in configs:
            if cfg.function == TransformationType.PAD_LEFT:
                if pad_len is not None:
                    cfg.params["pad_length"] = pad_len
                if pad_char:
                    cfg.params["pad_char"] = pad_char
    if PAD_RIGHT_EXPLICIT.search(description):
        try:
            pad_len_r = int(PAD_RIGHT_EXPLICIT.search(description).group(1))
        except Exception:
            pad_len_r = None
        for cfg in configs:
            if cfg.function == TransformationType.PAD_RIGHT:
                if pad_len_r is not None:
                    cfg.params["pad_length"] = pad_len_r
                if pad_char:
                    cfg.params["pad_char"] = pad_char

    # Substring params
    if m := SUBSTRING_EXPLICIT.search(description):
        try:
            length = int(m.group(1))
        except Exception:
            length = None
        for cfg in configs:
            if cfg.function == TransformationType.SUBSTRING and length is not None:
                cfg.params["substring_start"] = 0
                cfg.params["substring_length"] = length

    # Math params
    def assign_param(func_type, key, match_re):
        if m := match_re.search(description):
            try:
                val = float(m.group(1))
            except Exception:
                val = None
            for cfg in configs:
                if cfg.function == func_type and val is not None:
                    cfg.params[key] = val

    assign_param(TransformationType.ROUND, "decimals", ROUND_DIGITS)
    assign_param(TransformationType.ADD, "operand", ADD_NUM)
    assign_param(TransformationType.SUBTRACT, "operand", SUB_NUM)
    assign_param(TransformationType.MULTIPLY, "operand", MUL_NUM)
    assign_param(TransformationType.DIVIDE, "operand", DIV_NUM)

    return configs, issues
