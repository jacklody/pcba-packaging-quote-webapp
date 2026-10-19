import csv
import io

BOM_HEADERS = ["项目", "规格", "数量", "单价(元)", "成本(元/台)", "置信度"]


def result_to_csv(result: dict) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")

    recommended = result["recommended"]
    writer.writerow(["推荐方案", recommended["summary"]])
    writer.writerow(["台/箱", recommended["units_per_box"]])
    writer.writerow(["箱/托", recommended["boxes_per_pallet"]])
    writer.writerow(["台/托", recommended["units_per_pallet"]])
    writer.writerow(["总成本(元/台)", recommended["total_cost_per_unit"]])
    writer.writerow([])

    writer.writerow(BOM_HEADERS)
    total = 0.0
    for row in result["bom"]:
        writer.writerow([row["item"], row["spec"], row["qty"], row["unit_price"], row["cost_per_unit"], row["confidence"]])
        total += row["cost_per_unit"]
    writer.writerow(["合计", "", "", "", round(total, 2), ""])

    return buffer.getvalue()


def write_result_csv(result: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as file:
        file.write(result_to_csv(result))
