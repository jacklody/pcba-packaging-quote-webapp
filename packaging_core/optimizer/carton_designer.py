"""箱型自动设计器：由产品实物尺寸 + 单箱数量直接推导纸箱与内衬设计。

设计公式：
- 刀卡模式：内尺寸 = 格距×列/排/层数量 + 2×端部余量；外尺寸 = 内尺寸 + 2×壁厚
- EPE/EPS 模式：内腔 = 产品 + 2×缓冲厚度；内尺寸 = 内腔 + 2×配合间隙；外尺寸 = 内尺寸 + 2×壁厚

设计结果必须通过 packing_solver.assert_arrangement_feasible 的统一几何校验，
所有统计量由求解器摆放结果派生，本模块不做任何体积估算。
"""

from dataclasses import dataclass
from itertools import permutations

from packaging_core.optimizer.packing_solver import (
    CartonDims,
    PackingArrangement,
    ProductDims,
    _build_arrangement,
)


@dataclass(frozen=True)
class CartonDesign:
    orientation: str
    axis_map: dict[str, str]
    cols: int
    rows: int
    layers: int
    units: int
    inner_mm: dict[str, float]
    outer_mm: dict[str, float]
    outer_volume_mm3: float
    liner: dict
    arrangement: PackingArrangement | None


def _factor_triples(total: int) -> list[tuple[int, int, int]]:
    triples = []
    for cols in range(1, total + 1):
        if total % cols:
            continue
        rest = total // cols
        for rows in range(1, rest + 1):
            if rest % rows:
                continue
            triples.append((cols, rows, rest // rows))
    return triples


def design_divider_cartons(
    product: ProductDims,
    units: int,
    clearance_mm: float = 15,
    card_thickness_mm: float = 3,
    wall_thickness_mm: float = 5,
    end_margin_mm: float = 3,
    max_outer_height_mm: float = 400,
) -> list[CartonDesign]:
    """枚举全部几何可行的刀卡设计箱，按外箱体积升序、平放优先排序。"""
    if units <= 0:
        return []
    product_axes = product.axes
    designs: list[CartonDesign] = []
    for perm in permutations(("L", "S", "T")):
        axis_map = {"x": perm[0], "y": perm[1], "z": perm[2]}
        pitch_x = product_axes[axis_map["x"]] + clearance_mm
        pitch_y = product_axes[axis_map["y"]] + clearance_mm
        pitch_z = product_axes[axis_map["z"]] + clearance_mm
        for cols, rows, layers in _factor_triples(units):
            inner_l = cols * pitch_x + 2 * end_margin_mm
            inner_w = rows * pitch_y + 2 * end_margin_mm
            inner_h = layers * pitch_z + 2 * end_margin_mm
            outer_l = inner_l + 2 * wall_thickness_mm
            outer_w = inner_w + 2 * wall_thickness_mm
            outer_h = inner_h + 2 * wall_thickness_mm
            if outer_h > max_outer_height_mm:
                continue
            arrangement = _build_arrangement(
                axis_map, product_axes, CartonDims(inner_l, inner_w, inner_h), clearance_mm, card_thickness_mm
            )
            if arrangement is None or arrangement.capacity != units:
                continue
            designs.append(
                CartonDesign(
                    orientation=arrangement.orientation,
                    axis_map=dict(axis_map),
                    cols=cols,
                    rows=rows,
                    layers=layers,
                    units=units,
                    inner_mm={"l": round(inner_l, 1), "w": round(inner_w, 1), "h": round(inner_h, 1)},
                    outer_mm={"l": round(outer_l, 1), "w": round(outer_w, 1), "h": round(outer_h, 1)},
                    outer_volume_mm3=round(outer_l * outer_w * outer_h),
                    liner={
                        "type": "divider_grid",
                        "clearance_mm": clearance_mm,
                        "card_thickness_mm": card_thickness_mm,
                        "divider_card_count": len(arrangement.divider_cards),
                        "pitch_mm": {"l": round(pitch_x, 1), "w": round(pitch_y, 1), "h": round(pitch_z, 1)},
                    },
                    arrangement=arrangement,
                )
            )
    return sorted(designs, key=lambda d: (d.outer_volume_mm3, 0 if d.orientation == "flat_stacked" else 1, -d.cols))


def design_divider_carton(product: ProductDims, units: int, **kwargs) -> CartonDesign | None:
    """选最优设计箱：外箱体积最小 → 同体积平放优先 → 沿箱长密排列数更多。"""
    designs = design_divider_cartons(product, units, **kwargs)
    return designs[0] if designs else None


def design_foam_cartons(
    product: ProductDims,
    foam_thickness_mm: float = 20,
    fit_clearance_mm: float = 2,
    wall_thickness_mm: float = 5,
    max_layers: int = 1,
    max_outer_height_mm: float = 1360,
) -> list[CartonDesign]:
    """EPE/EPS 成型缓冲设计箱枚举：每层一个全包络成型腔垂直堆叠，按外箱体积升序。

    层高 = 产品高 + 2×缓冲厚度（单层与单腔口径一致），层数受 max_layers 与外高上限约束。
    """
    designs: list[CartonDesign] = []
    layer_pitch_h = product.height_mm + 2 * foam_thickness_mm
    max_by_height = int((max_outer_height_mm - 2 * wall_thickness_mm - 2 * fit_clearance_mm) // layer_pitch_h)
    top = max(1, min(max_layers, max_by_height))
    for n in range(1, top + 1):
        cavity_l = product.length_mm + 2 * foam_thickness_mm
        cavity_w = product.width_mm + 2 * foam_thickness_mm
        cavity_h = layer_pitch_h
        inner_l = cavity_l + 2 * fit_clearance_mm
        inner_w = cavity_w + 2 * fit_clearance_mm
        inner_h = n * layer_pitch_h + 2 * fit_clearance_mm
        outer_l = inner_l + 2 * wall_thickness_mm
        outer_w = inner_w + 2 * wall_thickness_mm
        outer_h = inner_h + 2 * wall_thickness_mm
        if outer_h > max_outer_height_mm:
            continue
        designs.append(
            CartonDesign(
                orientation="foam_stacked_cavity",
                axis_map={"x": "L", "y": "S", "z": "T"},
                cols=1,
                rows=1,
                layers=n,
                units=n,
                inner_mm={"l": round(inner_l, 1), "w": round(inner_w, 1), "h": round(inner_h, 1)},
                outer_mm={"l": round(outer_l, 1), "w": round(outer_w, 1), "h": round(outer_h, 1)},
                outer_volume_mm3=round(outer_l * outer_w * outer_h),
                liner={
                    "type": "foam_cavity",
                    "foam_thickness_mm": foam_thickness_mm,
                    "fit_clearance_mm": fit_clearance_mm,
                    "layers": n,
                    "cavity_mm": {"l": round(cavity_l, 1), "w": round(cavity_w, 1), "h": round(cavity_h, 1)},
                },
                arrangement=None,
            )
        )
    return designs


def design_foam_carton(
    product: ProductDims,
    foam_thickness_mm: float = 20,
    fit_clearance_mm: float = 2,
    wall_thickness_mm: float = 5,
) -> CartonDesign:
    """EPE/EPS 成型缓冲设计箱（单层便捷入口），口径与多层枚举的第 1 项完全一致。"""
    return design_foam_cartons(
        product,
        foam_thickness_mm=foam_thickness_mm,
        fit_clearance_mm=fit_clearance_mm,
        wall_thickness_mm=wall_thickness_mm,
        max_layers=1,
    )[0]
