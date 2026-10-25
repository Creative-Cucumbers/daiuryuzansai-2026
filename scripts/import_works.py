#!/usr/bin/env python3
"""Extract public exhibition data from a Forms XLSX, using Python's standard library."""

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import posixpath
import re
import sys
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import xml.etree.ElementTree as ET
from zipfile import BadZipFile, ZipFile

ROOT = Path(__file__).resolve().parents[1]
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
HEADERS = {
  "timestamp": "タイムスタンプ",
  "name": "氏名:ローマ字",
  "title": "作品名",
  "description": "作品の説明文",
  "url": "作品のURL",
}


def normalized(value):
  return " ".join(unicodedata.normalize("NFKC", value).split())


def initials(name):
  tokens = re.findall(r"[A-Za-z]+", unicodedata.normalize("NFKD", name))
  if not tokens or any(c.isalpha() and not c.isascii() for c in normalized(name)):
    raise ValueError("氏名:ローマ字はアルファベットで入力してください")
  return "".join(token[0].upper() + "." for token in tokens)


def public_url(value):
  if not value:
    return ""
  parsed = urlsplit(value)
  if (parsed.scheme != "https" or not parsed.hostname or parsed.username
      or parsed.password or re.search(r"\s", value)):
    raise ValueError("作品のURLは公開HTTPS URLにしてください")
  if parsed.hostname in ("ai.studio", "aistudio.google.com") and parsed.path.startswith("/apps/"):
    options = {"showAssistant": "true", "showPreview": "true", "fullscreenApplet": "true"}
    query = [(key, item) for key, item in parse_qsl(parsed.query, keep_blank_values=True)
             if key not in options]
    query.extend(options.items())
    return urlunsplit(("https", "aistudio.google.com", parsed.path, urlencode(query), parsed.fragment))
  return value


def screenshot_path(work):
  digest = hashlib.sha256(work["url"].encode()).hexdigest()[:10]
  return f"./assets/screenshots/{work['id']}-{digest}.png"


def read_sheets(path):
  with ZipFile(path) as archive:
    shared = []
    if "xl/sharedStrings.xml" in archive.namelist():
      shared = ["".join(node.itertext()) for node in
                ET.fromstring(archive.read("xl/sharedStrings.xml"))]
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relations = {node.get("Id"): node.get("Target") for node in
                 ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))}
    for sheet in workbook.findall("s:sheets/s:sheet", NS):
      target = relations[sheet.get(f"{{{REL}}}id")]
      target = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
      rows = []
      for row in ET.fromstring(archive.read(target)).findall("s:sheetData/s:row", NS):
        cells = {}
        for cell in row.findall("s:c", NS):
          column = re.match(r"[A-Z]+", cell.get("r")).group()
          value = cell.find("s:v", NS)
          text = value.text or "" if value is not None else ""
          if cell.get("t") == "s":
            text = shared[int(text)]
          elif cell.get("t") == "inlineStr":
            text = "".join(cell.find("s:is", NS).itertext())
          cells[column] = text.strip()
        rows.append((int(row.get("r")), cells))
      yield sheet.get("name"), rows


def timestamp(value):
  try:
    return float(value)
  except ValueError:
    for fmt in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S"):
      try:
        return (datetime.strptime(value, fmt) - datetime(1899, 12, 30)).total_seconds() / 86400
      except ValueError:
        continue
  raise ValueError("タイムスタンプを解釈できません")


def extract(path, sheet_name=None):
  records = []
  errors = []
  for sheet, rows in read_sheets(path):
    if sheet_name and sheet != sheet_name:
      continue
    columns = None
    for row_number, cells in rows:
      if columns is None:
        candidates = {key: [column for column, text in cells.items()
                           if normalized(text).startswith(prefix)]
                      for key, prefix in HEADERS.items()}
        if all(len(matches) == 1 for matches in candidates.values()):
          columns = {key: matches[0] for key, matches in candidates.items()}
        continue
      if not any(cells.values()):
        continue
      source = {"sheet": sheet, "row": row_number}
      try:
        fields = {key: cells.get(column, "").strip() for key, column in columns.items()}
        if not all(fields[key] for key in ("name", "title", "description", "timestamp")):
          raise ValueError("ローマ字氏名・作品名・説明・タイムスタンプは必須です")
        fields["initials"] = initials(fields["name"])
        fields["url"] = public_url(fields["url"])
        identity = normalized(fields["name"]).casefold()
        records.append({**fields, "identity": identity,
                        "time": timestamp(fields["timestamp"]), "source": source})
      except ValueError as error:
        errors.append({**source, "error": str(error)})
  if errors:
    raise ValueError(json.dumps(errors, ensure_ascii=False, indent=2))
  if not records:
    raise ValueError("回答がありません。列見出し、シート名、入力ファイルを確認してください")
  grouped = {}
  for record in records:
    grouped.setdefault(record["identity"], []).append(record)
  works, duplicates, warnings = [], [], []
  for identity, submissions in grouped.items():
    # Later worksheet/row wins when timestamps are identical.
    chosen = max(enumerate(submissions), key=lambda item: (item[1]["time"], item[0]))[1]
    work_id = "work-" + hashlib.sha256(identity.encode()).hexdigest()[:12]
    work = {
      "id": work_id,
      "initials": chosen["initials"],
      "title": chosen["title"],
      "description": chosen["description"],
      "url": chosen["url"],
      "sample": False,
    }
    image = screenshot_path(work)
    if work["url"] and (ROOT / image).is_file():
      work["screenshot"] = image
    works.append(work)
    if len(submissions) > 1:
      duplicates.append({"id": work_id, "initials": chosen["initials"],
                         "selected": chosen["source"],
                         "discarded": [row["source"] for row in submissions if row is not chosen],
                         "changedFields": [key for key in ("title", "description", "url")
                                           if len({r[key] for r in submissions}) > 1]})
    if not work["url"]:
      warnings.append({"id": work_id, "source": chosen["source"], "warning": "URL未入力。リンク非表示"})
    if len(work["title"]) > 40 or len(work["description"]) > 180:
      warnings.append({"id": work_id, "source": chosen["source"], "warning": "フォームの文字数目安を超過。原文を維持"})
  report = {"answers": len(records), "works": len(works), "duplicates": duplicates, "warnings": warnings}
  return works, report


def write_json(path, value):
  path.parent.mkdir(parents=True, exist_ok=True)
  temporary = path.with_suffix(path.suffix + ".tmp")
  temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
  temporary.replace(path)


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("xlsx", nargs="?", type=Path, help="未指定時は input/ とルートから1件を検出")
  parser.add_argument("--sheet", help="取り込むシート名。未指定時は見出しが一致する全シート")
  parser.add_argument("--check", action="store_true", help="確認のみ。ファイルは更新しない")
  args = parser.parse_args()
  try:
    path = args.xlsx
    if path is None:
      files = [p for folder in (ROOT, ROOT / "input") for p in folder.glob("*.xlsx")
               if not p.name.startswith("~$")]
      if len(files) != 1:
        raise ValueError("Excelが0件または複数あります。入力ファイルを引数で指定してください")
      path = files[0]
    works, report = extract(path, args.sheet)
    if not args.check:
      write_json(ROOT / "data/works.json", works)
      write_json(ROOT / ".local/import-report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0
  except (ValueError, OSError, KeyError, ET.ParseError, BadZipFile) as error:
    print(f"取り込みを中止しました（既存データは維持）: {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
  sys.exit(main())
