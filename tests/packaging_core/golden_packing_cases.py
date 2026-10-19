"""真实包装金标准案例。

每个案例均来自实际装过箱的数据，求解器输出必须与实测一致。
字段说明：
- product: 产品(含外扩后的有效包络)长 l / 宽 w / 高 h，单位 mm
- carton: 纸箱内尺寸 l / w / h，单位 mm
- expected_units: 实测单箱数量
- expected_orientation: 实测摆法标识
- expected_grid: (列, 排, 层)
"""

GOLDEN_DIVIDER_CASES = [
    {
        "case_id": "VERTICAL-160-95-35-IN-600-400-200",
        "description": "风机/水泵类小板竖放密排，两行每行12块",
        "product": {"l": 160, "w": 95, "h": 35},
        "carton": {"l": 600, "w": 400, "h": 200},
        "expected_units": 24,
        "expected_orientation": "vertical_dense_two_rows",
        "expected_grid": (12, 2, 1),
    },
    {
        "case_id": "FLAT-120-85-40-IN-300-250-180",
        "description": "小板平放刀卡，2列2排3层",
        "product": {"l": 120, "w": 85, "h": 40},
        "carton": {"l": 300, "w": 250, "h": 180},
        "expected_units": 12,
        "expected_orientation": "flat_stacked",
        "expected_grid": (2, 2, 3),
    },
]

# 边界不变量扫描：这些产品 × 全部标准箱，求解器返回的每个摆法都必须几何可行。
BOUNDARY_PRODUCTS = [
    {"id": "SMALL-FAN", "l": 120, "w": 85, "h": 40},
    {"id": "VERTICAL-PUMP", "l": 160, "w": 95, "h": 35},
    {"id": "MID-CONTROLLER", "l": 260, "w": 180, "h": 45},
]

STANDARD_CARTONS = [
    ("STD-01", 300, 250, 180),
    ("STD-02", 350, 300, 200),
    ("STD-03", 400, 300, 220),
    ("STD-04", 400, 300, 260),
    ("STD-05", 450, 350, 230),
    ("STD-06", 450, 350, 280),
    ("STD-07", 500, 400, 240),
    ("STD-08", 500, 400, 280),
    ("STD-09", 500, 400, 320),
    ("STD-10", 530, 380, 260),
    ("STD-11", 530, 380, 300),
    ("STD-12", 550, 400, 260),
    ("STD-13", 580, 420, 300),
    ("STD-14", 600, 400, 250),
    ("STD-15", 600, 400, 300),
]

# 自动设计箱金标准：由产品尺寸+数量直接推导箱体尺寸（内/外），公式化生成，逐项断言。
# inner = 格距×数量 + 2×端部余量；outer = inner + 2×壁厚
GOLDEN_DESIGN_CASES = [
    {
        "case_id": "DESIGN-VERTICAL-160-95-35-24UP",
        "description": "竖放密排24块：12列×50 + 2排×175 + 95立放1层",
        "product": {"l": 160, "w": 95, "h": 35},
        "units": 24,
        "expected_orientation": "vertical_dense_two_rows",
        "expected_grid": (12, 2, 1),
        "expected_inner": {"l": 606, "w": 356, "h": 116},
        "expected_outer": {"l": 616, "w": 366, "h": 126},
    },
    {
        "case_id": "DESIGN-FLAT-120-85-40-12UP",
        "description": "小板平放12块：紧凑平放摆法，须为flat_stacked",
        "product": {"l": 120, "w": 85, "h": 40},
        "units": 12,
        "expected_orientation": "flat_stacked",
    },
]
