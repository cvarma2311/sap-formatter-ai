from typing import Optional

from src.data_models import DataType


TYPE_MAP = {
    "CHAR": DataType.STRING,
    "STRING": DataType.STRING,
    "STR": DataType.STRING,
    "NUMC": DataType.INTEGER,
    "INT": DataType.INTEGER,
    "INTEGER": DataType.INTEGER,
    "DEC": DataType.DECIMAL,
    "CURR": DataType.DECIMAL,
    "DECIMAL": DataType.DECIMAL,
    "DATE": DataType.DATE,
    "DATS": DataType.DATE,
    "BOOL": DataType.BOOLEAN,
    "BOOLEAN": DataType.BOOLEAN,
}


def normalize_type(raw_type: Optional[str]) -> DataType:
    if not raw_type:
        return DataType.UNKNOWN
    upper = raw_type.strip().upper()
    return TYPE_MAP.get(upper, DataType.UNKNOWN)

