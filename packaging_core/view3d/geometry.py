def build_geometry(product_dims, outer_box_dims, pallet_layout) -> dict:
    pallet = pallet_layout["pallet"]
    layers = pallet_layout["layers"]

    layout = {
        "boxes_per_layer": pallet_layout["boxes_per_layer"],
        "layers": layers,
    }
    arrangement = pallet_layout.get("arrangement")
    if arrangement:
        layout["cols"] = arrangement["cols"]
        layout["rows"] = arrangement["rows"]
        layout["orientation"] = arrangement["orientation"]

    return {
        "box_view": {
            "outer_box": outer_box_dims,
            "product": product_dims,
            "buffers": [],
        },
        "pallet_view": {
            "pallet": pallet,
            "box": outer_box_dims,
            "layout": layout,
            "total_height_mm": pallet["h"] + layers * outer_box_dims["h"],
        },
    }
