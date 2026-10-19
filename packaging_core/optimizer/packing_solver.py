"""刀卡装箱几何求解器。

核心原则：
1. 每件产品都由枚举朝向生成具体坐标，容量由实际摆放结果派生，不做体积估算。
2. 任何一件产品、一张刀卡都必须落在箱内尺寸中，越界直接判不可行。
3. 3D 渲染层只消费本模块输出的坐标，不再自行计算布局。

坐标系：箱内 X=箱长方向，Y=箱宽方向，Z=箱高方向，原点在箱内底面一角。
产品三个维度键：L=长边，S=短边，T=厚度(元器件高度)方向。
"""

from dataclasses import dataclass
from itertools import permutations


@dataclass(frozen=True)
class ProductDims:
    length_mm: float
    width_mm: float
    height_mm: float

    @property
    def axes(self) -> dict[str, float]:
        return {
            "L": max(self.length_mm, self.width_mm),
            "S": min(self.length_mm, self.width_mm),
            "T": self.height_mm,
        }


@dataclass(frozen=True)
class CartonDims:
    length_mm: float
    width_mm: float
    height_mm: float


@dataclass(frozen=True)
class PlacedItem:
    """一件产品在箱内的位置，坐标为占用包围盒中心。"""

    index: int
    x_mm: float
    y_mm: float
    z_mm: float
    dx_mm: float
    dy_mm: float
    dz_mm: float


@dataclass(frozen=True)
class DividerCard:
    """一张刀卡。axis 为卡片法向轴，position 为沿该轴的中心位置。"""

    axis: str
    position_mm: float
    span_a_mm: float
    span_b_mm: float
    thickness_mm: float


@dataclass(frozen=True)
class PackingArrangement:
    orientation: str
    axis_map: dict[str, str]
    cols: int
    rows: int
    layers: int
    capacity: int
    slot_mm: dict[str, float]
    # 产品沿箱 x/y/z 方向的实际占长（经朝向旋转后，不含间隙）；与 slot_mm（含间隙的格距）区分，避免误读
    product_footprint_mm: dict[str, float]
    clearance_mm: float
    items: tuple[PlacedItem, ...]
    divider_cards: tuple[DividerCard, ...]
    used_size_mm: dict[str, float]
    axis_utilization: dict[str, float]
    volume_utilization: float


def _orientation_label(axis_map: dict[str, str], rows: int) -> str:
    vertical_axis = axis_map["z"]
    if vertical_axis == "T":
        return "flat_stacked"
    if vertical_axis == "S":
        return "vertical_dense_two_rows" if rows == 2 else "vertical_short_edge_up"
    return "vertical_long_edge_up"


def _build_arrangement(
    axis_map: dict[str, str],
    product_axes: dict[str, float],
    carton: CartonDims,
    clearance_mm: float,
    card_thickness_mm: float,
) -> PackingArrangement | None:
    dim_x = product_axes[axis_map["x"]]
    dim_y = product_axes[axis_map["y"]]
    dim_z = product_axes[axis_map["z"]]
    pitch_x = dim_x + clearance_mm
    pitch_y = dim_y + clearance_mm
    pitch_z = dim_z + clearance_mm

    cols = int(carton.length_mm // pitch_x)
    rows = int(carton.width_mm // pitch_y)
    layers = int(carton.height_mm // pitch_z)
    if cols <= 0 or rows <= 0 or layers <= 0:
        return None

    used_x = cols * pitch_x
    used_y = rows * pitch_y
    used_z = layers * pitch_z
    if used_x > carton.length_mm or used_y > carton.width_mm or used_z > carton.height_mm:
        return None

    items: list[PlacedItem] = []
    index = 0
    for layer in range(layers):
        for row in range(rows):
            for col in range(cols):
                items.append(
                    PlacedItem(
                        index=index,
                        x_mm=col * pitch_x + pitch_x / 2,
                        y_mm=row * pitch_y + pitch_y / 2,
                        z_mm=layer * pitch_z + pitch_z / 2,
                        dx_mm=dim_x,
                        dy_mm=dim_y,
                        dz_mm=dim_z,
                    )
                )
                index += 1

    cards: list[DividerCard] = []
    for col in range(1, cols):
        cards.append(DividerCard("x", col * pitch_x, used_y, used_z, card_thickness_mm))
    for row in range(1, rows):
        cards.append(DividerCard("y", row * pitch_y, used_x, used_z, card_thickness_mm))
    for layer in range(1, layers):
        cards.append(DividerCard("z", layer * pitch_z, used_x, used_y, card_thickness_mm))

    product_volume = dim_x * dim_y * dim_z * cols * rows * layers
    arrangement = PackingArrangement(
        orientation=_orientation_label(axis_map, rows),
        axis_map=dict(axis_map),
        cols=cols,
        rows=rows,
        layers=layers,
        capacity=cols * rows * layers,
        slot_mm={"l": round(pitch_x, 1), "w": round(pitch_y, 1), "h": round(pitch_z, 1)},
        product_footprint_mm={"l": round(dim_x, 1), "w": round(dim_y, 1), "h": round(dim_z, 1)},
        clearance_mm=clearance_mm,
        items=tuple(items),
        divider_cards=tuple(cards),
        used_size_mm={"l": round(used_x, 1), "w": round(used_y, 1), "h": round(used_z, 1)},
        axis_utilization={
            "x": round(used_x / carton.length_mm, 4),
            "y": round(used_y / carton.width_mm, 4),
            "z": round(used_z / carton.height_mm, 4),
        },
        volume_utilization=round(product_volume / (carton.length_mm * carton.width_mm * carton.height_mm), 4),
    )
    assert_arrangement_feasible(arrangement, carton)
    return arrangement


def enumerate_divider_arrangements(
    product: ProductDims,
    carton: CartonDims,
    clearance_mm: float = 15,
    card_thickness_mm: float = 3,
) -> list[PackingArrangement]:
    """枚举全部 6 种轴向朝向的刀卡规则摆法，只返回几何可行的方案。"""
    product_axes = product.axes
    results: list[PackingArrangement] = []
    for perm in permutations(("L", "S", "T")):
        axis_map = {"x": perm[0], "y": perm[1], "z": perm[2]}
        arrangement = _build_arrangement(axis_map, product_axes, carton, clearance_mm, card_thickness_mm)
        if arrangement is not None:
            results.append(arrangement)
    return results


def solve_divider_arrangement(
    product: ProductDims,
    carton: CartonDims,
    units: int,
    clearance_mm: float = 15,
    card_thickness_mm: float = 3,
) -> PackingArrangement | None:
    """在满足 units 的摆法中选最紧凑合理的一个。

    排序依据：容量浪费最少 → 同紧凑度时平放优先(小板标准稳妥做法) →
    三向平均利用率最高 → 沿箱长密排列数更多(刀卡竖插惯例)。
    """
    feasible = [
        arrangement
        for arrangement in enumerate_divider_arrangements(product, carton, clearance_mm, card_thickness_mm)
        if arrangement.capacity >= units
    ]
    if not feasible:
        return None
    mean_util = lambda a: (a.axis_utilization["x"] + a.axis_utilization["y"] + a.axis_utilization["z"]) / 3
    return min(
        feasible,
        key=lambda a: (
            a.capacity - units,
            0 if a.orientation == "flat_stacked" else 1,
            -mean_util(a),
            -a.cols,
        ),
    )


def assert_arrangement_feasible(arrangement: PackingArrangement, carton: CartonDims) -> None:
    """统一可行性校验：所有产品和刀卡必须在箱内，容量必须与摆放结果一致。"""
    if len(arrangement.items) != arrangement.capacity:
        raise ValueError("capacity 与实际摆放件数不一致")
    if arrangement.capacity != arrangement.cols * arrangement.rows * arrangement.layers:
        raise ValueError("capacity 与列排层乘积不一致")

    bounds = {"x": carton.length_mm, "y": carton.width_mm, "z": carton.height_mm}
    dims = {"x": "dx_mm", "y": "dy_mm", "z": "dz_mm"}
    for item in arrangement.items:
        for axis in ("x", "y", "z"):
            center = getattr(item, f"{axis}_mm")
            half = getattr(item, dims[axis]) / 2
            if center - half < -1e-6 or center + half > bounds[axis] + 1e-6:
                raise ValueError(f"产品超出箱内边界: axis={axis} item={item.index}")

    card_spans = {
        "x": (arrangement.used_size_mm["w"], arrangement.used_size_mm["h"]),
        "y": (arrangement.used_size_mm["l"], arrangement.used_size_mm["h"]),
        "z": (arrangement.used_size_mm["l"], arrangement.used_size_mm["w"]),
    }
    for card in arrangement.divider_cards:
        if not 0 <= card.position_mm <= bounds[card.axis] + 1e-6:
            raise ValueError("刀卡位置超出箱内边界")
        span_a, span_b = card_spans[card.axis]
        if card.span_a_mm > span_a + 1e-6 or card.span_b_mm > span_b + 1e-6:
            raise ValueError("刀卡尺寸超过实际占用包络")
