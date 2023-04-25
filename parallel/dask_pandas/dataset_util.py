from collections import defaultdict

import numpy as np
import pandas as pd


def has_csv_header(file):
    df = pd.read_csv(file, nrows=2)
    return df.columns[0] == "ID1"


headers = (
        "ID1", "ID2", "T1", "IND", "PRO",
        "F11", "F12", "F13", "F14",
        "F21A", "F21B", "F22A", "F22B", "F23A", "F23B", "F24A", "F24B", "F25A", "F25B", "F26A", "F26B",
        "D11", "D12",
        "D21A", "D21B", "D21C", "D22A", "D22B",
        "D31",
        "M11", "M12",
        "M21A", "M21B", "M22A", "M22B",
        "M31A", "M31B", "M31C", "M32",
        "M43",
        "M51", "M52", "M53A", "M53B", "M53C", "M53D",
        "C11", "C12", "C13",
        "S21", "S22", "S31",
        "R11", "R12", "R13"
        )  # fmt: skip

# np.iinfo(np.uint8)
# int8  [-128 : 127]
# uint8 [0 : 255]
# int64 [-9223372036854775808 : 9223372036854775807]
# np.finfo(np.float32)
# np.float32 [-3.4028235e+38 : 3.4028235e+38]
# np.float64 np.float_ [-1.7976931348623157e+308 : 1.7976931348623157e+308]

# float最低32，pyarrow的parquet不支持float16
explicit = {
    "ID1": "string[pyarrow]",
    "ID2": "string[pyarrow]",
    "IND": "string[pyarrow]",
    "T1": np.int16,
    "PRO": np.int32,
    "C11": np.float32,
    "C12": np.float32,
    "D21A": np.float32,
    "D21B": np.float32,
    "D21C": np.float32,
    "D22A": np.float64,
    "D22B": np.float64,
    "R12": np.float32,
    "S21": np.float32,
    "S22": np.float32,
    "S31": np.float32,
}
dt = defaultdict(np.float32)
dt.update(explicit)
