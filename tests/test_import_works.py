import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
from zipfile import ZipFile

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/import_works.py"
SPEC = importlib.util.spec_from_file_location("import_works", SCRIPT)
importer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(importer)


class ImportTests(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.root = Path(self.temp.name)
    self.columns = ["作品のURL", "氏名：漢字", "作品名：40文字以内", "タイムスタンプ",
                    "氏名：ローマ字（例えば）", "作品の説明文：180文字以内", "学年"]

  def row(self, name="Example Person", time="46000", title="作品", url="https://example.com/app"):
    return [url, "非公開の氏名", title, time, name, "説明です。\n次の段落。", "2年"]

  def workbook(self, rows, shared=False):
    path = self.root / "answers.xlsx"
    ns = importer.NS["s"]
    worksheet = ET.Element(f"{{{ns}}}worksheet")
    data = ET.SubElement(worksheet, f"{{{ns}}}sheetData")
    strings = []
    for i, values in enumerate([self.columns, *rows], 1):
      row = ET.SubElement(data, f"{{{ns}}}row", r=str(i))
      for column, value in zip("ABCDEFG", values):
        cell = ET.SubElement(row, f"{{{ns}}}c", r=f"{column}{i}", t="s" if shared else "inlineStr")
        if shared:
          ET.SubElement(cell, f"{{{ns}}}v").text = str(len(strings))
          strings.append(value)
        else:
          inline = ET.SubElement(cell, f"{{{ns}}}is")
          ET.SubElement(inline, f"{{{ns}}}t").text = value
    with ZipFile(path, "w") as archive:
      archive.writestr("xl/workbook.xml", f'<workbook xmlns="{ns}" xmlns:r="{importer.REL}"><sheets><sheet name="回答" r:id="rId1"/></sheets></workbook>')
      archive.writestr("xl/_rels/workbook.xml.rels", '<Relationships><Relationship Id="rId1" Target="worksheets/sheet7.xml"/></Relationships>')
      archive.writestr("xl/worksheets/sheet7.xml", ET.tostring(worksheet))
      if shared:
        root = ET.Element(f"{{{ns}}}sst")
        for value in strings:
          item = ET.SubElement(root, f"{{{ns}}}si")
          ET.SubElement(item, f"{{{ns}}}t").text = value
        archive.writestr("xl/sharedStrings.xml", ET.tostring(root))
    return path

  def test_initials_follow_entered_order(self):
    self.assertEqual(importer.initials("  Example   Person "), "E.P.")
    self.assertEqual(importer.initials("Ｐｅｒｓｏｎ Example"), "P.E.")

  def test_extract_inline_and_shared_strings_without_private_columns(self):
    for shared in (False, True):
      works, _ = importer.extract(self.workbook([self.row()], shared=shared))
      serialized = json.dumps(works, ensure_ascii=False)
      for private in ("Example", "Person", "非公開の氏名", "2年"):
        self.assertNotIn(private, serialized)
      self.assertEqual(works[0]["initials"], "E.P.")
      self.assertEqual(works[0]["description"], "説明です。\n次の段落。")

  def test_latest_timestamp_wins_even_if_rows_reordered_and_title_changes(self):
    works, report = importer.extract(self.workbook([
      self.row(name="ＥＸＡＭＰＬＥ  Person", time="46001", title="修正版"),
      self.row(time="46000", title="元の作品", url="https://example.com/old"),
    ]))
    self.assertEqual(len(works), 1)
    self.assertEqual(works[0]["title"], "修正版")
    self.assertEqual(report["duplicates"][0]["selected"]["row"], 2)
    self.assertEqual(set(report["duplicates"][0]["changedFields"]), {"title", "url"})
    original, _ = importer.extract(self.workbook([self.row()]))
    self.assertEqual(works[0]["id"], original[0]["id"])

  def test_same_initials_are_separate_people(self):
    works, _ = importer.extract(self.workbook([self.row(), self.row(name="Else Place")]))
    self.assertEqual([w["initials"] for w in works], ["E.P.", "E.P."])
    self.assertNotEqual(works[0]["id"], works[1]["id"])

  def test_latest_blank_url_is_not_filled_from_previous(self):
    works, report = importer.extract(self.workbook([self.row(), self.row(time="46001", url="")]))
    self.assertEqual(works[0]["url"], "")
    self.assertTrue(report["warnings"])

  def test_invalid_required_fields_urls_and_timestamps_fail(self):
    for row in (self.row(url="javascript:alert(1)"), self.row(url="http://example.com"),
                self.row(url="https://user:pass@example.com"), self.row(title=""),
                self.row(time="yesterday"), self.row(name="氏名")):
      with self.assertRaises(ValueError):
        importer.extract(self.workbook([row]))

  def test_url_change_does_not_reuse_old_screenshot(self):
    works, _ = importer.extract(self.workbook([self.row(url="https://example.com/old")]))
    work = works[0]
    old_path = importer.screenshot_path(work)
    with patch.object(importer, "ROOT", self.root):
      image = self.root / old_path
      image.parent.mkdir(parents=True)
      image.write_bytes(b"old image")
      old_works, _ = importer.extract(self.workbook([self.row(url=work["url"])]))
      self.assertEqual(old_works[0]["screenshot"], old_path)
      work["url"] = "https://example.com/new"
      self.assertNotEqual(old_path, importer.screenshot_path(work))
      works, _ = importer.extract(self.workbook([self.row(url=work["url"])]))
      self.assertNotIn("screenshot", works[0])

  def test_equal_timestamp_prefers_later_row(self):
    works, _ = importer.extract(self.workbook([self.row(), self.row(title="後の回答")]))
    self.assertEqual(works[0]["title"], "後の回答")

  def test_ai_studio_links_open_fullscreen_and_preserve_other_options(self):
    expected = "https://aistudio.google.com/apps/example?lang=ja&showAssistant=true&showPreview=true&fullscreenApplet=true#preview"
    for host in ("ai.studio", "aistudio.google.com"):
      url = f"https://{host}/apps/example?fullscreenApplet=false&lang=ja&fullscreenApplet=false#preview"
      works, _ = importer.extract(self.workbook([self.row(url=url)]))
      self.assertEqual(works[0]["url"], expected)
      self.assertEqual(importer.public_url(works[0]["url"]), expected)

  def test_deployed_apps_and_unrelated_hosts_keep_original_url(self):
    for url in ("https://example.ai.studio/?lang=ja", "https://example.com/apps/example",
                "https://aistudio.google.com.example.com/apps/example"):
      self.assertEqual(importer.public_url(url), url)


if __name__ == "__main__":
  unittest.main()
