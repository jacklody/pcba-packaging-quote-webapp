from packaging_core.view3d.geometry import build_geometry


def test_build_geometry_returns_web_3d_contract():
    product_dims = {"l": 620, "w": 360, "h": 95}
    outer_box_dims = {"l": 665, "w": 393, "h": 405}
    pallet_layout = {
        "boxes_per_layer": 3,
        "layers": 3,
        "pallet": {"l": 1100, "w": 1100, "h": 120},
    }

    geometry = build_geometry(product_dims, outer_box_dims, pallet_layout)

    assert geometry == {
        "box_view": {
            "outer_box": outer_box_dims,
            "product": product_dims,
            "buffers": [],
        },
        "pallet_view": {
            "pallet": pallet_layout["pallet"],
            "box": outer_box_dims,
            "layout": {
                "boxes_per_layer": 3,
                "layers": 3,
            },
            "total_height_mm": 1335,
        },
    }


def test_build_geometry_passes_through_arrangement():
    pallet_layout = {
        "boxes_per_layer": 2,
        "layers": 3,
        "pallet": {"l": 1100, "w": 1100, "h": 120},
        "arrangement": {"cols": 1, "rows": 2, "orientation": "A"},
    }

    geometry = build_geometry({"l": 620, "w": 360, "h": 95}, {"l": 665, "w": 393, "h": 405}, pallet_layout)

    assert geometry["pallet_view"]["layout"]["cols"] == 1
    assert geometry["pallet_view"]["layout"]["rows"] == 2
    assert geometry["pallet_view"]["layout"]["orientation"] == "A"
