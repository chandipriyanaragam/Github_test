import json
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


run_dir = Path(sys.argv[1]).resolve()
data = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
results = data["results"]
counts = {status: sum(row["status"] == status for row in results) for status in ("PASS", "FAIL", "BLOCKED", "UNAVAILABLE", "PARTIAL")}


def col(n):
    out = ""
    while n:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def worksheet(rows):
    row_xml = []
    for ri, row in enumerate(rows, 1):
        cells = []
        for ci, value in enumerate(row, 1):
            ref = f"{col(ci)}{ri}"
            value = "" if value is None else str(value)
            cells.append(f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{escape(value)}</t></is></c>')
        row_xml.append(f'<row r="{ri}">{"".join(cells)}</row>')
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>' + "".join(row_xml) + "</sheetData></worksheet>"


summary = [
    ["LegalLens UI and backend E2E test report", "Value"],
    ["Run date", data["run_date"]],
    ["Browser", "Headless Microsoft Edge via Chrome DevTools Protocol"],
    ["Model mode", data["model_mode"]],
    ["Pass", counts["PASS"]], ["Fail", counts["FAIL"]], ["Blocked", counts["BLOCKED"]],
    ["Unavailable", counts["UNAVAILABLE"]], ["Partial", counts["PARTIAL"]],
    ["Interpretation", "Workflow results use a deterministic local stub. They verify UI, extraction, persistence and citation plumbing, not real model quality."],
    ["Live provider check", "BLOCKED: configured OpenAI credential returned HTTP 401 invalid_api_key; no real model response was evaluated."],
    ["PDF upload", "BLOCKED: pypdf is absent from the active backend virtual environment."],
]
cases = [["Case ID", "Test case", "Status", "Observed result", "Screenshot"]]
evidence = [["Case ID", "Artifact", "Description"]]
for item in results:
    shot = item.get("screenshot", "")
    cases.append([item["id"], item["title"], item["status"], item.get("observed", ""), shot])
    if shot:
        evidence.append([item["id"], shot, f'Screenshot evidence for {item["title"]}'])
for filename, desc in (("results.json", "Machine-readable run results"), ("browser-errors.json", "Browser exception capture")):
    evidence.append(["RUN", filename, desc])

worksheets = [summary, cases, evidence]
names = ["Summary", "Test Cases", "Evidence"]
content_types = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>' + ''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1, 4)) + '</Types>'
workbook = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>' + ''.join(f'<sheet name="{name}" sheetId="{i}" r:id="rId{i}"/>' for i, name in enumerate(names, 1)) + '</sheets></workbook>'
rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
sheet_rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + ''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1, 4)) + '</Relationships>'
out = run_dir / "LegalLens-E2E-Results.xlsx"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("[Content_Types].xml", content_types)
    zf.writestr("_rels/.rels", rels)
    zf.writestr("xl/workbook.xml", workbook)
    zf.writestr("xl/_rels/workbook.xml.rels", sheet_rels)
    for i, rows in enumerate(worksheets, 1):
        zf.writestr(f"xl/worksheets/sheet{i}.xml", worksheet(rows))
print(out)
