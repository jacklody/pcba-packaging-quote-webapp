from packaging_core.optimizer.packing_solver import (
    CartonDims,
    ProductDims,
    assert_arrangement_feasible,
    enumerate_divider_arrangements,
    solve_divider_arrangement,
)


CLEARANCE = 15


def test_real_vertical_case_160x95x35_in_600x400x200_packs_24():
    product = ProductDims(160, 95, 35)
    carton = CartonDims(600, 400, 200)

    arrangement = solve_divider_arrangement(product, carton, units=24, clearance_mm=CLEARANCE)

    assert arrangement is not None
    assert arrangement.capacity == 24
    assert (arrangement.cols, arrangement.rows, arrangement.layers) == (12, 2, 1)
    assert arrangement.orientation == "vertical_dense_two_rows"
    assert arrangement.axis_map == {"x": "T", "y": "L", "z": "S"}
    assert arrangement.slot_mm == {"l": 50, "w": 175, "h": 110}
    assert len(arrangement.items) == 24
    assert_arrangement_feasible(arrangement, carton)


def test_small_board_flat_stacked_in_300x250x180_packs_12():
    product = ProductDims(120, 85, 40)
    carton = CartonDims(300, 250, 180)

    arrangement = solve_divider_arrangement(product, carton, units=12, clearance_mm=CLEARANCE)

    assert arrangement is not None
    assert arrangement.capacity == 12
    assert (arrangement.cols, arrangement.rows, arrangement.layers) == (2, 2, 3)
    assert arrangement.orientation == "flat_stacked"
    assert len(arrangement.items) == 12
    assert_arrangement_feasible(arrangement, carton)


def test_every_placed_item_and_divider_stays_inside_carton():
    product = ProductDims(160, 95, 35)
    carton = CartonDims(600, 400, 200)

    arrangements = enumerate_divider_arrangements(product, carton, clearance_mm=CLEARANCE)

    assert arrangements
    for arrangement in arrangements:
        assert_arrangement_feasible(arrangement, carton)


def test_capacity_always_equals_cols_rows_layers_and_item_count():
    product = ProductDims(120, 85, 40)
    carton = CartonDims(350, 300, 200)

    for arrangement in enumerate_divider_arrangements(product, carton, clearance_mm=CLEARANCE):
        assert arrangement.capacity == arrangement.cols * arrangement.rows * arrangement.layers
        assert len(arrangement.items) == arrangement.capacity


def test_utilization_is_between_zero_and_one():
    product = ProductDims(160, 95, 35)
    carton = CartonDims(600, 400, 200)
    arrangement = solve_divider_arrangement(product, carton, units=24, clearance_mm=CLEARANCE)

    for axis in ("x", "y", "z"):
        assert 0 < arrangement.axis_utilization[axis] <= 1
    assert 0 < arrangement.volume_utilization <= 1
    assert arrangement.axis_utilization["x"] == 1.0


def test_returns_none_when_product_cannot_fit():
    product = ProductDims(420, 320, 90)
    carton = CartonDims(300, 250, 180)

    assert solve_divider_arrangement(product, carton, units=1, clearance_mm=CLEARANCE) is None


def test_prefers_compact_capacity_over_oversized_layout():
    product = ProductDims(160, 95, 35)
    carton = CartonDims(600, 400, 200)

    arrangement = solve_divider_arrangement(product, carton, units=24, clearance_mm=CLEARANCE)

    # 平放可装 36 台但容量浪费，竖放正好 24 台应被选中
    assert arrangement.capacity == 24
    assert arrangement.layers == 1


def test_divider_cards_match_grid_boundaries():
    product = ProductDims(160, 95, 35)
    carton = CartonDims(600, 400, 200)
    arrangement = solve_divider_arrangement(product, carton, units=24, clearance_mm=CLEARANCE)

    x_cards = [card for card in arrangement.divider_cards if card.axis == "x"]
    y_cards = [card for card in arrangement.divider_cards if card.axis == "y"]
    z_cards = [card for card in arrangement.divider_cards if card.axis == "z"]

    assert len(x_cards) == 11
    assert len(y_cards) == 1
    assert len(z_cards) == 0
    assert x_cards[0].position_mm == 50
