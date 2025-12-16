from typing import Optional

from src.data_models import ChunkingSpec


def normalize_chunking(chunking: Optional[ChunkingSpec]) -> Optional[ChunkingSpec]:
    if not chunking:
        return None
    size = max(chunking.chunk_size, 1)
    ordinal_start = max(chunking.ordinal_start, 1)
    ordinal_inc = max(chunking.ordinal_increment, 1)
    return ChunkingSpec(
        chunk_size=size,
        ordinal_start=ordinal_start,
        ordinal_increment=ordinal_inc,
        map_to=chunking.map_to,
    )

