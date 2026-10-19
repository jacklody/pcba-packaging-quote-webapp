from dataclasses import dataclass, field
from typing import Any, Literal

ConfidenceGrade = Literal["A", "B", "C", "D"]


@dataclass(frozen=True)
class ProductInput:
    name: str
    product_class: str
    length_mm: float
    width_mm: float
    height_mm: float
    weight_kg: float
    fragility: str
    esd_sensitive: bool
    has_heat_sink: bool = False
    has_sheet_metal: bool = False
    has_wire_harness: bool = False
    has_tall_fragile_components: bool = False

    def __post_init__(self) -> None:
        if self.product_class not in {"pcba", "assembly"}:
            raise ValueError("product_class must be one of: pcba, assembly")
        for field_name in ("length_mm", "width_mm", "height_mm", "weight_kg"):
            if getattr(self, field_name) <= 0:
                raise ValueError(f"{field_name} must be positive")


@dataclass(frozen=True)
class BusinessInput:
    annual_qty: int
    design_frozen: bool
    allow_mold: bool


@dataclass(frozen=True)
class LogisticsInput:
    ship_mode: str
    destination: str
    logistics_product: str
    pallet_size: str
    max_pallet_height_mm: float
    max_pallet_weight_kg: float
    origin: str = "青岛市"
    freight_discount: float = 1.0
    pallet_material: str = "wood"
    pallet_reusable: bool = False
    pallet_height_mm: float = 120.0
    supported_logistics_products: list[str] = field(default_factory=lambda: ["特惠普运", "次日达"])
    available_destinations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.logistics_product not in self.supported_logistics_products:
            raise ValueError("logistics_product must be one of supported_logistics_products")
        for field_name in ("max_pallet_height_mm", "max_pallet_weight_kg", "pallet_height_mm"):
            if getattr(self, field_name) <= 0:
                raise ValueError(f"{field_name} must be positive")
        if self.freight_discount <= 0 or self.freight_discount > 1:
            raise ValueError("freight_discount must be > 0 and <= 1")


@dataclass(frozen=True)
class AccessoryOptionsInput:
    stretch_film: bool = True
    packing_band: bool = True
    corner_protector: bool = True
    edge_protector: bool = True


@dataclass(frozen=True)
class CartonInput:
    layers: int = 5
    flute: str = "BC"
    thickness_mm: float = 7.0
    max_load_kg: float = 35.0
    stack_safety_factor: float = 1.5

    def __post_init__(self) -> None:
        for field_name in ("layers", "thickness_mm", "max_load_kg", "stack_safety_factor"):
            if getattr(self, field_name) <= 0:
                raise ValueError(f"{field_name} must be positive")


@dataclass(frozen=True)
class CartonCandidateInput:
    carton_id: str
    length_mm: float
    width_mm: float
    height_mm: float
    modularity: str = ""
    typical_use: str = ""
    source: Literal["standard", "custom", "generated"] = "custom"

    def __post_init__(self) -> None:
        if not self.carton_id:
            raise ValueError("carton_id must be non-empty")
        for field_name in ("length_mm", "width_mm", "height_mm"):
            if getattr(self, field_name) <= 0:
                raise ValueError(f"{field_name} must be positive")
        if self.source not in {"standard", "custom", "generated"}:
            raise ValueError("source must be one of: standard, custom, generated")


@dataclass(frozen=True)
class DimensionAllowanceInput:
    length_mm: float = 0.0
    width_mm: float = 0.0
    height_mm: float = 0.0

    def __post_init__(self) -> None:
        for field_name in ("length_mm", "width_mm", "height_mm"):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} must be non-negative")


@dataclass(frozen=True)
class CostOverridesInput:
    eps_base_fee: float | None = None
    eps_vol_fee: float | None = None
    epe_unit_price_per_m3: float | None = None
    corrugated_box_price: float | None = None
    corrugated_material_yuan_per_m2: float | None = None
    pallet_purchase_price: float | None = None
    pallet_reuse_count: int | None = None
    stretch_film_unit_price_per_kg: float | None = None
    stretch_film_kg_per_pallet: float | None = None
    packing_band_price_per_pallet: float | None = None
    mold_amortize_per_unit: float | None = None
    mold_tooling_cost: float | None = None
    mold_amortize_qty: int | None = None
    anti_static_bag_price_per_unit: float | None = None
    corner_protector_price_per_pallet: float | None = None
    edge_protector_price_per_pallet: float | None = None

    def applied_fields(self) -> list[str]:
        return sorted(field for field in self.__dataclass_fields__ if getattr(self, field) is not None)

    def __post_init__(self) -> None:
        for field_name in self.__dataclass_fields__:
            value = getattr(self, field_name)
            if value is not None and value <= 0:
                raise ValueError(f"cost override {field_name} must be positive")


@dataclass(frozen=True)
class ConstraintsInput:
    units_per_box_candidates: list[int] = field(default_factory=lambda: [1, 2, 4, 6])
    max_box_weight_kg: float = 25.0
    config_version: str = "2026-10-13"
    auto_units_per_box: bool = True
    auto_design_carton: bool = True
    override_units_per_box: int | None = None
    packaging_mode: Literal["auto", "divider", "foam"] = "auto"
    carton: CartonInput = field(default_factory=CartonInput)
    carton_candidates: list[CartonCandidateInput] = field(default_factory=list)
    dimension_allowance: DimensionAllowanceInput = field(default_factory=DimensionAllowanceInput)
    accessories: AccessoryOptionsInput = field(default_factory=AccessoryOptionsInput)
    cost_overrides: CostOverridesInput = field(default_factory=CostOverridesInput)

    def __post_init__(self) -> None:
        if self.packaging_mode not in {"auto", "divider", "foam"}:
            raise ValueError("packaging_mode must be one of: auto, divider, foam")
        if self.max_box_weight_kg <= 0:
            raise ValueError("max_box_weight_kg must be positive")
        if any(n <= 0 for n in self.units_per_box_candidates):
            raise ValueError("units_per_box_candidates must be positive")
        if self.override_units_per_box is not None and self.override_units_per_box <= 0:
            raise ValueError("override_units_per_box must be positive")


@dataclass(frozen=True)
class PackagingRequest:
    product: ProductInput
    business: BusinessInput
    logistics: LogisticsInput
    constraints: ConstraintsInput


@dataclass(frozen=True)
class RiskFlag:
    level: str
    type: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
