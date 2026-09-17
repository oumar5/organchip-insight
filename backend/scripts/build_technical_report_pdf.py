#!/usr/bin/env python3
"""Render the English technical report to a deterministic, reviewable PDF."""

from __future__ import annotations

import argparse
import re
import tempfile
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    Flowable,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = REPOSITORY_ROOT / "docs/submission/technical-report-en.md"
OUTPUT_PATH = REPOSITORY_ROOT / "output/pdf/organchip-insight-technical-report-candidate.pdf"
PAGE_BREAK_HEADINGS = {
    "1. Problem and target user",
    "2. Data, provenance, and legal basis",
    "3. System architecture",
    "4. Product method",
    "5. Evaluation design",
    "6. Results",
    "6.2 Instance audit on BBBC038",
    "6.3 Quality classification and metadata shortcuts",
    "7. Product verification",
    "8. Credibility and limitations",
    "9. Practical value",
    "10. Reproduction",
    "11. AI tools, libraries, and licences",
}


def register_fonts() -> None:
    font_root = Path("/System/Library/Fonts/Supplemental")
    pdfmetrics.registerFont(TTFont("ReportSans", font_root / "Arial.ttf"))
    pdfmetrics.registerFont(TTFont("ReportSans-Bold", font_root / "Arial Bold.ttf"))
    pdfmetrics.registerFont(TTFont("ReportSans-Italic", font_root / "Arial Italic.ttf"))
    pdfmetrics.registerFont(TTFont("ReportSans-BoldItalic", font_root / "Arial Bold Italic.ttf"))
    pdfmetrics.registerFontFamily(
        "ReportSans",
        normal="ReportSans",
        bold="ReportSans-Bold",
        italic="ReportSans-Italic",
        boldItalic="ReportSans-BoldItalic",
    )


def inline_markup(text: str) -> str:
    text = text.replace("‑", "-").replace("–", "-").replace("—", "-")
    text = escape(text)
    text = re.sub(
        r"\[([^]]+)]\(([^)]+)\)",
        r'<link href="\2" color="#176247"><u>\1</u></link>',
        text,
    )
    text = re.sub(r"`([^`]+)`", r'<font name="ReportSans-Bold">\1</font>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    return text


class ArchitectureDiagram(Flowable):
    def __init__(self) -> None:
        super().__init__()
        self.width = 170 * mm
        self.height = 63 * mm

    def draw(self) -> None:
        canvas = self.canv
        boxes = [
            (5, 124, 160, 42, "React + TypeScript", "experiment workspace"),
            (200, 124, 160, 42, "FastAPI", "API + CLI contract"),
            (395, 124, 80, 42, "SQLite", "state"),
            (395, 58, 80, 42, "Files", "sources + overlays"),
            (
                200,
                0,
                160,
                66,
                "Evidence-gated engine registry",
                "adaptive available | CNN abstains | µSAM benchmark",
            ),
        ]
        for x, y, width, height, title, subtitle in boxes:
            canvas.setFillColor(colors.HexColor("#F3F8F5"))
            canvas.setStrokeColor(colors.HexColor("#7BAE99"))
            canvas.roundRect(x, y, width, height, 8, fill=1, stroke=1)
            canvas.setFillColor(colors.HexColor("#163B31"))
            canvas.setFont("ReportSans-Bold", 9)
            canvas.drawCentredString(x + width / 2, y + height - 16, title)
            canvas.setFillColor(colors.HexColor("#53665E"))
            canvas.setFont("ReportSans", 6.8)
            canvas.drawCentredString(x + width / 2, y + 14, subtitle)
        canvas.setStrokeColor(colors.HexColor("#238365"))
        canvas.setLineWidth(1.5)
        connectors = [
            ((165, 145), (198, 145)),
            ((360, 145), (393, 145)),
            ((360, 132), (393, 80)),
            ((280, 122), (280, 68)),
        ]
        for start, end in connectors:
            canvas.line(*start, *end)


class GroupedBars(Flowable):
    def __init__(self, title: str, categories: list[str], series: dict[str, list[float]]) -> None:
        super().__init__()
        self.title = title
        self.categories = categories
        self.series = series
        self.width = 170 * mm
        self.height = 66 * mm

    def draw(self) -> None:
        canvas = self.canv
        left, bottom, chart_width, chart_height = 48, 38, 420, 132
        palette = [
            colors.HexColor("#238365"),
            colors.HexColor("#F07155"),
            colors.HexColor("#D59A32"),
        ]
        canvas.setFillColor(colors.HexColor("#163B31"))
        canvas.setFont("ReportSans-Bold", 9)
        canvas.drawString(left, self.height - 16, self.title)
        canvas.setStrokeColor(colors.HexColor("#B9C8C1"))
        canvas.line(left, bottom, left, bottom + chart_height)
        canvas.line(left, bottom, left + chart_width, bottom)
        for tick in range(0, 101, 25):
            y = bottom + chart_height * tick / 100
            canvas.setStrokeColor(colors.HexColor("#E4EBE7"))
            canvas.line(left, y, left + chart_width, y)
            canvas.setFillColor(colors.HexColor("#607069"))
            canvas.setFont("ReportSans", 6.5)
            canvas.drawRightString(left - 5, y - 2, f"{tick / 100:.2f}")
        group_width = chart_width / len(self.categories)
        bar_width = min(18, (group_width - 18) / max(len(self.series), 1))
        for category_index, category in enumerate(self.categories):
            group_start = left + category_index * group_width + 9
            for series_index, (_label, values) in enumerate(self.series.items()):
                value = values[category_index]
                x = group_start + series_index * bar_width
                height = chart_height * value
                canvas.setFillColor(palette[series_index % len(palette)])
                canvas.rect(x, bottom, bar_width - 2, height, fill=1, stroke=0)
            canvas.setFillColor(colors.HexColor("#33433D"))
            canvas.setFont("ReportSans", 6.5)
            canvas.drawCentredString(
                left + category_index * group_width + group_width / 2,
                bottom - 13,
                category,
            )
        legend_x = left
        for index, label in enumerate(self.series):
            canvas.setFillColor(palette[index % len(palette)])
            canvas.rect(legend_x, 9, 8, 8, fill=1, stroke=0)
            canvas.setFillColor(colors.HexColor("#33433D"))
            canvas.setFont("ReportSans", 6.8)
            canvas.drawString(legend_x + 12, 10, label)
            legend_x += 105


def styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "body": ParagraphStyle(
            "Body",
            parent=sample["BodyText"],
            fontName="ReportSans",
            fontSize=9.2,
            leading=13.1,
            textColor=colors.HexColor("#24352F"),
            spaceAfter=6,
            alignment=TA_LEFT,
        ),
        "h2": ParagraphStyle(
            "Heading2",
            parent=sample["Heading2"],
            fontName="ReportSans-Bold",
            fontSize=18,
            leading=21,
            textColor=colors.HexColor("#123D31"),
            spaceAfter=10,
        ),
        "h3": ParagraphStyle(
            "Heading3",
            parent=sample["Heading3"],
            fontName="ReportSans-Bold",
            fontSize=12.5,
            leading=15,
            textColor=colors.HexColor("#176247"),
            spaceBefore=6,
            spaceAfter=7,
        ),
        "quote": ParagraphStyle(
            "Quote",
            parent=sample["BodyText"],
            fontName="ReportSans-Italic",
            fontSize=8.8,
            leading=12.5,
            textColor=colors.HexColor("#4C5D56"),
            borderColor=colors.HexColor("#8CC8AE"),
            borderWidth=0,
            borderPadding=(8, 10, 8, 12),
            backColor=colors.HexColor("#EDF7F2"),
            leftIndent=8,
            rightIndent=8,
            spaceAfter=8,
        ),
        "code": ParagraphStyle(
            "Code",
            fontName="Courier",
            fontSize=7.4,
            leading=10,
            textColor=colors.HexColor("#183C32"),
            backColor=colors.HexColor("#F1F5F3"),
            borderPadding=8,
            spaceAfter=8,
        ),
        "caption": ParagraphStyle(
            "Caption",
            fontName="ReportSans-Italic",
            fontSize=7.2,
            leading=9.5,
            textColor=colors.HexColor("#607069"),
            spaceAfter=8,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            fontName="ReportSans-Bold",
            fontSize=7.1,
            leading=9.2,
            textColor=colors.white,
        ),
    }


def markdown_blocks(markdown: str, report_styles: dict[str, ParagraphStyle]) -> list[Flowable]:
    lines = markdown.splitlines()
    start = next(index for index, line in enumerate(lines) if line == "## Abstract")
    lines = lines[start:]
    blocks: list[Flowable] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue
        if stripped.startswith("## ") or stripped.startswith("### "):
            level = 3 if stripped.startswith("### ") else 2
            title = stripped[level + 1 :]
            if title in PAGE_BREAK_HEADINGS:
                blocks.append(PageBreak())
            blocks.append(Paragraph(inline_markup(title), report_styles[f"h{level}"]))
            if title == "3. System architecture":
                blocks.extend(
                    [
                        ArchitectureDiagram(),
                        Paragraph(
                            "Figure 1. Local architecture and evidence-gated engine roles.",
                            report_styles["caption"],
                        ),
                    ]
                )
            if title == "6.1 Foreground segmentation on BBBC019":
                blocks.extend(
                    [
                        GroupedBars(
                            "External foreground benchmark",
                            ["Adaptive", "µSAM"],
                            {"Macro-F1": [0.424892, 0.815542], "Macro-IoU": [0.273632, 0.698535]},
                        ),
                        Paragraph(
                            "Figure 2. BBBC019 macro scores; the stronger µSAM "
                            "result carries much higher measured cost.",
                            report_styles["caption"],
                        ),
                    ]
                )
            if title == "6.3 Quality classification and metadata shortcuts":
                blocks.extend(
                    [
                        GroupedBars(
                            "Balanced accuracy by acquisition mode",
                            ["Reference", "Gray 224", "Gray 448", "Metadata"],
                            {
                                "L": [0.7729, 0.7389, 0.8338, 0.8171],
                                "RGB": [0.6315, 0.5948, 0.6079, 0.6533],
                            },
                        ),
                        Paragraph(
                            "Figure 3. Mode-specific validation exposes the weak "
                            "and unstable RGB signal hidden by global scores.",
                            report_styles["caption"],
                        ),
                    ]
                )
            index += 1
            continue
        if stripped.startswith("```"):
            language = stripped[3:]
            code_lines: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index].replace("→", "->"))
                index += 1
            index += 1
            label = f"{language}\n" if language else ""
            blocks.append(Preformatted(label + "\n".join(code_lines), report_styles["code"]))
            continue
        if stripped.startswith("> "):
            quote_lines = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                quote_lines.append(lines[index].strip().lstrip(">").strip())
                index += 1
            blocks.append(Paragraph(inline_markup(" ".join(quote_lines)), report_styles["quote"]))
            continue
        if (
            "|" in stripped
            and index + 1 < len(lines)
            and re.match(r"^\|?\s*:?-+", lines[index + 1].strip())
        ):
            table_lines = [stripped]
            index += 2
            while index < len(lines) and "|" in lines[index] and lines[index].strip():
                table_lines.append(lines[index].strip())
                index += 1
            rows = [[cell.strip() for cell in row.strip("|").split("|")] for row in table_lines]
            column_count = len(rows[0])
            if column_count >= 7:
                widths = [31 * mm] + [20 * mm] * (column_count - 1)
            elif column_count == 4:
                widths = [36 * mm, 35 * mm, 44 * mm, 55 * mm]
            elif column_count == 2:
                widths = [96 * mm, 74 * mm]
            else:
                widths = [170 * mm / column_count] * column_count
            data = []
            for row_index, row in enumerate(rows):
                cell_style = (
                    report_styles["table_header"] if row_index == 0 else report_styles["body"]
                )
                data.append([Paragraph(inline_markup(cell), cell_style) for cell in row])
            table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#164B3C")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "ReportSans-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 7.1 if column_count >= 4 else 8),
                        ("LEADING", (0, 0), (-1, -1), 9.2),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C9D8D1")),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor("#F4F8F6")],
                        ),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            blocks.extend([table, Spacer(1, 8)])
            continue
        if re.match(r"^(?:- |\d+\. )", stripped):
            ordered_match = re.match(r"^(\d+)\. ", stripped)
            ordered = ordered_match is not None
            items: list[ListItem] = []
            while index < len(lines) and re.match(r"^(?:- |\d+\. )", lines[index].strip()):
                item_text = re.sub(r"^(?:- |\d+\. )", "", lines[index].strip())
                items.append(ListItem(Paragraph(inline_markup(item_text), report_styles["body"])))
                index += 1
            blocks.append(
                ListFlowable(
                    items,
                    bulletType="1" if ordered else "bullet",
                    start=ordered_match.group(1) if ordered_match else "1",
                    leftIndent=16,
                    bulletFontName="ReportSans",
                    bulletFontSize=8,
                    spaceAfter=6,
                )
            )
            continue
        paragraph_lines = [stripped]
        index += 1
        while index < len(lines):
            candidate = lines[index].strip()
            if not candidate:
                break
            if candidate.startswith(("## ", "### ", "```", "> ")):
                break
            if re.match(r"^(?:- |\d+\. )", candidate):
                break
            if (
                "|" in candidate
                and index + 1 < len(lines)
                and re.match(r"^\|?\s*:?-+", lines[index + 1].strip())
            ):
                break
            paragraph_lines.append(candidate)
            index += 1
        blocks.append(Paragraph(inline_markup(" ".join(paragraph_lines)), report_styles["body"]))
    return blocks


class ReportCanvas(Canvas):
    def __init__(self, *args, **kwargs) -> None:
        kwargs["invariant"] = 1
        super().__init__(*args, **kwargs)
        self.setTitle("OrganChip Insight - Technical Report Candidate")
        self.setAuthor("OrganChip Insight team - owner declaration pending")


def draw_page_frame(canvas: Canvas, document: SimpleDocTemplate) -> None:
    width, height = A4
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D9E4DF"))
    canvas.line(20 * mm, height - 14 * mm, width - 20 * mm, height - 14 * mm)
    canvas.setFillColor(colors.HexColor("#52645C"))
    canvas.setFont("ReportSans", 7)
    canvas.drawString(20 * mm, height - 11 * mm, "OrganChip Insight | Technical report candidate")
    canvas.drawRightString(width - 20 * mm, 10 * mm, f"{document.page}")
    canvas.restoreState()


def cover(report_styles: dict[str, ParagraphStyle]) -> list[Flowable]:
    title = ParagraphStyle(
        "CoverTitle",
        fontName="ReportSans-Bold",
        fontSize=28,
        leading=32,
        textColor=colors.HexColor("#123D31"),
        alignment=TA_LEFT,
        spaceAfter=16,
    )
    subtitle = ParagraphStyle(
        "CoverSubtitle",
        fontName="ReportSans",
        fontSize=15,
        leading=21,
        textColor=colors.HexColor("#436057"),
        spaceAfter=24,
    )
    badge = ParagraphStyle(
        "CoverBadge",
        fontName="ReportSans-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#176247"),
        backColor=colors.HexColor("#E7F5EF"),
        borderPadding=8,
        spaceAfter=22,
    )
    return [
        Spacer(1, 28 * mm),
        Paragraph("OrganChip Insight", title),
        Paragraph(
            "A traceable microscopy workspace for organ-on-chip experiments",
            subtitle,
        ),
        Paragraph("TOOL &amp; PLATFORM | AI4S OPEN INNOVATION 2026", badge),
        Paragraph(
            "Evidence-gated image analysis that keeps sources, overlays, "
            "measurements, provenance, uncertainty, and negative findings "
            "in one reproducible local experiment.",
            ParagraphStyle(
                "CoverStatement",
                parent=report_styles["body"],
                fontSize=13,
                leading=19,
                textColor=colors.HexColor("#24352F"),
                spaceAfter=30,
            ),
        ),
        Table(
            [
                ["Candidate date", "17 September 2026"],
                ["Team", "Owner declaration pending"],
                ["Release", "Validated on dev; public tag pending authorization"],
                ["Scientific scope", "Non-clinical, exploratory microscopy workflow"],
            ],
            colWidths=[40 * mm, 120 * mm],
            style=TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "ReportSans-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "ReportSans"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#176247")),
                    ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#33433D")),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#D7E4DE")),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            ),
        ),
        Spacer(1, 23 * mm),
        Paragraph(
            "Candidate PDF. Team identity, code licence, public release tag, "
            "and public URLs remain owner-controlled publication fields.",
            report_styles["quote"],
        ),
        PageBreak(),
    ]


def build(output_path: Path) -> None:
    register_fonts()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_styles = styles()
    document = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        title="OrganChip Insight - Technical Report Candidate",
        author="OrganChip Insight team - owner declaration pending",
    )
    story = cover(report_styles)
    story.extend(markdown_blocks(SOURCE_PATH.read_text(), report_styles))
    document.build(story, onLaterPages=draw_page_frame, canvasmaker=ReportCanvas)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    if arguments.check:
        if not OUTPUT_PATH.is_file():
            raise SystemExit("Technical report PDF is missing; run `make report-pdf`.")
        with tempfile.TemporaryDirectory() as temporary_directory:
            candidate = Path(temporary_directory) / OUTPUT_PATH.name
            build(candidate)
            if candidate.read_bytes() != OUTPUT_PATH.read_bytes():
                raise SystemExit("Technical report PDF is stale; run `make report-pdf`.")
        print(f"OK: {OUTPUT_PATH.relative_to(REPOSITORY_ROOT)}")
        return
    build(OUTPUT_PATH)
    print(f"Wrote {OUTPUT_PATH.relative_to(REPOSITORY_ROOT)}")


if __name__ == "__main__":
    main()
