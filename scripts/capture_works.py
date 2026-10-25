#!/usr/bin/env python3
"""Capture app screens for review; approve selected screenshots for the exhibition."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

from import_works import ROOT, screenshot_path, write_json

REPORT = ROOT / ".local/capture-report.json"


def write_report(report):
  write_json(REPORT, report)
  labels = {"approved": "掲載済み", "needs-review": "画像の目視確認待ち",
            "needs-login": "ログインが必要", "http-error": "HTTPエラー",
            "blank-screen": "白画面", "needs-attention": "要対応",
            "missing-url": "URL未入力", "failed": "取得失敗"}
  lines = ["# キャプチャ状況（ローカル専用）", "",
           "| 作品 | ID | 状況 | メモ |", "| --- | --- | --- | --- |"]
  for entry in report.values():
    values = [entry["title"], entry["id"], labels.get(entry["state"], entry["state"]), entry.get("note", "")]
    lines.append("| " + " | ".join(v.replace("|", "／").replace("\n", " ") for v in values) + " |")
  REPORT.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def cli(*args):
  command = ["playwright-cli", "-s=capture", *args]
  result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=60)
  if result.returncode or "### Error" in result.stdout:
    raise RuntimeError((result.stderr or result.stdout)[-2000:])
  return result.stdout


def capture(work):
  destination = ROOT / ".local/captures" / Path(screenshot_path(work)).name
  destination.parent.mkdir(parents=True, exist_ok=True)
  # JSON is embedded in JavaScript, never interpolated into a shell command.
  runner = ROOT / ".local/capture-runner.js"
  runner.write_text("""async page => {
  await page.setViewportSize({ width: 1280, height: 900 });
  const response = await page.goto(URL_VALUE, { waitUntil: 'domcontentloaded', timeout: 25000 });
  await page.waitForLoadState('networkidle', { timeout: 7000 }).catch(() => {});
  await page.waitForFunction(() => document.body?.innerText.trim().length > 0, null, { timeout: 10000 }).catch(() => {});
  await page.evaluate(() => document.fonts.ready);
  // Allow initial client rendering to settle before the still image.
  await page.waitForTimeout(1000);
  await page.screenshot({ path: PATH_VALUE, fullPage: false });
  return {
    url: page.url(),
    title: await page.title(),
    status: response ? response.status() : null,
    excerpt: (await page.locator('body').innerText()).slice(0, 1400)
  };
}
""".replace("URL_VALUE", json.dumps(work["url"]))
     .replace("PATH_VALUE", json.dumps(str(destination))), encoding="utf-8")
  output = cli("run-code", f"--filename={runner}")
  # playwright-cli wraps the function's JSON return in a Result section.
  marker = "### Result\n"
  if marker not in output:
    raise RuntimeError("キャプチャの結果を読み取れません: " + output[-1500:])
  metadata, _ = json.JSONDecoder().raw_decode(output.split(marker, 1)[1].lstrip())
  state = "needs-review"
  if urlsplit(metadata["url"]).hostname == "accounts.google.com":
    state = "needs-login"
  elif metadata["status"] and metadata["status"] >= 400:
    state = "http-error"
  elif not metadata["excerpt"].strip():
    state = "blank-screen"
  return {"id": work["id"], "title": work["title"], "url": work["url"],
          "candidate": str(destination.relative_to(ROOT)), "state": state, "page": metadata}


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--id", action="append", help="対象の作品ID（複数指定可）。未指定で全作品")
  parser.add_argument("--force", action="store_true", help="掲載済み・確認待ちも撮り直す")
  parser.add_argument("--approve", nargs="+", metavar="ID", help="目視確認したキャプチャを掲載する")
  args = parser.parse_args()
  works_path = ROOT / "data/works.json"
  works = json.loads(works_path.read_text(encoding="utf-8"))
  report = json.loads(REPORT.read_text(encoding="utf-8")) if REPORT.exists() else {}
  known_ids = {work["id"] for work in works}
  requested = set(args.approve or args.id or [])
  if requested - known_ids:
    parser.error("不明な作品ID: " + ", ".join(sorted(requested - known_ids)))
  if args.approve:
    # Check all requested candidates before publishing any of them.
    for work in works:
      if work["id"] not in requested:
        continue
      entry = report.get(work["id"], {})
      candidate = ROOT / ".local/captures" / Path(screenshot_path(work)).name
      if entry.get("url") != work["url"] or not candidate.is_file():
        parser.error(f"{work['id']}: 現在のURLのキャプチャがありません。先に撮影してください")
      if entry.get("state") not in ("needs-review", "approved"):
        parser.error(f"{work['id']}: ログイン・表示エラーなどを解消して再撮影してください")
    for work in works:
      if work["id"] in requested:
        destination = ROOT / screenshot_path(work)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / ".local/captures" / destination.name, destination)
        work["screenshot"] = screenshot_path(work)
        report[work["id"]]["state"] = "approved"
        print(f"掲載: {work['id']} {work['title']}")
    write_json(works_path, works)
    write_report(report)
    return 0
  if not shutil.which("playwright-cli"):
    parser.error("playwright-cli が必要です。README のセットアップを参照してください")
  selected = [w for w in works if not args.id or w["id"] in requested]
  cli("open")
  failures = 0
  try:
    for work in selected:
      previous = report.get(work["id"], {})
      if not work["url"]:
        report[work["id"]] = {"id": work["id"], "title": work["title"], "url": "", "state": "missing-url"}
      elif not args.force and (ROOT / screenshot_path(work)).is_file():
        print(f"掲載済み: {work['id']}", flush=True)
        continue
      elif (not args.force and previous.get("url") == work["url"]
            and previous.get("state") in ("needs-review", "needs-login", "http-error", "blank-screen", "needs-attention")
            and (ROOT / previous["candidate"]).is_file()):
        print(f"確認待ち: {work['id']}", flush=True)
        continue
      else:
        try:
          report[work["id"]] = capture(work)
          print(f"{report[work['id']]['state']}: {work['id']} {work['title']}", flush=True)
        except (RuntimeError, subprocess.TimeoutExpired) as error:
          failures += 1
          report[work["id"]] = {"id": work["id"], "title": work["title"], "url": work["url"],
                                "state": "failed", "error": str(error)}
          print(f"取得できません: {work['id']} {error}", file=sys.stderr, flush=True)
      write_report(report)
  finally:
    cli("close")
  print("結果: .local/capture-report.json（画像を確認後 --approve ID で掲載）")
  return 1 if failures else 0


if __name__ == "__main__":
  sys.exit(main())
