import csv
import re
from pathlib import Path
from typing import List, Optional


def _normalize(s: str) -> str:
    return re.sub(r"[\s_\-]+", " ", s.strip().lower())


def best_header_match(csv_path: Path, target_field: str) -> Optional[str]:
    if not csv_path.exists():
        return None
    norm_target = _normalize(target_field)
    headers: List[str] = []
    with csv_path.open() as f:
        reader = csv.reader(f)
        for row in reader:
            headers = row
            break
    if not headers:
        return None
    scored = []
    for h in headers:
        norm_h = _normalize(h)
        if norm_h == norm_target:
            return h
        if norm_target in norm_h or norm_h in norm_target:
            scored.append((0.9, h))
        else:
            # simple overlap score
            overlap = len(set(norm_target.split()) & set(norm_h.split()))
            score = overlap / max(len(norm_h.split()), 1)
            scored.append((score, h))
    scored.sort(key=lambda x: x[0], reverse=True)
    top_score, top_header = scored[0]
    return top_header if top_score >= 0.4 else None

