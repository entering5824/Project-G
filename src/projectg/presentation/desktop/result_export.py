"""Export the displayed overview without rerunning or changing planner decisions."""
from datetime import datetime
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZipFile, ZIP_DEFLATED


def _text(value) -> str:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return str(value if value is not None else "—").replace("\n", " ").replace("|", "\\|")


def result_report(data: dict, exported_at: str) -> str:
    today = data.get("today") or {}
    lines = ["# ProjectG — Kết quả đánh giá", "", f"Thời điểm xuất: {exported_at}",
             f"Snapshot: {_text(data.get('snapshotId'))}", "",
             "Đây là kết quả đã tải gần nhất trong ứng dụng, không tính lại khi xuất. "
             "Bộ lọc trên màn hình không giới hạn bản xuất. results.json chứa toàn bộ dữ liệu đối chiếu.", "",
             "## Đề xuất chính", ""]
    primary = today.get("primaryTask")
    if primary:
        lines.extend([f"**{_text(primary.get('title'))}**", "",
                      f"Thao tác: {_text(primary.get('actionText'))}",
                      f"Lý do: {_text(primary.get('whySummary'))}",
                      f"Điểm: {_text(primary.get('score'))}", ""])
    else:
        lines.extend([f"Không có đề xuất chính: {_text(today.get('noActionReason'))}", ""])
    for key, title in (("quickActions", "Thao tác nhanh"), ("farming", "Farm hôm nay"),
                       ("unavailable", "Chưa khả dụng"), ("blocked", "Đang chờ")):
        lines.extend([f"## {title}", "", "| Thao tác | Điểm | Trạng thái | Lý do | Tài nguyên cần |",
                      "| --- | --- | --- | --- | --- |"])
        for task in today.get(key) or []:
            lines.append("| " + " | ".join(_text(task.get(field)) for field in
                         ("title", "score", "availability", "whySummary", "requiredCost")) + " |")
        lines.append("")
    lines.extend(["## Cách thực hiện mục tiêu", "", "| Mục tiêu | Hành động |",
                  "| --- | --- |"])
    for task in [*(today.get("farming") or []), *(today.get("unavailable") or []), *(today.get("blocked") or [])]:
        for method in task.get("farmMethods") or []:
            lines.append("| " + _text(task.get("title")) + " | " + _text(method.get("actionText")) + " |")
    lines.extend(["", "## Lộ trình", "", "| Hạng | Nhân vật | Thành phần | Điểm | Trạng thái | Mục tiêu | Chuỗi milestone |",
                  "| --- | --- | --- | --- | --- | --- | --- |"])
    for goal in (data.get("roadmap") or {}).get("global") or []:
        lines.append("| " + " | ".join(_text(value) for value in
                     (goal.get("rank"), (goal.get("character") or {}).get("key"),
                      goal.get("goalType") or goal.get("type"), goal.get("score"), goal.get("status"),
                      goal.get("strategicTarget") or goal.get("target"), goal.get("milestoneChain"))) + " |")
    lines.extend(["", "## Dữ liệu và độ phủ", "", "```json",
                  json.dumps(today.get("coverage") or {}, ensure_ascii=False, indent=2), "```", ""])
    return "\n".join(lines)


REVIEW_TEMPLATE = """# Nhận xét kết quả ProjectG

- Người đánh giá / ngày:
- Tình huống và mục tiêu mong muốn:
- Đề xuất chính có hợp lý không? Vì sao?
- Thứ tự nguồn farm và điểm ưu tiên có phù hợp không?
- Tài nguyên và nhân vật cần ưu tiên khác:
- Mục sai hoặc thiếu (ghi task ID / source ID từ results.json):
- Kết quả mong đợi thay thế:
- Mức độ ảnh hưởng (thấp / vừa / cao):
- Nhận xét về độ rõ ràng và thao tác UI:
"""


def export_results(path: str | Path, data: dict) -> None:
    destination = Path(path)
    exported_at = datetime.now().astimezone().isoformat(timespec="seconds")
    payload = json.dumps({"schemaVersion": 2, "exportedAt": exported_at,
                          "result": data}, ensure_ascii=False, indent=2, allow_nan=False)
    temporary = None
    try:
        with NamedTemporaryFile(dir=destination.parent, suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
        with ZipFile(temporary, "w", compression=ZIP_DEFLATED) as archive:
            archive.writestr("report.md", result_report(data, exported_at).encode("utf-8"))
            archive.writestr("results.json", payload.encode("utf-8"))
            archive.writestr("review.md", REVIEW_TEMPLATE.encode("utf-8"))
        temporary.replace(destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
