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
SOURCE_PATHS = {
    "en": REPOSITORY_ROOT / "docs/submission/technical-report-en.md",
    "fr": REPOSITORY_ROOT / "docs/submission/technical-report-fr.md",
}
OUTPUT_PATHS = {
    "en": REPOSITORY_ROOT / "output/pdf/organchip-insight-technical-report-candidate-en.pdf",
    "fr": REPOSITORY_ROOT / "output/pdf/organchip-insight-technical-report-candidate-fr.pdf",
}
PAGE_BREAK_PREFIXES = (
    "1. ",
    "2. ",
    "3. ",
    "4. ",
    "5. ",
    "6. ",
    "6.2 ",
    "6.3 ",
    "7. ",
    "8. ",
    "9. ",
    "10. ",
    "11. ",
)
TEXT = {
    "en": {
        "header": "OrganChip Insight | Technical report candidate",
        "pdf_title": "OrganChip Insight - Technical Report Candidate",
        "pdf_author": "OrganChip Insight - solo team",
        "cover_title": "OrganChip Insight",
        "cover_subtitle": "A traceable microscopy workspace for organ-on-chip experiments",
        "cover_badge": "TOOL &amp; PLATFORM | AI4S OPEN INNOVATION 2026",
        "cover_statement": (
            "Evidence-gated image analysis that keeps sources, overlays, "
            "measurements, provenance, uncertainty, and negative findings "
            "in one reproducible local experiment."
        ),
        "cover_rows": [
            ["Candidate date", "17 September 2026"],
            ["Team", "Solo team; public author name pending"],
            ["Release", "Validated on dev; public tag pending authorization"],
            ["Scientific scope", "Non-clinical, exploratory microscopy workflow"],
        ],
        "cover_note": (
            "Candidate PDF. Apache-2.0 is fixed for the code; the public author "
            "name, release tag, and public URLs remain owner-controlled fields."
        ),
        "architecture_boxes": [
            ("React + TypeScript", "experiment workspace"),
            ("FastAPI", "API + CLI contract"),
            ("SQLite", "state"),
            ("Files", "sources + overlays"),
            (
                "Evidence-gated engine registry",
                "adaptive available | CNN abstains | µSAM benchmark",
            ),
        ],
        "figure_1": "Figure 1. Local architecture and evidence-gated engine roles.",
        "foreground_title": "External foreground benchmark",
        "adaptive": "Adaptive",
        "figure_2": (
            "Figure 2. BBBC019 macro scores; the stronger µSAM result carries "
            "much higher measured cost."
        ),
        "classification_title": "Balanced accuracy by acquisition mode",
        "classification_categories": ["Reference", "Gray 224", "Gray 448", "Metadata"],
        "figure_3": (
            "Figure 3. Mode-specific validation exposes the weak and unstable "
            "RGB signal hidden by global scores."
        ),
    },
    "fr": {
        "header": "OrganChip Insight | Rapport technique candidat",
        "pdf_title": "OrganChip Insight - Rapport technique candidat",
        "pdf_author": "OrganChip Insight - équipe solo",
        "cover_title": "OrganChip Insight",
        "cover_subtitle": "Un espace de microscopie traçable pour les expériences sur puce",
        "cover_badge": "OUTIL &amp; PLATEFORME | AI4S OPEN INNOVATION 2026",
        "cover_statement": (
            "Une analyse d'images gouvernée par les preuves, qui conserve les "
            "sources, overlays, mesures, provenance, incertitudes et résultats "
            "négatifs dans une expérience locale reproductible."
        ),
        "cover_rows": [
            ["Date du candidat", "17 septembre 2026"],
            ["Équipe", "Équipe solo ; nom public de l'auteur à confirmer"],
            ["Release", "Validée sur dev ; tag public en attente d'autorisation"],
            ["Périmètre scientifique", "Exploration microscopique non clinique"],
        ],
        "cover_note": (
            "PDF candidat. Apache-2.0 est fixée pour le code ; le nom public de "
            "l'auteur, le tag de release et les URL publiques restent à confirmer."
        ),
        "architecture_boxes": [
            ("React + TypeScript", "espace expérimental"),
            ("FastAPI", "contrat API + CLI"),
            ("SQLite", "état"),
            ("Fichiers", "sources + overlays"),
            (
                "Registre de moteurs gouverné par les preuves",
                "adaptatif disponible | CNN s'abstient | benchmark µSAM",
            ),
        ],
        "figure_1": "Figure 1. Architecture locale et rôles des moteurs selon les preuves.",
        "foreground_title": "Benchmark externe du premier plan",
        "adaptive": "Adaptatif",
        "figure_2": (
            "Figure 2. Macro-scores BBBC019 ; le meilleur résultat µSAM a un "
            "coût mesuré nettement supérieur."
        ),
        "classification_title": "Balanced accuracy par mode d'acquisition",
        "classification_categories": ["Référence", "Gris 224", "Gris 448", "Métadonnées"],
        "figure_3": (
            "Figure 3. La validation par mode révèle le signal RGB faible et "
            "instable masqué par les scores globaux."
        ),
    },
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
    def __init__(self, language: str) -> None:
        super().__init__()
        self.language = language
        self.width = 170 * mm
        self.height = 63 * mm

    def draw(self) -> None:
        canvas = self.canv
        labels = TEXT[self.language]["architecture_boxes"]
        boxes = [
            (5, 124, 160, 42, *labels[0]),
            (200, 124, 160, 42, *labels[1]),
            (395, 124, 80, 42, *labels[2]),
            (395, 58, 80, 42, *labels[3]),
            (200, 0, 160, 66, *labels[4]),
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


def markdown_blocks(
    markdown: str,
    report_styles: dict[str, ParagraphStyle],
    language: str,
) -> list[Flowable]:
    lines = markdown.splitlines()
    start = next(index for index, line in enumerate(lines) if line.startswith("## "))
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
            if title.startswith(PAGE_BREAK_PREFIXES):
                blocks.append(PageBreak())
            blocks.append(Paragraph(inline_markup(title), report_styles[f"h{level}"]))
            if title.startswith("3. "):
                blocks.extend(
                    [
                        ArchitectureDiagram(language),
                        Paragraph(
                            TEXT[language]["figure_1"],
                            report_styles["caption"],
                        ),
                    ]
                )
            if title.startswith("6.1 "):
                blocks.extend(
                    [
                        GroupedBars(
                            TEXT[language]["foreground_title"],
                            [TEXT[language]["adaptive"], "µSAM"],
                            {"Macro-F1": [0.424892, 0.815542], "Macro-IoU": [0.273632, 0.698535]},
                        ),
                        Paragraph(
                            TEXT[language]["figure_2"],
                            report_styles["caption"],
                        ),
                    ]
                )
            if title.startswith("6.3 "):
                blocks.extend(
                    [
                        GroupedBars(
                            TEXT[language]["classification_title"],
                            TEXT[language]["classification_categories"],
                            {
                                "L": [0.7729, 0.7389, 0.8338, 0.8171],
                                "RGB": [0.6315, 0.5948, 0.6079, 0.6533],
                            },
                        ),
                        Paragraph(
                            TEXT[language]["figure_3"],
                            report_styles["caption"],
                        ),
                    ]
                )
            index += 1
            continue
        if stripped.startswith("```"):
            code_language = stripped[3:]
            code_lines: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index].replace("→", "->"))
                index += 1
            index += 1
            label = f"{code_language}\n" if code_language else ""
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
    def __init__(self, *args, language: str, **kwargs) -> None:
        kwargs["invariant"] = 1
        super().__init__(*args, **kwargs)
        self.setTitle(TEXT[language]["pdf_title"])
        self.setAuthor(TEXT[language]["pdf_author"])


def draw_page_frame(
    canvas: Canvas,
    document: SimpleDocTemplate,
    language: str,
) -> None:
    width, height = A4
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D9E4DF"))
    canvas.line(20 * mm, height - 14 * mm, width - 20 * mm, height - 14 * mm)
    canvas.setFillColor(colors.HexColor("#52645C"))
    canvas.setFont("ReportSans", 7)
    canvas.drawString(20 * mm, height - 11 * mm, TEXT[language]["header"])
    canvas.drawRightString(width - 20 * mm, 10 * mm, f"{document.page}")
    canvas.restoreState()


def cover(
    report_styles: dict[str, ParagraphStyle],
    language: str,
) -> list[Flowable]:
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
        Paragraph(TEXT[language]["cover_title"], title),
        Paragraph(TEXT[language]["cover_subtitle"], subtitle),
        Paragraph(TEXT[language]["cover_badge"], badge),
        Paragraph(
            TEXT[language]["cover_statement"],
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
            TEXT[language]["cover_rows"],
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
            TEXT[language]["cover_note"],
            report_styles["quote"],
        ),
        PageBreak(),
    ]


def build(language: str, output_path: Path) -> None:
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
        title=TEXT[language]["pdf_title"],
        author=TEXT[language]["pdf_author"],
    )
    story = cover(report_styles, language)
    story.extend(markdown_blocks(SOURCE_PATHS[language].read_text(), report_styles, language))

    def frame(canvas: Canvas, current_document: SimpleDocTemplate) -> None:
        draw_page_frame(canvas, current_document, language)

    def canvas_factory(*args, **kwargs) -> ReportCanvas:
        return ReportCanvas(*args, language=language, **kwargs)

    document.build(story, onLaterPages=frame, canvasmaker=canvas_factory)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--language", choices=("en", "fr", "all"), default="all")
    arguments = parser.parse_args()
    languages = ("en", "fr") if arguments.language == "all" else (arguments.language,)
    if arguments.check:
        for language in languages:
            output_path = OUTPUT_PATHS[language]
            if not output_path.is_file():
                raise SystemExit(
                    f"Technical report PDF ({language}) is missing; run `make report-pdf`."
                )
            with tempfile.TemporaryDirectory() as temporary_directory:
                candidate = Path(temporary_directory) / output_path.name
                build(language, candidate)
                if candidate.read_bytes() != output_path.read_bytes():
                    raise SystemExit(
                        f"Technical report PDF ({language}) is stale; run `make report-pdf`."
                    )
            print(f"OK: {output_path.relative_to(REPOSITORY_ROOT)}")
        return
    for language in languages:
        output_path = OUTPUT_PATHS[language]
        build(language, output_path)
        print(f"Wrote {output_path.relative_to(REPOSITORY_ROOT)}")


if __name__ == "__main__":
    main()
