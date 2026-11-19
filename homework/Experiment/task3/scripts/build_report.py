#!/usr/bin/env python3
"""从 report.md 生成实验三单篇，并将同一内容另起一页接入已完成的报告。"""
from copy import deepcopy
from pathlib import Path
import re

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
COURSE = ROOT.parent / "task-requirement/计算机操作系统实验要求.docx"
PREFIX = "052403137_王智壹_OSEX"
PREVIOUS = ROOT.parent / "task1&2" / (PREFIX + "12.docx")
TEMPLATE = Document(COURSE)
TEXT = (ROOT / "report.md").read_text().splitlines()
WIDTH = {"process-flow": 10.1, "01-build": 17.8, "02-ring": 15.0,
         "03-waits": 11.45, "04-check": 11.45}
# 第四页的题名、栏目和条目保留原段落属性，显式编号便于与前两份报告合并。
TITLES = {TEMPLATE.paragraphs[i].text: i for i in (65, 66, 70, 89)}


def inline(p, text, size, bold=False):
    for i, part in enumerate(text.split("`")):
        if not part:
            continue
        r = p.add_run(part)
        r.font.name = "Consolas" if i % 2 else "楷体"
        r.font.size = Pt(size - .5 if i % 2 else size)
        r.font.bold = bold
        r.font.color.rgb = RGBColor.from_string("000000")
        fonts = r._element.get_or_add_rPr().rFonts
        fonts.set(qn("w:eastAsia"), "楷体")


def paragraph(doc, text, *, original=None, size=11, bold=False, center=False,
              before=0, after=3, indent=False, heading=False):
    p = doc.add_paragraph()
    if original is not None:
        props = deepcopy(TEMPLATE.paragraphs[original]._p.pPr)
        num = props.find(qn("w:numPr"))
        if num is not None:
            props.remove(num)
        p._p.insert(0, props)
    pf = p.paragraph_format
    pf.space_before, pf.space_after = Pt(before), Pt(after)
    pf.line_spacing = Pt(size * 1.43)
    pf.keep_with_next = heading
    if indent:
        pf.first_line_indent = Pt(22)
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    inline(p, text, size, bold)
    return p


def figure(doc, filename, caption, note=None):
    if note:
        table = doc.add_table(rows=1, cols=2)
        table.autofit = False
        for index, width in enumerate((11.9, 6.2)):
            table.columns[index].width = Cm(width)
            table.cell(0, index).width = Cm(width)
        table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        p = table.cell(0, 0).paragraphs[0]
        cell = table.cell(0, 1)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        body = cell.paragraphs[0]
        body.paragraph_format.line_spacing = Pt(15)
        inline(body, note, 10.5)
    else:
        p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = p.paragraph_format
    pf.space_before, pf.space_after = Pt(2), Pt(0)
    pf.keep_with_next = True
    shape = p.add_run().add_picture(str(ROOT / filename), width=Cm(WIDTH[Path(filename).stem]))
    shape._inline.docPr.set("descr", caption)
    paragraph(doc, caption, size=9.5, center=True, after=4)


def sem_table(doc, lines):
    rows = [[cell.strip() for cell in line.strip("|").split("|")] for line in lines]
    table = doc.add_table(rows=0, cols=2)
    table.autofit = False
    widths = [Cm(5.5), Cm(12.6)]
    for column, width in zip(table.columns, widths):
        column.width = width
    borders = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideV", "insideH"):
        edge = OxmlElement("w:" + side)
        for key, value in (("val", "single"), ("sz", "4"), ("color", "AAAAAA")):
            edge.set(qn("w:" + key), value)
        borders.append(edge)
    table._tbl.tblPr.append(borders)
    for i, values in enumerate([rows[0], *rows[2:]]):
        row = table.add_row()
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        for cell, width, value in zip(row.cells, widths, values):
            cell.width = width
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = Pt(14.5)
            inline(p, value, 10.5, bold=(i == 0))


def append_experiment(doc, *, new_page):
    cover = paragraph(doc, "《计算机操作系统》上机实验报告 EX3", size=12,
                      bold=True, center=True, heading=True)
    cover.paragraph_format.page_break_before = new_page
    i = 0
    page_break = False
    beside = False
    while i < len(TEXT):
        line = TEXT[i]
        i += 1
        if not line:
            continue
        if line == "<!-- 分页 -->":
            page_break = True
        elif line == "<!-- 图文并排 -->":
            beside = True
        elif line.startswith("# "):
            title = line[2:]
            paragraph(doc, title, original=TITLES[title], size=15, bold=True,
                      center=True, heading=True)
        elif line.startswith("学号"):
            paragraph(doc, line, size=10, center=True, after=5)
        elif line.startswith("## "):
            title = line[3:]
            paragraph(doc, title, original=TITLES[title], size=12, bold=True,
                      before=4, heading=True)
        elif line.startswith("### "):
            p = paragraph(doc, line[4:], size=11.5, bold=True, before=4, heading=True)
            p.paragraph_format.page_break_before = page_break
            page_break = False
        elif re.match(r"\d+\. ", line):
            n, content = line.split(". ", 1)
            paragraph(doc, n + "．" + content, original=67, after=1)
        elif line.startswith("|"):
            begin = i - 1
            while i < len(TEXT) and TEXT[i].startswith("|"):
                i += 1
            sem_table(doc, TEXT[begin:i])
        elif line.startswith("!["):
            match = re.fullmatch(r"!\[(.+)\]\((.+)\)", line)
            note = None
            if beside:
                while not TEXT[i]:
                    i += 1
                note = TEXT[i]
                i += 1
                beside = False
            figure(doc, match[2], match[1], note)
        else:
            paragraph(doc, line, indent=True)


if __name__ == "__main__":
    single = Document(COURSE)
    single._element.body.clear_content()  # 保留原页宽、页边距和样式。
    for rel in list(single.part.rels.values()):
        if rel.reltype.endswith(("/image", "/hyperlink")):
            single.part.drop_rel(rel.rId)
    append_experiment(single, new_page=False)
    single.core_properties.title = "计算机操作系统上机实验报告 EX3"
    single.core_properties.author = "王智壹"
    single.save(ROOT / (PREFIX + "3.docx"))

    combined = Document(PREVIOUS)
    append_experiment(combined, new_page=True)
    combined.core_properties.title = "计算机操作系统上机实验报告 EX1、EX2、EX3"
    combined.save(ROOT / (PREFIX + "123.docx"))
