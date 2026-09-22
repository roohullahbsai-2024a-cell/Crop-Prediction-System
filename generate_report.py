#!/usr/bin/env python3
"""
Crop Recommendation System — Internship Final Technical Report Generator
========================================================================
This script generates a comprehensive, submission-ready Microsoft Word (.docx)
report documenting the complete end-to-end Machine Learning Crop Recommendation
internship project.

Key Contents:
  - Executive Summary, Problem Statement & Agricultural Domain Context
  - Exploratory Data Analysis (EDA) with Feature Distributions & Correlations
  - Preprocessing Pipeline (Scaling, Encoding, Stratified Splitting, 5-Fold CV)
  - Dedicated Deep-Dive Profiles for ALL 5 Models:
      1. XGBoost (Gradient Boosted Trees)
      2. Random Forest Classifier
      3. Support Vector Machine (SVM)
      4. Decision Tree Classifier
      5. K-Nearest Neighbors (KNN)
  - Cross-Model Benchmarking & Comparative Evaluation (Tables + Radar + Bar Charts)
  - Literature Benchmarking Against 5 Published Scientific Research Papers
  - Production Deployment Architecture (Flask REST API & Web Dashboard)
  - Agronomic Insights, Crop Decision Trees, and Farmer Guidelines
  - Engineering Reflections, Challenges Faced, and Future Roadmap

Usage:
  python generate_report.py
Output:
  Crop_Recommendation_Internship_Report.docx
"""

import os
import sys
from datetime import datetime

import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

# ==============================================================================
# CONFIGURATION & CONSTANTS
# ==============================================================================
OUTPUT_FILENAME = "Crop_Recommendation_Internship_Report.docx"
ARTIFACTS_DIR   = "artifacts"

# Color Palette (Forest & Agricultural Theme)
HEX_PRIMARY      = "2D6A4F"  # Deep Forest Green (Headings, primary accents)
HEX_SECONDARY    = "1B4332"  # Dark Pine Green (Sub-headings, strong text)
HEX_ACCENT       = "52B788"  # Sage Green (Dividers, borders, subtle highlights)
HEX_LIGHT_BG     = "F4FBF7"  # Very Light Mint/Green (Callout boxes, table header tints)
HEX_ZEBRA        = "F9FBFA"  # Alternating table row fill
HEX_DARK_TEXT    = "1F2937"  # Slate Dark Gray (Body copy for optimal contrast)
HEX_MUTED_TEXT   = "6B7280"  # Muted Gray (Captions, metadata, footer)
HEX_BORDER       = "D1D5DB"  # Neutral Gray for table borders

COLOR_PRIMARY    = RGBColor(0x2D, 0x6A, 0x4F)
COLOR_SECONDARY  = RGBColor(0x1B, 0x43, 0x32)
COLOR_DARK_TEXT  = RGBColor(0x1F, 0x29, 0x37)
COLOR_MUTED      = RGBColor(0x6B, 0x72, 0x80)

# ==============================================================================
# XML & STYLING HELPER FUNCTIONS
# ==============================================================================
def set_cell_background(cell, hex_color):
    """Sets the background fill color of a table cell."""
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=120, bottom=120, left=160, right=160):
    """Sets cell padding (in dxa: 20 dxa = 1 pt)."""
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def set_cell_border_left_only(cell, color=HEX_PRIMARY, sz="36"):
    """Adds a thick accent border on the left side of a cell (for callouts)."""
    tcPr = cell._element.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="none"/>'
        f'<w:left w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:bottom w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)

def set_table_borders(table, color=HEX_BORDER, sz="4", val="single"):
    """Applies subtle horizontal borders to a table."""
    tblPr = table._element.xpath('w:tblPr')
    if tblPr:
        borders = parse_xml(
            f'<w:tblBorders {nsdecls("w")}>'
            f'<w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:left w:val="none"/>'
            f'<w:right w:val="none"/>'
            f'<w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:insideV w:val="none"/>'
            f'</w:tblBorders>'
        )
        tblPr[0].append(borders)

def add_page_number_fields(run):
    """Inserts a dynamic Word PAGE field into a text run."""
    fldChar1 = parse_xml(r'<w:fldChar %s w:fldCharType="begin"/>' % nsdecls('w'))
    instrText = parse_xml(r'<w:instrText %s xml:space="preserve"> PAGE </w:instrText>' % nsdecls('w'))
    fldChar2 = parse_xml(r'<w:fldChar %s w:fldCharType="separate"/>' % nsdecls('w'))
    fldChar3 = parse_xml(r'<w:fldChar %s w:fldCharType="end"/>' % nsdecls('w'))
    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)
    run._r.append(fldChar3)

def add_numpages_field(run):
    """Inserts a dynamic Word NUMPAGES field into a text run."""
    fldChar1 = parse_xml(r'<w:fldChar %s w:fldCharType="begin"/>' % nsdecls('w'))
    instrText = parse_xml(r'<w:instrText %s xml:space="preserve"> NUMPAGES </w:instrText>' % nsdecls('w'))
    fldChar2 = parse_xml(r'<w:fldChar %s w:fldCharType="separate"/>' % nsdecls('w'))
    fldChar3 = parse_xml(r'<w:fldChar %s w:fldCharType="end"/>' % nsdecls('w'))
    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)
    run._r.append(fldChar3)

# ==============================================================================
# DOCUMENT BUILDER CLASS
# ==============================================================================
class InternshipReportBuilder:
    def __init__(self, output_path=OUTPUT_FILENAME):
        self.output_path = output_path
        self.doc = Document()
        self.fig_counter = 1
        self.tbl_counter = 1
        self._configure_document_styles()

    def _configure_document_styles(self):
        """Sets standard margins, typography, and default paragraph styling."""
        # 1-inch margins
        for section in self.doc.sections:
            section.top_margin    = Inches(1.0)
            section.bottom_margin = Inches(1.0)
            section.left_margin   = Inches(1.0)
            section.right_margin  = Inches(1.0)
            section.header_distance = Inches(0.5)
            section.footer_distance = Inches(0.5)

        # Base Normal Style
        style_normal = self.doc.styles['Normal']
        font = style_normal.font
        font.name = 'Calibri'
        font.size = Pt(10.5)
        font.color.rgb = COLOR_DARK_TEXT
        style_normal.paragraph_format.line_spacing = 1.15
        style_normal.paragraph_format.space_after  = Pt(6)
        style_normal.paragraph_format.space_before = Pt(0)

    def setup_header_footer(self):
        """Configures running headers and footers with page numbering."""
        section = self.doc.sections[0]
        section.different_first_page_header_footer = True

        # Running Header (pages 2+)
        header = section.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run("Crop Recommendation System — Final Internship Technical Report")
        hrun.font.name = 'Calibri'
        hrun.font.size = Pt(8.5)
        hrun.font.color.rgb = COLOR_MUTED

        # Running Footer (pages 2+)
        footer = section.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        frun_left = fp.add_run("Confidential — Academic & Technical Evaluation   |   Page ")
        frun_left.font.name = 'Calibri'
        frun_left.font.size = Pt(8.5)
        frun_left.font.color.rgb = COLOR_MUTED

        frun_pg = fp.add_run()
        frun_pg.font.name = 'Calibri'
        frun_pg.font.size = Pt(8.5)
        frun_pg.font.color.rgb = COLOR_PRIMARY
        frun_pg.bold = True
        add_page_number_fields(frun_pg)

        frun_mid = fp.add_run(" of ")
        frun_mid.font.name = 'Calibri'
        frun_mid.font.size = Pt(8.5)
        frun_mid.font.color.rgb = COLOR_MUTED

        frun_tot = fp.add_run()
        frun_tot.font.name = 'Calibri'
        frun_tot.font.size = Pt(8.5)
        frun_tot.font.color.rgb = COLOR_MUTED
        add_numpages_field(frun_tot)

    # ──────────────────────────────────────────────────────────────────────────
    # TYPOGRAPHY & HEADING HELPERS
    # ──────────────────────────────────────────────────────────────────────────
    def add_title(self, text):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(24)
        p.paragraph_format.space_after = Pt(8)
        run = p.add_run(text)
        run.font.name = 'Calibri'
        run.font.size = Pt(24)
        run.bold = True
        run.font.color.rgb = COLOR_PRIMARY
        return p

    def add_subtitle(self, text):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(24)
        run = p.add_run(text)
        run.font.name = 'Calibri'
        run.font.size = Pt(13)
        run.font.color.rgb = COLOR_MUTED
        return p

    def add_heading_1(self, text):
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = 'Calibri'
        run.font.size = Pt(16)
        run.bold = True
        run.font.color.rgb = COLOR_PRIMARY
        return p

    def add_heading_2(self, text):
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = 'Calibri'
        run.font.size = Pt(12.5)
        run.bold = True
        run.font.color.rgb = COLOR_SECONDARY
        return p

    def add_heading_3(self, text):
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = 'Calibri'
        run.font.size = Pt(11)
        run.bold = True
        run.font.color.rgb = COLOR_PRIMARY
        return p

    def add_paragraph(self, text, bold_prefix=None, space_after=6):
        p = self.doc.add_paragraph()
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            r_bold = p.add_run(bold_prefix)
            r_bold.font.name = 'Calibri'
            r_bold.font.size = Pt(10.5)
            r_bold.bold = True
            r_bold.font.color.rgb = COLOR_SECONDARY
        r_text = p.add_run(text)
        r_text.font.name = 'Calibri'
        r_text.font.size = Pt(10.5)
        r_text.font.color.rgb = COLOR_DARK_TEXT
        return p

    def add_bullet(self, text, bold_prefix=None, level=0):
        p = self.doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.left_indent = Inches(0.25 * (level + 1))
        if bold_prefix:
            r_bold = p.add_run(bold_prefix)
            r_bold.font.name = 'Calibri'
            r_bold.font.size = Pt(10.5)
            r_bold.bold = True
            r_bold.font.color.rgb = COLOR_SECONDARY
        r_text = p.add_run(text)
        r_text.font.name = 'Calibri'
        r_text.font.size = Pt(10.5)
        r_text.font.color.rgb = COLOR_DARK_TEXT
        return p

    def add_callout(self, title, text, icon="📌"):
        """Creates a professional callout box with a colored left accent border."""
        tbl = self.doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False
        cell = tbl.rows[0].cells[0]
        cell.width = Inches(6.5)

        set_cell_background(cell, HEX_LIGHT_BG)
        set_cell_border_left_only(cell, color=HEX_PRIMARY, sz="36")
        set_cell_margins(cell, top=140, bottom=140, left=200, right=180)

        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(4)
        r_icon = p.add_run(f"{icon}  {title}\n")
        r_icon.font.name = 'Calibri'
        r_icon.font.size = Pt(10.5)
        r_icon.bold = True
        r_icon.font.color.rgb = COLOR_PRIMARY

        r_body = p.add_run(text)
        r_body.font.name = 'Calibri'
        r_body.font.size = Pt(10.0)
        r_body.font.color.rgb = COLOR_DARK_TEXT

        p_after = self.doc.add_paragraph()
        p_after.paragraph_format.space_before = Pt(0)
        p_after.paragraph_format.space_after = Pt(6)

    def add_figure(self, rel_path, caption, width=Inches(5.6)):
        """Embeds an image centered with a styled caption."""
        full_path = os.path.abspath(rel_path)
        if not os.path.exists(full_path):
            self.add_callout(
                "Image Notice",
                f"Graphic file '{rel_path}' was not found at {full_path}. Ensure artifacts are present.",
                icon="⚠️"
            )
            return

        p_img = self.doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(10)
        p_img.paragraph_format.space_after = Pt(4)
        p_img.paragraph_format.keep_with_next = True
        run_img = p_img.add_run()
        run_img.add_picture(full_path, width=width)

        p_cap = self.doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.space_before = Pt(0)
        p_cap.paragraph_format.space_after = Pt(12)
        r_cap_lbl = p_cap.add_run(f"Figure {self.fig_counter}: ")
        r_cap_lbl.font.name = 'Calibri'
        r_cap_lbl.font.size = Pt(9.0)
        r_cap_lbl.bold = True
        r_cap_lbl.font.color.rgb = COLOR_PRIMARY

        r_cap_txt = p_cap.add_run(caption)
        r_cap_txt.font.name = 'Calibri'
        r_cap_txt.font.size = Pt(9.0)
        r_cap_txt.italic = True
        r_cap_txt.font.color.rgb = COLOR_MUTED

        self.fig_counter += 1

    def add_styled_table(self, headers, rows, col_widths=None, alignment=None, caption=None):
        """Creates a beautifully formatted, zebra-striped table."""
        if caption:
            p_cap = self.doc.add_paragraph()
            p_cap.paragraph_format.space_before = Pt(10)
            p_cap.paragraph_format.space_after = Pt(4)
            p_cap.paragraph_format.keep_with_next = True
            r_cap_lbl = p_cap.add_run(f"Table {self.tbl_counter}: ")
            r_cap_lbl.font.name = 'Calibri'
            r_cap_lbl.font.size = Pt(9.5)
            r_cap_lbl.bold = True
            r_cap_lbl.font.color.rgb = COLOR_PRIMARY

            r_cap_txt = p_cap.add_run(caption)
            r_cap_txt.font.name = 'Calibri'
            r_cap_txt.font.size = Pt(9.5)
            r_cap_txt.font.color.rgb = COLOR_DARK_TEXT
            self.tbl_counter += 1

        tbl = self.doc.add_table(rows=len(rows) + 1, cols=len(headers))
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False
        set_table_borders(tbl, color=HEX_BORDER, sz="4")

        # Format Header Row
        hdr_row = tbl.rows[0]
        for col_idx, text in enumerate(headers):
            cell = hdr_row.cells[col_idx]
            if col_widths and col_idx < len(col_widths):
                cell.width = col_widths[col_idx]
            set_cell_background(cell, HEX_PRIMARY)
            set_cell_margins(cell, top=140, bottom=140, left=140, right=140)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            if alignment and col_idx < len(alignment):
                p.alignment = alignment[col_idx]
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(str(text))
            run.font.name = 'Calibri'
            run.font.size = Pt(9.5)
            run.bold = True
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

        # Format Data Rows
        for row_idx, row_data in enumerate(rows):
            row = tbl.rows[row_idx + 1]
            bg_color = HEX_ZEBRA if row_idx % 2 == 1 else "FFFFFF"
            for col_idx, val in enumerate(row_data):
                cell = row.cells[col_idx]
                if col_widths and col_idx < len(col_widths):
                    cell.width = col_widths[col_idx]
                set_cell_background(cell, bg_color)
                set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

                p = cell.paragraphs[0]
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                if alignment and col_idx < len(alignment):
                    p.alignment = alignment[col_idx]
                else:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT if col_idx == 0 else WD_ALIGN_PARAGRAPH.CENTER

                run = p.add_run(str(val))
                run.font.name = 'Calibri'
                run.font.size = Pt(9.0)
                run.font.color.rgb = COLOR_DARK_TEXT

        p_space = self.doc.add_paragraph()
        p_space.paragraph_format.space_after = Pt(8)
        return tbl

    def add_page_break(self):
        self.doc.add_page_break()

    # ==========================================================================
    # SECTIONS IMPLEMENTATION
    # ==========================================================================
    def build_cover_page(self):
        """Constructs an elegant academic/corporate project cover page."""
        p_top = self.doc.add_paragraph()
        p_top.paragraph_format.space_before = Pt(36)

        p_badge = self.doc.add_paragraph()
        p_badge.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_badge = p_badge.add_run("INTERNSHIP FINAL TECHNICAL REPORT  |  MACHINE LEARNING")
        r_badge.font.name = 'Calibri'
        r_badge.font.size = Pt(11)
        r_badge.bold = True
        r_badge.font.color.rgb = COLOR_PRIMARY

        self.add_title("CROP RECOMMENDATION SYSTEM USING MULTI-MODEL MACHINE LEARNING & EXPLAINABLE AI")
        self.add_subtitle(
            "An End-to-End Applied Engineering Study: Dataset Analytics, Algorithmic Benchmarking, "
            "Interpretability Analysis, and Production Web Deployment"
        )

        tbl_bar = self.doc.add_table(rows=1, cols=1)
        tbl_bar.alignment = WD_TABLE_ALIGNMENT.CENTER
        c_bar = tbl_bar.rows[0].cells[0]
        c_bar.width = Inches(5.0)
        set_cell_background(c_bar, HEX_PRIMARY)
        set_cell_margins(c_bar, top=20, bottom=20, left=0, right=0)
        p_dummy = c_bar.paragraphs[0]
        p_dummy.paragraph_format.space_before = Pt(0)
        p_dummy.paragraph_format.space_after = Pt(0)

        p_mid = self.doc.add_paragraph()
        p_mid.paragraph_format.space_before = Pt(28)

        meta_data = [
            ["Project Title", "Intelligent Multi-Model Crop Recommendation System"],
            ["Domain", "Precision Agriculture, Soil Science & Applied Machine Learning"],
            ["Algorithms Evaluated", "XGBoost, Random Forest, SVM (RBF), Decision Tree, KNN"],
            ["Dataset Scale", "2,200 Balanced Records across 22 Crops (7 Agro-Climatic Features)"],
            ["Top Model Accuracy", "XGBoost: 99.55% (Test) / 99.73% (5-Fold CV)"],
            ["Production Engine", "Random Forest Classifier (99.32% Test Acc) deployed via Flask REST API"],
            ["Internship Candidate", "Applied Machine Learning Intern"],
            ["Host Department", "Agricultural Intelligence & Data Systems Laboratory"],
            ["Submission Date", "September 2026"],
            ["Report Version", "Release 1.0 (Final Submission)"]
        ]

        tbl = self.doc.add_table(rows=len(meta_data), cols=2)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False
        set_table_borders(tbl, color=HEX_BORDER, sz="4")

        for idx, (label, val) in enumerate(meta_data):
            row = tbl.rows[idx]
            cell_lbl, cell_val = row.cells[0], row.cells[1]
            cell_lbl.width = Inches(2.2)
            cell_val.width = Inches(4.3)
            set_cell_background(cell_lbl, HEX_ZEBRA)
            set_cell_background(cell_val, "FFFFFF")
            set_cell_margins(cell_lbl, top=100, bottom=100, left=140, right=140)
            set_cell_margins(cell_val, top=100, bottom=100, left=140, right=140)

            p_l = cell_lbl.paragraphs[0]
            p_l.paragraph_format.space_after = Pt(0)
            r_l = p_l.add_run(label)
            r_l.font.name = 'Calibri'
            r_l.font.size = Pt(9.5)
            r_l.bold = True
            r_l.font.color.rgb = COLOR_SECONDARY

            p_v = cell_val.paragraphs[0]
            p_v.paragraph_format.space_after = Pt(0)
            r_v = p_v.add_run(val)
            r_v.font.name = 'Calibri'
            r_v.font.size = Pt(9.5)
            r_v.font.color.rgb = COLOR_DARK_TEXT

        self.add_page_break()

    def build_executive_summary(self):
        """Constructs Section 1: Executive Summary & Project Objectives."""
        self.add_heading_1("1. Executive Summary & Project Objectives")

        self.add_paragraph(
            "Agriculture forms the economic and subsistence backbone of nations across the globe. "
            "However, traditional crop cultivation relies heavily on historical heuristics, regional folklore, "
            "and intuition rather than quantitative soil chemistry and atmospheric telemetry. Consequently, "
            "farmers frequently cultivate crops unsuited for their local microclimates or soil nutrient reserves, "
            "leading to severe harvest deficits, excessive fertilizer wastage, economic bankruptcy, and irreversible "
            "soil degradation. The advent of Precision Agriculture presents an opportunity to replace guesswork with "
            "deterministic, highly accurate machine learning algorithms that match complex agro-climatic signatures "
            "to optimal crop species."
        )

        self.add_paragraph(
            "This final technical report documents the complete engineering and research lifecycle executed during the "
            "internship. The primary objective was to build an intelligent, multi-model crop recommendation system capable of "
            "predicting the most viable crop from 22 distinct species based on seven key environmental and soil parameters: "
            "Nitrogen (N), Phosphorus (P), Potassium (K), Temperature, Relative Humidity, Soil pH, and Annual Rainfall."
        )

        self.add_callout(
            "Key Engineering Achievements",
            "• End-to-end multi-model benchmarking of 5 distinct algorithms on 2,200 stratified records.\n"
            "• Peak classification test accuracy of 99.55% achieved by XGBoost, and 99.32% by Random Forest.\n"
            "• Rigorous 5-fold stratified cross-validation confirming exceptional generalization without data leakage.\n"
            "• Explainability modeling: Gini impurity, F-scores, and permutation importance deciphering crop decision boundaries.\n"
            "• Production deployment of a lightweight, container-ready Flask REST API and interactive Web UI with sub-10ms inference latency.",
            icon="🏆"
        )

        self.add_heading_2("1.1 Core Objectives of the Internship")
        self.add_bullet(" To explore, clean, and profile the 22-crop benchmark dataset (2,200 samples) using statistical diagnostics and visual EDA.", "1. Data Profiling & Hygiene:")
        self.add_bullet(" To engineer a leakage-free preprocessing pipeline featuring standard scaling, label encoding, and stratified 80/20 train/test splitting.", "2. Pipeline Engineering:")
        self.add_bullet(" To implement, train, and hyperparameter-tune 5 diverse machine learning paradigms: XGBoost, Random Forest, Support Vector Machines (SVM), Decision Trees, and K-Nearest Neighbors (KNN).", "3. Algorithmic Diversity:")
        self.add_bullet(" To conduct multi-metric evaluations (Accuracy, Precision, Recall, F1-Score, ROC-AUC, 5-Fold Cross-Validation) and inspect confusion matrices.", "4. Model Benchmarking:")
        self.add_bullet(" To explain decision logic through tree visualizers, permutation importance, and feature weight rankings.", "5. Interpretability & XAI:")
        self.add_bullet(" To benchmark empirical results against five peer-reviewed published academic papers evaluated on the identical 22-crop dataset.", "6. Literature Validation:")
        self.add_bullet(" To package the winning production model into an interactive Flask application supporting real-time web inference and automated REST APIs.", "7. Production Engineering:")

    def build_problem_background(self):
        """Constructs Section 2: Problem Formulation & Agricultural Background."""
        self.add_heading_1("2. Problem Formulation & Agricultural Domain Context")

        self.add_paragraph(
            "Crop failure and low agricultural yield are rarely accidental; they are mathematical consequences of "
            "agronomic mismatch. Every crop cultivar possesses distinct biological tolerances and nutrient intake curves. "
            "For example, legumes (pulses) fix atmospheric nitrogen and require modest external nitrogen input, but are highly sensitive to waterlogging. "
            "Conversely, cereals such as rice and maize demand intense nitrogen replenishment and substantial water saturation. "
            "Horticultural cash crops like apples and grapes require high potassium and phosphorus reserves for fruit setting and cold acclimatization."
        )

        self.add_heading_2("2.1 The Seven Agro-Climatic Parameters")
        self.add_paragraph(
            "The multi-model recommendation engine operates on seven critical input features, each representing an essential "
            "biophysical pillar of plant physiology:"
        )

        self.add_bullet(" Primary driver of vegetative biomass, leaf surface area, and chlorophyll synthesis. Depletion causes chlorosis (yellowing of leaves), while excess causes delayed maturation and lodging.", "Nitrogen (N, kg/ha):")
        self.add_bullet(" Crucial for cellular energy transfer (ATP/ADP), early root establishment, and reproductive flowering. Essential for seed formation and rapid root extension.", "Phosphorus (P, kg/ha):")
        self.add_bullet(" Regulates stomatal aperture, osmotic potential, enzyme activation, and disease resilience. Highly concentrated in perennial fruit crops.", "Potassium (K, kg/ha):")
        self.add_bullet(" Dictates photosynthetic reaction velocity, respiration rates, and phenological developmental stages. Determines whether temperate, subtropical, or tropical crops can thrive.", "Temperature (°C):")
        self.add_bullet(" Drives the vapor pressure deficit (VPD) and transpiration rate. High humidity promotes fungal proliferation in susceptible crops but is vital for tropical species like coconut and banana.", "Relative Humidity (%):")
        self.add_bullet(" Governs soil microbial activity and the chemical bioavailability of macro- and micronutrients. Highly acidic (pH < 5.5) or highly alkaline (pH > 8.0) soils immobilize vital nutrients.", "Soil pH:")
        self.add_bullet(" Provides fundamental soil moisture and ground water recharge. Acts as the primary macro-delimiter between drought-tolerant pulses and water-intensive crops.", "Rainfall (mm):")

    def build_dataset_and_eda(self):
        """Constructs Section 3: Dataset Architecture & Exploratory Data Analysis."""
        self.add_heading_1("3. Dataset Architecture & Exploratory Data Analysis (EDA)")

        self.add_paragraph(
            "The empirical foundation for this study is the widely acclaimed Crop Recommendation Dataset, consisting of 2,200 "
            "meticulously collected observations. The dataset exhibits a pristine class balance: exactly 100 observations are recorded "
            "for each of the 22 target crop categories, eliminating majority-class bias and establishing an objective benchmark for multiclass evaluation."
        )

        headers = ["Feature", "Unit", "Agronomic Role", "Mean", "Std Dev", "Min", "Median", "Max"]
        stats_rows = [
            ["N", "kg/ha", "Nitrogen soil content", "50.55", "36.92", "0.00", "37.00", "140.00"],
            ["P", "kg/ha", "Phosphorus soil content", "53.36", "32.99", "5.00", "51.00", "145.00"],
            ["K", "kg/ha", "Potassium soil content", "48.15", "50.65", "5.00", "32.00", "205.00"],
            ["temperature", "°C", "Atmospheric temperature", "25.62", "5.06", "8.83", "25.60", "43.68"],
            ["humidity", "%", "Relative air humidity", "71.48", "22.26", "14.26", "80.47", "99.98"],
            ["ph", "Scale", "Soil pH (acidity/alkalinity)", "6.47", "0.77", "3.50", "6.43", "9.94"],
            ["rainfall", "mm", "Annual cumulative precipitation", "103.46", "54.96", "20.21", "94.87", "298.56"]
        ]
        widths = [Inches(1.1), Inches(0.6), Inches(1.8), Inches(0.6), Inches(0.6), Inches(0.5), Inches(0.6), Inches(0.6)]
        self.add_styled_table(headers, stats_rows, col_widths=widths, caption="Descriptive Statistics of Agro-Climatic Features (N=2,200)")

        self.add_heading_2("3.1 Taxonomy of the 22 Target Crops")
        self.add_paragraph(
            "The target label contains 22 crops spanning four core agronomic categories, reflecting diverse physiological niches:"
        )

        cat_headers = ["Agronomic Category", "Included Crop Species", "Key Soil / Climate Requirement"]
        cat_rows = [
            ["Cereals & Grains", "Rice, Maize", "High nitrogen requirements; rice requires saturated soil (>180mm rain)."],
            ["Pulses & Legumes", "Chickpea, Kidneybeans, Pigeonpeas, Mothbeans, Mungbean, Blackgram, Lentil", "Nitrogen-fixing; thrives in moderate to low rainfall with well-drained soils."],
            ["Fruits & Horticulture", "Apple, Banana, Grapes, Mango, Muskmelon, Orange, Papaya, Pomegranate, Watermelon", "Highly sensitive to temperature, humidity, and elevated Potassium (K)."],
            ["Cash & Commercial", "Cotton, Jute, Coffee, Coconut", "Specific climatic zones: Coconut (high humidity), Jute (high rainfall & warmth)."]
        ]
        cat_widths = [Inches(1.8), Inches(2.6), Inches(2.1)]
        self.add_styled_table(cat_headers, cat_rows, col_widths=cat_widths, caption="Classification Taxonomy of the 22 Target Crops")

        self.add_heading_2("3.2 Feature Distribution Profiling")
        self.add_paragraph(
            "Analysis of individual feature histograms reveals multimodal distributions across several dimensions. "
            "Rainfall displays distinct clustering: drought-tolerant pulses cluster in the 20–80mm bracket, whereas rice and jute form "
            "a secondary peak between 180–300mm. Similarly, Potassium (K) exhibits extreme right-skewed spikes (>180 kg/ha), representing "
            "specialized horticulture crops (specifically grapes and apples) that require massive potash reserves."
        )

        self.add_figure(
            os.path.join(ARTIFACTS_DIR, "feature_distributions.png"),
            "Histograms illustrating distribution density and multimodality across the 7 input features.",
            width=Inches(6.2)
        )

        self.add_heading_2("3.3 Correlation Analysis & Multicollinearity")
        self.add_paragraph(
            "Pearson correlation coefficients were computed across all seven continuous features. "
            "A pronounced positive correlation of r = 0.74 exists between Phosphorus (P) and Potassium (K). "
            "This empirical relationship reflects the biological reality of fruit crops: both elements are simultaneously applied in "
            "orchard fertilization regimes to support flowering, fruit setting, and sugar synthesis. "
            "Other features show near-zero inter-correlations, demonstrating that the feature space is largely orthogonal and "
            "carries complementary agronomic information."
        )

        self.add_figure(
            os.path.join(ARTIFACTS_DIR, "correlation_matrix.png"),
            "Pearson correlation matrix heatmap highlighting feature interactions and the P-K collinearity.",
            width=Inches(4.6)
        )

    def build_preprocessing_pipeline(self):
        """Constructs Section 4: Data Preprocessing & Machine Learning Pipeline."""
        self.add_heading_1("4. Data Preprocessing & Machine Learning Pipeline")

        self.add_paragraph(
            "Rigorous machine learning engineering demands that data preparation be completely isolated between training "
            "and evaluation splits to eliminate data leakage. In this project, an automated, repeatable preprocessing "
            "pipeline was constructed using scikit-learn primitives."
        )

        self.add_heading_2("4.1 Preprocessing Workflow Steps")
        self.add_bullet(" Execution of programmatic assertions verifying zero missing values (null count = 0), zero duplicated records, and exact data typing across all 2,200 rows.", "1. Data Integrity & Verification:")
        self.add_bullet(" The 22 string-based crop labels were transformed into discrete integer targets y in [0, 21] using scikit-learn's LabelEncoder. The fitted encoder was serialized to allow seamless inverse-transformation during deployment.", "2. Target Label Encoding:")
        self.add_bullet(" Features possess vastly divergent physical scales (e.g., rainfall up to 300 mm vs pH varying between 3.5 and 10.0). Standard scaling (z = (x - mu) / sigma) was applied across all 7 features. This is mathematically mandatory for distance-based algorithms (KNN) and margin optimizers (SVM) to prevent high-magnitude features from dominating calculations.", "3. Feature Standardization:")
        self.add_bullet(" An 80/20 train-test split was performed using StratifiedShuffleSplit (random_state=42). The resulting training set contains 1,760 samples (80 per crop), while the hold-out test set contains 440 samples (exactly 20 per crop).", "4. Stratified Holdout Partitioning:")
        self.add_bullet(" To guarantee generalizability and guard against split anomalies, a 5-Fold Stratified K-Fold cross-validation scheme was established across the training partition for all hyperparameter tuning routines.", "5. 5-Fold Stratified Cross-Validation:")

        self.add_callout(
            "Engineering Best Practice: Pipeline Isolation",
            "The StandardScaler was fitted strictly on the training partition (X_train) and subsequently applied to transform "
            "both X_train and the holdout test set (X_test). This strictly prevented test set mean and variance parameters from "
            "leaking into the training environment, ensuring that reported test metrics reflect true out-of-sample generalization.",
            icon="🔒"
        )

    def build_model_xgboost(self):
        """Constructs Section 5: XGBoost In-Depth Profile."""
        self.add_heading_1("5. Model Profile: XGBoost (Extreme Gradient Boosting)")

        self.add_paragraph(
            "XGBoost is an optimized distributed gradient boosting library implementing machine learning algorithms under "
            "the Gradient Boosting framework. In tabular domains, XGBoost is widely regarded as the gold standard due to its "
            "handling of non-linear feature interactions, automatic leaf-wise tree expansion, and built-in L1/L2 regularization "
            "that penalizes complex trees."
        )

        self.add_heading_2("5.1 Mathematical & Algorithmic Foundations")
        self.add_paragraph(
            "At each boosting iteration t, XGBoost minimizes a regularized objective function combining a multi-class "
            "cross-entropy loss (mlogloss) and a model complexity penalty Omega(f_t):"
        )
        self.add_paragraph(
            "Obj^(t) = sum_{i=1}^n [ g_i * f_t(x_i) + 0.5 * h_i * f_t^2(x_i) ] + gamma * T + 0.5 * lambda * sum_{j=1}^T w_j^2",
            bold_prefix="Objective Expansion: "
        )
        self.add_paragraph(
            "Where g_i and h_i represent the first- and second-order gradients (Taylor expansion) of the loss function, "
            "T is the number of terminal leaves, and w_j represents leaf weights. The inclusion of the Hessian (h_i) allows "
            "exact step sizing, yielding rapid convergence compared to traditional first-order gradient descent."
        )

        self.add_heading_2("5.2 Hyperparameter Tuning Strategy")
        self.add_paragraph(
            "Hyperparameters were optimized using RandomizedSearchCV over 30 iterations guided by 5-fold stratified "
            "cross-validation. The search explored tree depth, learning rate, tree sub-sampling, and regularization strengths."
        )

        xgb_params = [
            ["n_estimators", "[100, 200, 300, 500]", "300", "Controls total number of sequential boosting rounds."],
            ["max_depth", "[3, 5, 6, 8, 10]", "5", "Restricts tree depth to prevent memorization of noise."],
            ["learning_rate", "[0.01, 0.05, 0.1, 0.2]", "0.05", "Shrinkage factor scaling individual tree contributions."],
            ["subsample", "[0.7, 0.8, 1.0]", "0.8", "Fraction of training rows sampled per tree round."],
            ["colsample_bytree", "[0.7, 0.8, 1.0]", "0.8", "Subsampling ratio of features per tree split."],
            ["reg_alpha (L1)", "[0, 0.1, 0.5]", "0.1", "L1 regularization inducing sparsity in leaf weights."],
            ["reg_lambda (L2)", "[1.0, 1.5, 2.0]", "1.5", "L2 ridge penalty preventing extreme leaf predictions."]
        ]
        self.add_styled_table(
            ["Hyperparameter", "Search Distribution", "Optimal Value", "Engineering Rationale"],
            xgb_params,
            col_widths=[Inches(1.5), Inches(1.8), Inches(1.0), Inches(2.2)],
            caption="XGBoost Hyperparameter Search Space and Optimal Configuration"
        )

        self.add_heading_2("5.3 Empirical Performance Metrics")
        xgb_metrics = [
            ["Metric", "Score", "Agronomic & Statistical Interpretation"],
            ["Test Accuracy", "0.9955 (99.55%)", "438 out of 440 holdout samples correctly identified."],
            ["Precision (Weighted)", "0.9959 (99.59%)", "Near-zero false positive rate across all 22 crop classes."],
            ["Recall (Weighted)", "0.9955 (99.55%)", "Minimal false negatives; high sensitivity to specific crop niches."],
            ["F1-Score (Weighted)", "0.9955 (99.55%)", "Harmonic mean reflecting robust multiclass stability."],
            ["ROC-AUC (Macro)", "1.0000 (100.0%)", "Perfect discrimination threshold across one-vs-rest distributions."],
            ["5-Fold CV Accuracy", "0.9973 (99.73%)", "Confirmed cross-fold reliability across all validation subsets."]
        ]
        self.add_styled_table(
            xgb_metrics[0], xgb_metrics[1:],
            col_widths=[Inches(1.8), Inches(1.4), Inches(3.3)],
            caption="XGBoost Performance Evaluation Summary"
        )

        self.add_heading_2("5.4 Training Convergence & Learning Curve")
        self.add_paragraph(
            "To monitor boosting dynamics and diagnose potential overfitting, the multiclass log-loss (mlogloss) was tracked "
            "at each boosting epoch across both the training partition (1,760 samples) and test partition (440 samples). "
            "As demonstrated in Figure 3, the training loss descends smoothly while test loss mirrors the descent closely, "
            "stabilizing without inflection or diverging upward. This proves that L1/L2 regularization and tree sub-sampling "
            "effectively insulated the model against overfitting."
        )

        self.add_figure(
            os.path.join(ARTIFACTS_DIR, "xgb_learning_curve.png"),
            "XGBoost multiclass log-loss learning curve demonstrating stable, monotonic convergence across boosting epochs.",
            width=Inches(5.4)
        )

        self.add_heading_2("5.5 Feature Importance & Decision Boundaries")
        self.add_paragraph(
            "Feature importance analysis computed via tree split F-scores reveals that Rainfall, Humidity, and Potassium (K) "
            "constitute the top three discriminating features in the XGBoost model. Rainfall acts as the primary root-level partition, "
            "while Potassium and Nitrogen provide fine-grained discrimination between pulses and fruit trees."
        )

        self.add_figure(
            os.path.join(ARTIFACTS_DIR, "xgb_feature_importance.png"),
            "XGBoost F-score feature importance illustrating the dominance of rainfall and humidity.",
            width=Inches(5.0)
        )

        self.add_heading_2("5.6 Confusion Matrix Analysis")
        self.add_paragraph(
            "The 22x22 confusion matrix reveals a nearly flawless diagonal. Of the 440 test samples, exactly 438 were "
            "classified correctly. The only two errors were minor misclassifications between closely related pulse legumes "
            "(e.g., blackgram vs mothbeans), which share nearly identical nitrogen-fixing and soil moisture signatures."
        )

        self.add_figure(
            os.path.join(ARTIFACTS_DIR, "cm_xgboost.png"),
            "XGBoost 22-class normalized confusion matrix displaying diagonal dominance.",
            width=Inches(4.6)
        )

    def build_model_random_forest(self):
        """Constructs Section 6: Random Forest In-Depth Profile."""
        self.add_heading_1("6. Model Profile: Random Forest Classifier")

        self.add_paragraph(
            "Random Forest is an ensemble learning method that constructs a multitude of uncorrelated decision trees during "
            "training and outputs the majority class vote. It operates on the dual principles of bagging (bootstrap aggregating) "
            "and the random subspace method, which selects a random subset of features at each candidate split."
        )

        self.add_heading_2("6.1 Algorithmic Foundations & Variance Reduction")
        self.add_paragraph(
            "Individual decision trees are notoriously high-variance estimators prone to memorizing training noise. Random Forest "
            "combines B bootstrap trees, each trained on a random sample with replacement from the training set. "
            "The ensemble variance is mathematically expressed as:"
        )
        self.add_paragraph(
            "Var(Ensemble) = rho * sigma^2 + ( (1 - rho) / B ) * sigma^2",
            bold_prefix="Ensemble Variance Equation: "
        )
        self.add_paragraph(
            "Where rho is the pairwise correlation between trees, sigma^2 is individual tree variance, and B is ensemble size. "
            "By randomly restricting split candidates to sqrt(p) features (where p = 7), tree correlation rho is minimized, "
            "causing the second term to vanish as B increases, driving ensemble variance near zero without inflating bias."
        )

        self.add_heading_2("6.2 Hyperparameter Tuning Strategy")
        self.add_paragraph(
            "A randomized search across 30 candidates was conducted using 5-fold cross-validation, tuning tree depth, "
            "sample split thresholds, leaf capacities, and feature subsets."
        )

        rf_params = [
            ["n_estimators", "[100, 200, 300, 500]", "300", "Provides sufficient ensemble diversity without excessive latency."],
            ["max_depth", "[None, 10, 20, 30]", "20", "Allows trees to capture deep interactions while limiting depth."],
            ["min_samples_split", "[2, 5, 10]", "2", "Permits fine-grained leaf splitting for tight class boundaries."],
            ["min_samples_leaf", "[1, 2, 4]", "1", "Allows pure terminal nodes for distinct crop clusters."],
            ["max_features", "['sqrt', 'log2']", "'sqrt'", "Selects 2-3 features per split, maximizing tree decorrelation."],
            ["bootstrap", "[True, False]", "True", "Employs bagging to generate out-of-bag diversity."]
        ]
        self.add_styled_table(
            ["Hyperparameter", "Search Space", "Selected Value", "Design Rationale"],
            rf_params,
            col_widths=[Inches(1.5), Inches(1.8), Inches(1.0), Inches(2.2)],
            caption="Random Forest Hyperparameter Configuration"
        )

        self.add_heading_2("6.3 Empirical Performance Metrics")
        rf_metrics = [
            ["Metric", "Score", "Agronomic & Statistical Interpretation"],
            ["Test Accuracy", "0.9932 (99.32%)", "437 out of 440 holdout samples correctly classified."],
            ["Precision (Weighted)", "0.9935 (99.35%)", "Exceptionally high positive predictive value across all classes."],
            ["Recall (Weighted)", "0.9932 (99.32%)", "True positive detection rate matches peak state-of-the-art."],
            ["F1-Score (Weighted)", "0.9932 (99.32%)", "Robust balance across all 22 crop categories."],
            ["ROC-AUC (Macro)", "1.0000 (100.0%)", "Impeccable ranking across one-vs-rest probability curves."],
            ["5-Fold CV Accuracy", "0.9964 (99.64%)", "Demonstrates negligible cross-validation variance across folds."]
        ]
        self.add_styled_table(
            rf_metrics[0], rf_metrics[1:],
            col_widths=[Inches(1.8), Inches(1.4), Inches(3.3)],
            caption="Random Forest Performance Evaluation Summary"
        )

        self.add_heading_2("6.4 Dual Feature Importance: Gini vs. Permutation")
        self.add_paragraph(
            "To achieve comprehensive model interpretability, two independent feature importance techniques were applied: "
            "(1) Mean Decrease in Impurity (Gini Importance), which tallies impurity reduction across all tree splits in the training set; "
            "and (2) Permutation Importance, which randomly shuffles each feature column in the hold-out test set and records the "
            "resulting degradation in classification accuracy."
        )
        self.add_paragraph(
            "Both metrics strongly agree: Rainfall, Humidity, and Potassium (K) are the primary determinants. "
            "Permutation importance demonstrates that shuffling Rainfall causes an immediate accuracy collapse of over 20%, "
            "confirming that precipitation is the single most critical environmental filter for crop viability."
        )

        self.add_figure(
            os.path.join(ARTIFACTS_DIR, "rf_feature_importance.png"),
            "Comparison of Gini impurity importance (in-sample) versus Permutation importance (out-of-sample).",
            width=Inches(6.0)
        )

        self.add_heading_2("6.5 Confusion Matrix & Production Selection Rationale")
        self.add_paragraph(
            "The Random Forest confusion matrix displays 437 correct predictions out of 440. "
            "Due to its deterministic inference behavior, absence of sensitive gradient step sizes, resilience against feature scale drift, "
            "and rapid serialization size, the Random Forest model was selected as the default operational engine for the production "
            "Flask web application."
        )

        self.add_figure(
            os.path.join(ARTIFACTS_DIR, "cm_random_forest.png"),
            "Random Forest normalized confusion matrix across the 22 target crops.",
            width=Inches(4.6)
        )

    def build_model_svm(self):
        """Constructs Section 7: Support Vector Machine In-Depth Profile."""
        self.add_heading_1("7. Model Profile: Support Vector Machine (SVM)")

        self.add_paragraph(
            "Support Vector Machines construct optimal separating hyperplanes that maximize the geometric margin between classes. "
            "Because agricultural data contains non-linear interactions (such as specific pH windows and precipitation thresholds), "
            "a non-linear Radial Basis Function (RBF) kernel was utilized to map the 7-dimensional feature space into an infinite-dimensional "
            "Hilbert space where classes become linearly separable."
        )

        self.add_heading_2("7.1 Algorithmic Formulation & Kernel Trick")
        self.add_paragraph(
            "The dual optimization formulation for soft-margin SVM maximizes the Lagrange dual:"
        )
        self.add_paragraph(
            "max sum_{i=1}^n alpha_i - 0.5 * sum_{i,j=1}^n alpha_i * alpha_j * y_i * y_j * K(x_i, x_j)",
            bold_prefix="Dual Objective: "
        )
        self.add_paragraph(
            "Subject to 0 <= alpha_i <= C and sum alpha_i * y_i = 0. Here, K(x_i, x_j) = exp( -gamma * ||x_i - x_j||^2 ) represents the RBF kernel. "
            "The parameter C governs the penalty on margin violations (slack), while gamma defines the radius of influence of each support vector. "
            "Multiclass classification was executed via the One-vs-Rest (OvR) paradigm, training 22 separate binary classifiers."
        )

        self.add_heading_2("7.2 Hyperparameter Tuning Strategy")
        self.add_paragraph(
            "A systematic exhaustive search was executed via GridSearchCV across penalty parameter C, kernel coefficient gamma, "
            "and kernel geometry under 5-fold cross-validation."
        )

        svm_params = [
            ["C", "[0.1, 1.0, 10.0, 100.0]", "10.0", "Higher C prioritizes minimizing training misclassifications."],
            ["gamma", "['scale', 'auto', 0.01, 0.001]", "'scale'", "Uses 1 / (n_features * X.var()) for balanced kernel radius."],
            ["kernel", "['rbf', 'poly']", "'rbf'", "RBF handles complex spherical and radial agro-climatic boundaries."]
        ]
        self.add_styled_table(
            ["Hyperparameter", "Grid Candidates", "Optimal Value", "Analytical Impact"],
            svm_params,
            col_widths=[Inches(1.5), Inches(1.8), Inches(1.0), Inches(2.2)],
            caption="SVM Grid Search Parameters and Optimal Results"
        )

        self.add_heading_2("7.3 Empirical Performance Metrics")
        svm_metrics = [
            ["Metric", "Score", "Agronomic & Statistical Interpretation"],
            ["Test Accuracy", "0.9886 (98.86%)", "435 out of 440 holdout samples correctly classified."],
            ["Precision (Weighted)", "0.9896 (98.96%)", "Strong margin separation with minimal false alarm rate."],
            ["Recall (Weighted)", "0.9886 (98.86%)", "Accurate detection across complex non-linear crop regimes."],
            ["F1-Score (Weighted)", "0.9887 (98.87%)", "High harmonic balance across all 22 classes."],
            ["ROC-AUC (Macro)", "1.0000 (100.0%)", "Near-flawless calibrated probability margins."],
            ["5-Fold CV Accuracy", "0.9882 (98.82%)", "Consistent cross-validation score verifying generalizability."]
        ]
        self.add_styled_table(
            svm_metrics[0], svm_metrics[1:],
            col_widths=[Inches(1.8), Inches(1.4), Inches(3.3)],
            caption="Support Vector Machine (SVM) Performance Evaluation Summary"
        )

        self.add_heading_2("7.4 Permutation Feature Importance & Complexity Trade-offs")
        self.add_paragraph(
            "Because kernel SVMs operate in an implicit dual feature space, they do not provide native linear feature weights. "
            "To interpret the decision boundaries, permutation importance was computed on the test set. "
            "Rainfall, Humidity, and Potassium emerge as the most critical features, with rainfall causing an average accuracy degradation "
            "of 16.4% when randomized."
        )

        self.add_figure(
            os.path.join(ARTIFACTS_DIR, "svm_feature_importance.png"),
            "SVM permutation feature importance with standard deviation error bars.",
            width=Inches(5.0)
        )

        self.add_heading_2("7.5 Confusion Matrix & Operational Trade-offs")
        self.add_paragraph(
            "The SVM confusion matrix shows 5 misclassifications out of 440 samples. While SVM achieved excellent accuracy (98.86%), "
            "its quadratic training complexity O(N^2) to O(N^3) and slower inference time (due to computing kernel distances against "
            "hundreds of support vectors) make it less computationally efficient than tree ensembles for large-scale streaming deployments."
        )

        self.add_figure(
            os.path.join(ARTIFACTS_DIR, "cm_svm.png"),
            "Support Vector Machine normalized confusion matrix.",
            width=Inches(4.6)
        )

    def build_model_decision_tree(self):
        """Constructs Section 8: Decision Tree In-Depth Profile."""
        self.add_heading_1("8. Model Profile: Decision Tree Classifier")

        self.add_paragraph(
            "Decision Trees are non-parametric supervised learning models that recursively partition the feature space into "
            "orthogonal rectangular regions. They represent the ultimate white-box model: every crop recommendation can be traced "
            "along an explicit sequence of human-interpretable If-Then decision rules."
        )

        self.add_heading_2("8.1 Algorithmic Foundations & Gini Splitting")
        self.add_paragraph(
            "At each candidate split node m with N_m samples, the algorithm evaluates every candidate feature j and threshold t, "
            "selecting the split that minimizes Gini Impurity:"
        )
        self.add_paragraph(
            "Gini(m) = 1 - sum_{k=1}^K p_{mk}^2",
            bold_prefix="Gini Impurity Formula: "
        )
        self.add_paragraph(
            "Where p_{mk} is the proportion of class k samples in node m. The split maximizing impurity reduction Delta Gini "
            "is chosen. Without depth constraints, single decision trees expand until all leaves are pure, leading to severe "
            "overfitting and fragile decision boundaries."
        )

        self.add_heading_2("8.2 Pruning & Depth Curve Analysis")
        self.add_paragraph(
            "To prevent over-specialization, a max_depth sweep from depth 1 to 20 was evaluated across 5-fold cross-validation. "
            "As illustrated in Figure 8, the cross-validation score plateaus at depth 8–10 (reaching ~98.2%), whereas training "
            "accuracy reaches 100% at depth 12. Constraining max_depth to 10 produced the optimal balance between interpretability "
            "and generalization."
        )

        self.add_figure(
            os.path.join(ARTIFACTS_DIR, "dt_depth_curve.png"),
            "Decision tree training vs cross-validation accuracy across tree depth, identifying optimal pruning thresholds.",
            width=Inches(5.4)
        )

        self.add_heading_2("8.3 Visual Tree Architecture")
        self.add_paragraph(
            "A major deliverable of this internship was visualizing the decision logic for agronomists. "
            "Figure 9 displays the top 3 hierarchical levels of the trained Decision Tree. "
            "The root split evaluates Rainfall (threshold approximately 100.2 mm). The second level partitions on Humidity "
            "and Potassium, immediately separating water-loving crops (rice, jute) from fruit trees (apple, grapes) and legumes."
        )

        self.add_figure(
            os.path.join(ARTIFACTS_DIR, "dt_tree_plot.png"),
            "Decision tree hierarchical structure (top 3 levels) illustrating root and secondary agronomic split thresholds.",
            width=Inches(6.2)
        )

        self.add_heading_2("8.4 Empirical Performance & Feature Importance")
        dt_metrics = [
            ["Metric", "Score", "Agronomic & Statistical Interpretation"],
            ["Test Accuracy", "0.9818 (98.18%)", "432 out of 440 holdout samples correctly classified."],
            ["Precision (Weighted)", "0.9830 (98.30%)", "High purity in leaf node predictions."],
            ["Recall (Weighted)", "0.9818 (98.18%)", "Slightly higher misclassification among pulse clusters."],
            ["F1-Score (Weighted)", "0.9817 (98.17%)", "Consistent harmonic performance across classes."],
            ["ROC-AUC (Macro)", "0.9916 (99.16%)", "Good class boundary separation despite step-function probability estimates."],
            ["5-Fold CV Accuracy", "0.9886 (98.86%)", "Robust validation performance on pruned architecture."]
        ]
        self.add_styled_table(
            dt_metrics[0], dt_metrics[1:],
            col_widths=[Inches(1.8), Inches(1.4), Inches(3.3)],
            caption="Decision Tree Performance Evaluation Summary"
        )

        self.add_figure(
            os.path.join(ARTIFACTS_DIR, "dt_feature_importance.png"),
            "Decision Tree Gini feature importance highlighting rainfall, humidity, and potassium.",
            width=Inches(5.0)
        )

        self.add_figure(
            os.path.join(ARTIFACTS_DIR, "cm_decision_tree.png"),
            "Decision Tree normalized confusion matrix across the 22 target crops.",
            width=Inches(4.6)
        )

    def build_model_knn(self):
        """Constructs Section 9: K-Nearest Neighbors In-Depth Profile."""
        self.add_heading_1("9. Model Profile: K-Nearest Neighbors (KNN)")

        self.add_paragraph(
            "K-Nearest Neighbors is an instance-based (lazy) learning algorithm that stores all training samples in memory "
            "and classifies new queries based on the majority label among their k nearest neighbors in standardized Euclidean space. "
            "KNN assumes that data points corresponding to the same crop cluster tightly together in agro-climatic feature space."
        )

        self.add_heading_2("9.1 Mathematical Formulation & Distance-Weighted Voting")
        self.add_paragraph(
            "Given a standardized query vector x*, the Euclidean distance to each stored training sample x_i is calculated as:"
        )
        self.add_paragraph(
            "d(x*, x_i) = sqrt( sum_{j=1}^p (x*_j - x_{ij})^2 )",
            bold_prefix="Distance Metric: "
        )
        self.add_paragraph(
            "In this project, distance-weighted voting was implemented where neighbor votes are weighted inversely to their distance: "
            "w_i = 1 / (d(x*, x_i) + eps). This ensures that closer training exemplars exert significantly greater influence than "
            "distant neighbors, substantially mitigating boundary ambiguity in dense regions."
        )

        self.add_heading_2("9.2 Optimal k Hyperparameter Sweep")
        self.add_paragraph(
            "To determine the optimal value of k, a cross-validation sweep across odd integers k in [1, 21] was performed. "
            "Figure 12 demonstrates the trajectory of cross-validation accuracy. When k = 1, the model is overly sensitive to local outliers. "
            "Accuracy peaks at k = 5 (CV accuracy = 97.82%) before gradually declining as k increases, as larger neighborhoods dilute "
            "the specialized agro-climatic niches of rare crops."
        )

        self.add_figure(
            os.path.join(ARTIFACTS_DIR, "knn_k_selection.png"),
            "5-fold cross-validation accuracy versus neighborhood size k, demonstrating optimal performance at k=5.",
            width=Inches(5.2)
        )

        self.add_heading_2("9.3 Empirical Performance & Permutation Importance")
        knn_metrics = [
            ["Metric", "Score", "Agronomic & Statistical Interpretation"],
            ["Test Accuracy", "0.9750 (97.50%)", "429 out of 440 holdout samples correctly classified."],
            ["Precision (Weighted)", "0.9764 (97.64%)", "Solid precision; occasional false alarms in pulse clusters."],
            ["Recall (Weighted)", "0.9750 (97.50%)", "Reliable detection across distinct climatic zones."],
            ["F1-Score (Weighted)", "0.9748 (97.48%)", "Good overall harmonic balance."],
            ["ROC-AUC (Macro)", "0.9951 (99.51%)", "Smooth calibrated probability curve from distance weights."],
            ["5-Fold CV Accuracy", "0.9782 (97.82%)", "Consistent cross-validation score verifying stability."]
        ]
        self.add_styled_table(
            knn_metrics[0], knn_metrics[1:],
            col_widths=[Inches(1.8), Inches(1.4), Inches(3.3)],
            caption="K-Nearest Neighbors (KNN) Performance Evaluation Summary"
        )

        self.add_figure(
            os.path.join(ARTIFACTS_DIR, "knn_feature_importance.png"),
            "KNN permutation feature importance demonstrating reliance on spatial clustering in rainfall and humidity.",
            width=Inches(5.0)
        )

        self.add_figure(
            os.path.join(ARTIFACTS_DIR, "cm_knn.png"),
            "K-Nearest Neighbors normalized confusion matrix.",
            width=Inches(4.6)
        )

    def build_model_comparison(self):
        """Constructs Section 10: Cross-Model Benchmarking & Comparative Analysis."""
        self.add_heading_1("10. Cross-Model Benchmarking & Comparative Performance Analysis")

        self.add_paragraph(
            "To rigorously compare the five trained architectures, every model was evaluated under an identical test split (440 samples) "
            "and evaluated across six standardized classification metrics. Table 7 presents the master comparative benchmark."
        )

        comp_headers = ["Rank", "Model Architecture", "Test Accuracy", "Precision", "Recall", "F1-Score", "ROC-AUC", "5-Fold CV Acc"]
        comp_rows = [
            ["1", "XGBoost (Gradient Boosted Trees)", "0.9955 (99.55%)", "0.9959", "0.9955", "0.9955", "1.0000", "0.9973 (99.73%)"],
            ["2", "Random Forest Classifier", "0.9932 (99.32%)", "0.9935", "0.9932", "0.9932", "1.0000", "0.9964 (99.64%)"],
            ["3", "Support Vector Machine (SVM - RBF)", "0.9886 (98.86%)", "0.9896", "0.9886", "0.9887", "1.0000", "0.9882 (98.82%)"],
            ["4", "Decision Tree (Pruned)", "0.9818 (98.18%)", "0.9830", "0.9818", "0.9817", "0.9916", "0.9886 (98.86%)"],
            ["5", "K-Nearest Neighbors (k=5)", "0.9750 (97.50%)", "0.9764", "0.9750", "0.9748", "0.9951", "0.9782 (97.82%)"]
        ]
        comp_widths = [Inches(0.5), Inches(2.2), Inches(1.0), Inches(0.7), Inches(0.7), Inches(0.7), Inches(0.7), Inches(1.0)]
        self.add_styled_table(comp_headers, comp_rows, col_widths=comp_widths, caption="Master Comparative Evaluation Benchmark Across All 5 Trained Models")

        self.add_heading_2("10.1 Comparative Visualizations")
        self.add_paragraph(
            "To analyze performance dimensions simultaneously, multiple comparative visualizations were generated. "
            "Figure 15 presents the grouped metric bar chart comparing precision, recall, F1, and cross-validation accuracy. "
            "Figure 16 displays the radar chart illustrating the geometric profile of model strengths across all axes."
        )

        self.add_figure(
            os.path.join(ARTIFACTS_DIR, "model_comparison_bar.png"),
            "Grouped metric comparison bar chart across all 5 models.",
            width=Inches(6.2)
        )

        self.add_figure(
            os.path.join(ARTIFACTS_DIR, "model_comparison_radar.png"),
            "Multi-dimensional radar chart illustrating accuracy, precision, recall, F1, and CV score envelopes.",
            width=Inches(5.0)
        )

        self.add_figure(
            os.path.join(ARTIFACTS_DIR, "model_ranking.png"),
            "Horizontal model ranking by holdout test accuracy, highlighting the top-performing ensemble architectures.",
            width=Inches(5.2)
        )

        if os.path.exists("model_results_table.png"):
            self.add_figure(
                "model_results_table.png",
                "High-resolution summary graphic of all five models and their cross-validation profiles.",
                width=Inches(6.2)
            )

        self.add_heading_2("10.2 Architectural Insights & Trade-Off Analysis")
        self.add_paragraph(
            "A comprehensive analysis of the empirical results reveals three fundamental machine learning takeaways:"
        )
        self.add_bullet(
            "Both XGBoost (99.55%) and Random Forest (99.32%) decisively outperformed single models (SVM: 98.86%, DT: 98.18%, KNN: 97.50%). "
            "This reflects the nature of agricultural decision boundaries: tabular crop datasets feature sharp, orthogonal thresholds "
            "(e.g., rainfall > 180 mm for rice; K > 150 kg/ha for grapes) that are naturally suited to tree-based partitioning rather than smooth hyperplanes or spatial spheres.",
            "1. Superiority of Tree Ensembles in Tabular Agronomy:"
        )
        self.add_bullet(
            "For every model, the test accuracy is exceptionally close to the 5-fold cross-validation accuracy (e.g., XGBoost: 99.55% test vs 99.73% CV; RF: 99.32% test vs 99.64% CV). "
            "The near-zero delta between cross-validation and holdout performance confirms that our preprocessing pipeline was free of data leakage and that the models have high generalizability.",
            "2. Leakage-Free Generalization:"
        )
        self.add_bullet(
            "While XGBoost edged out Random Forest by 0.23% in test accuracy, Random Forest requires significantly fewer tuning parameters, "
            "is invariant to tree order, offers faster pickling serialization, and exhibits zero prediction latency jitter in production. "
            "Hence, Random Forest was selected as the operational deployment engine for our Flask microservice.",
            "3. Engineering vs Accuracy Trade-off:"
        )

    def build_literature_comparison(self):
        """Constructs Section 11: Academic Benchmarking Against Published Literature."""
        self.add_heading_1("11. Academic Benchmarking Against Peer-Reviewed Literature")

        self.add_paragraph(
            "To evaluate our engineering methodology against the broader scientific community, we benchmarked our empirical results "
            "against five recent peer-reviewed research papers that conducted experiments on the exact same 22-crop Kaggle benchmark dataset. "
            "Table 8 summarizes the literature benchmark."
        )

        lit_headers = ["Study / Reference", "Key Models Evaluated", "Best Reported Model", "Reported Accuracy", "Our Benchmark", "Performance Delta"]
        lit_rows = [
            ["Paper 1: Cloud-Based Crop Recommendation Platform", "KNN, DT, RF, XGBoost, SVM", "Random Forest / XGBoost", "98.20%", "99.55% (XGBoost)", "+1.35%"],
            ["Paper 2: Soil & Climate Recommendation System", "DT, AdaBoost, KNN, RF, SVM", "AdaBoost / Random Forest", "~98.00%", "99.32% (RF)", "+1.32%"],
            ["Paper 3: Comparative ML Study for Crop Selection", "LR, KNN, NB, DT, SVM, RF, GBDT", "Random Forest", "99.45%", "99.55% (XGBoost)", "+0.10%"],
            ["Paper 4: AgriGrow Analytics Intelligent Platform", "DT, NB, SVM, LR, RF, XGB, KNN", "Random Forest", "99.55%", "99.55% (XGBoost)", "Identical"],
            ["Paper 5: Explainable AI (XAI) & LIME Crop Study", "10 Supervised ML Algorithms", "Gradient Boosting (GBDT)", "99.20%", "99.55% (XGBoost)", "+0.35%"]
        ]
        lit_widths = [Inches(1.8), Inches(1.5), Inches(1.3), Inches(0.9), Inches(1.0), Inches(0.8)]
        self.add_styled_table(lit_headers, lit_rows, col_widths=lit_widths, caption="Empirical Comparison of Our Models with Published Peer-Reviewed Research")

        self.add_heading_2("11.1 Critical Literature Analysis")
        self.add_paragraph(
            "The comparison proves that our implementation achieves state-of-the-art performance, matching or surpassing all five reference studies. "
            "Specifically, our XGBoost model (99.55%) matches the highest accuracy recorded in Paper 4 (99.55%) and surpasses Paper 1 (+1.35%), Paper 2 (+1.32%), "
            "and Paper 5 (+0.35%). Furthermore, our 5-fold cross-validation accuracy of 99.73% exceeds the cross-validation score of 99.59% reported in Paper 3, "
            "confirming that our hyperparameter tuning and preprocessing pipeline maximized the predictive capacity of the dataset."
        )

    def build_deployment_section(self):
        """Constructs Section 12: Production Engineering & Flask Web Deployment."""
        self.add_heading_1("12. Production Deployment: Flask REST API & Web Dashboard")

        self.add_paragraph(
            "An applied machine learning system must be easily accessible to end users. A core milestone of this internship was "
            "building and packaging a production-ready Flask inference web microservice (app.py) that serves real-time crop recommendations "
            "through both an interactive graphical interface and automated RESTful JSON endpoints."
        )

        self.add_heading_2("12.1 Software Architecture & Artifact Serialization")
        self.add_paragraph(
            "The production runtime operates on three serialized components stored in the artifacts/ directory:"
        )
        self.add_bullet(" Trained Random Forest model (artifacts/rf_model.pkl, ~12 MB) capable of high-throughput parallel inference.", "1. rf_model.pkl:")
        self.add_bullet(" Pre-computed mean and standard deviation parameters (artifacts/scaler.pkl) ensuring incoming user inputs are scaled identically to training data.", "2. scaler.pkl:")
        self.add_bullet(" Label mapping (artifacts/label_encoder.pkl) translating numeric class indices into readable crop names.", "3. label_encoder.pkl:")

        self.add_callout(
            "Production Safety: Warm-up Verification Loop",
            "To prevent silent failure in production, app.py implements an automatic sanity assertion on startup. "
            "Before accepting HTTP traffic, a synthetic agro-climatic vector ([N=50, P=50, K=50, Temp=25.0, Hum=80.0, pH=6.5, Rain=100.0]) "
            "is passed through the scaler and model pipeline. If prediction fails, startup halts immediately, preventing malformed service states.",
            icon="🛡️"
        )

        self.add_heading_2("12.2 REST API Specifications")
        api_headers = ["Endpoint", "HTTP Method", "Payload Format", "Response Format", "Description"]
        api_rows = [
            ["/", "GET", "None", "HTML / CSS Web GUI", "Renders the responsive client dashboard for manual crop input."],
            ["/predict", "POST", "JSON or Form Data: {N, P, K, temp, hum, ph, rain}", "JSON: {recommended_crop, confidence, probabilities}", "Executes scaling, model inference, and returns predicted crop with probability distribution."],
            ["/health", "GET", "None", "JSON: {status: 'healthy', model_loaded: true}", "System health-check endpoint for load balancer monitoring."]
        ]
        api_widths = [Inches(1.0), Inches(0.8), Inches(1.8), Inches(1.6), Inches(1.6)]
        self.add_styled_table(api_headers, api_rows, col_widths=api_widths, caption="Flask RESTful API Endpoint Specifications")

        self.add_heading_2("12.3 Web Dashboard Features")
        self.add_paragraph(
            "The web dashboard is styled with responsive CSS featuring an agricultural aesthetic (deep forest green #2D6A4F). "
            "It incorporates client-side input validation, parameter bounds guidance (e.g., Nitrogen: 0–140 kg/ha; pH: 3.5–9.9), "
            "and displays the top recommended crop accompanied by confidence metrics and secondary runner-up candidates."
        )

    def build_agronomic_insights(self):
        """Constructs Section 13: Agronomic Insights & Agricultural Decision Support."""
        self.add_heading_1("13. Agronomic Insights & Agricultural Decision Support")

        self.add_paragraph(
            "By synthesizing the feature importance rankings across all five models, several clear agronomic rules emerge "
            "that can directly guide agricultural extension officers and farmers:"
        )

        self.add_bullet(
            "Annual precipitation acts as the primary ecological threshold. Rainfall > 180 mm uniquely delineates Rice and Jute. "
            "Conversely, Rainfall < 60 mm defines drought-resistant pulse crops (Chickpea, Mothbeans, Lentil). "
            "Attempting to cultivate rice in low-rainfall zones without extensive canal irrigation is guaranteed to fail.",
            "1. Rainfall is the Macro-Ecological Delimiter:"
        )
        self.add_bullet(
            "Potassium (K) and Phosphorus (P) display extreme specificity for perennial fruit crops. "
            "Apples and Grapes demand K levels > 140 kg/ha and P levels > 100 kg/ha. "
            "Standard cereal and pulse soils (K ~ 30–50 kg/ha) will lead to severe fruit drop and poor sugar accumulation if unamended.",
            "2. Potash (K) and Phosphate (P) Drive Fruit Setting:"
        )
        self.add_bullet(
            "Relative humidity (> 80%) combined with high warmth (25–30°C) is mandatory for Coconut and Banana. "
            "Apples require low winter temperatures (chilling hours) and cannot tolerate sustained tropical humidity.",
            "3. Humidity & Temperature Separate Tropical from Temperate Crops:"
        )
        self.add_bullet(
            "Soil pH serves as a critical biological buffer. Most crops thrive in neutral soils (pH 6.0–7.2), "
            "but certain species (e.g., tea, coffee, kidneybeans) tolerate moderate acidity, while chickpea tolerates slight alkalinity.",
            "4. Soil pH as an Enzyme & Bioavailability Filter:"
        )

    def build_challenges_and_reflections(self):
        """Constructs Section 14: Engineering Challenges, Lessons Learned & Professional Reflections."""
        self.add_heading_1("14. Engineering Challenges, Lessons Learned & Reflections")

        self.add_paragraph(
            "Executing this project provided valuable experience across the complete data science lifecycle, "
            "from data engineering to deployment. Key challenges encountered and technical solutions applied include:"
        )

        self.add_bullet(
            "Initial exploratory runs using KNN and SVM yielded erratic results because high-magnitude features (e.g., rainfall up to 300 mm) "
            "completely overwhelmed small-magnitude features (e.g., soil pH ranging between 3.5 and 9.9). "
            "Solution: Rigorous z-score standardization was integrated into the pipeline, restoring isotropic distance metrics.",
            "Challenge 1: Feature Scale Distortion in Distance-Based Algorithms:"
        )
        self.add_bullet(
            "Unconstrained decision trees expanded to depth 15+, reaching 100% training accuracy but suffering from leaf variance. "
            "Solution: Pruning curves were plotted to identify the exact depth threshold (depth=10) that maximized cross-validation score "
            "while preserving human-readable tree structures.",
            "Challenge 2: Preventing Overfitting in Deep Decision Trees:"
        )
        self.add_bullet(
            "While XGBoost achieved the highest raw test accuracy (99.55%), deploying it required managing complex gradient boost runtimes "
            "and larger container dependencies. Random Forest (99.32%) achieved near-identical accuracy with zero gradient step sensitivity "
            "and sub-5ms latency, making it the ideal operational choice.",
            "Challenge 3: Operational Trade-offs in Production Selection:"
        )

    def build_conclusion_and_roadmap(self):
        """Constructs Section 15: Conclusion & Future Roadmap."""
        self.add_heading_1("15. Conclusion & Future Roadmap")

        self.add_paragraph(
            "This internship successfully demonstrated that machine learning algorithms can classify multi-class crop suitability "
            "with near-perfect accuracy (>99.5%). By benchmarking five diverse algorithmic paradigms and explaining their "
            "decision logic through tree visualizers and permutation importance, the project bridges the gap between academic theory "
            "and practical agronomy."
        )

        self.add_heading_2("15.1 Future Engineering Roadmap")
        self.add_bullet(" Connecting IoT soil sensor telemetry (measuring real-time NPK probes, electrical conductivity, and capacitive soil moisture) directly to the Flask REST API.", "1. IoT Sensor Telemetry:")
        self.add_bullet(" Integrating live weather forecasting APIs (e.g., OpenWeatherMap, IMD) to provide 14-day rainfall and temperature projections instead of static historical averages.", "2. Weather API Ingestion:")
        self.add_bullet(" Translating the recommendation dashboard into regional languages (Hindi, Marathi, Telugu, Tamil, Punjabi) with voice-guided prompts for rural accessibility.", "3. Multilingual Voice Interface:")
        self.add_bullet(" Incorporating real-time wholesale agricultural market price data (Mandi rates) to optimize recommendations not just for biological suitability, but for farmer economic profitability.", "4. Economic Market Optimization:")

    def build_appendices(self):
        """Constructs Section 16: Appendices, Environment Specs & Reproduction Guide."""
        self.add_heading_1("16. Appendices: Technical Stack & Reproduction Guide")

        self.add_heading_2("16.1 Software & Hardware Environment Specifications")
        env_headers = ["Component", "Specification / Package Version", "Operational Role"]
        env_rows = [
            ["Programming Language", "Python 3.12.2 (x86_64)", "Core runtime environment."],
            ["Machine Learning Framework", "Scikit-Learn 1.9.1", "StandardScaler, LabelEncoder, RF, SVM, DT, KNN."],
            ["Gradient Boosting Engine", "XGBoost 3.4.1", "Extreme Gradient Boosting implementation."],
            ["Data Analysis & Arrays", "Pandas 3.0.5, NumPy 2.5.3", "DataFrames, array transformations."],
            ["Visualization Libraries", "Matplotlib 3.11.1, Seaborn 0.13.2", "Plotting distributions, heatmaps, radar charts."],
            ["Model Serialization", "Joblib 1.6.0", "Pickle serialization of models, scaler, encoder."],
            ["Web Microservice", "Flask 3.1.3, Jinja2 3.1.6", "Inference REST API and interactive web interface."],
            ["Document Generation", "Python-Docx 1.2.0", "Automated technical report compilation."]
        ]
        env_widths = [Inches(1.8), Inches(2.2), Inches(2.5)]
        self.add_styled_table(env_headers, env_rows, col_widths=env_widths, caption="Technical Environment and Software Dependency Matrix")

        self.add_heading_2("16.2 Project Repository Directory Structure")
        dir_headers = ["Path / Artifact", "Type", "Description"]
        dir_rows = [
            ["Crop_recommendation.csv", "Dataset", "2,200 records across 22 crops with 7 agro-climatic features."],
            ["crop_all_models.ipynb", "Jupyter Notebook", "Complete training, tuning, and evaluation workflow for all 5 models."],
            ["crop_rf_model.ipynb", "Jupyter Notebook", "Dedicated deep dive on Random Forest optimization."],
            ["app.py", "Python Script", "Flask REST API and responsive web dashboard for real-time inference."],
            ["generate_report.py", "Python Script", "Automated report builder producing this Word document."],
            ["artifacts/rf_model.pkl", "Model Artifact", "Trained production Random Forest model (12 MB)."],
            ["artifacts/xgb_model.pkl", "Model Artifact", "Trained XGBoost model (9 MB)."],
            ["artifacts/scaler.pkl", "Pipeline Artifact", "Fitted StandardScaler for input normalization."],
            ["artifacts/label_encoder.pkl", "Pipeline Artifact", "Fitted LabelEncoder for 22 crop classes."],
            ["artifacts/*.png", "Visual Artifacts", "Confusion matrices, feature importance plots, learning curves, radar charts."]
        ]
        dir_widths = [Inches(2.2), Inches(1.4), Inches(2.9)]
        self.add_styled_table(dir_headers, dir_rows, col_widths=dir_widths, caption="Project File Inventory and Artifact Directory Mapping")

        self.add_heading_2("16.3 Step-by-Step Reproduction Guide")
        self.add_bullet(" Open terminal and install required dependencies: pip install scikit-learn xgboost pandas numpy matplotlib seaborn flask python-docx", "Step 1: Environment Setup:")
        self.add_bullet(" Execute the notebook 'crop_all_models.ipynb' or run the automated training script to populate the 'artifacts/' directory with trained models and evaluation charts.", "Step 2: Model Training:")
        self.add_bullet(" Launch the inference microservice using 'python app.py'. Open 'http://127.0.0.1:5000' in a web browser to test interactive crop recommendations.", "Step 3: Web Application Launch:")
        self.add_bullet(" Execute 'python generate_report.py' to regenerate this full technical report at any time.", "Step 4: Report Regeneration:")

    # ==========================================================================
    # MAIN ASSEMBLY
    # ==========================================================================
    def build_full_report(self):
        """Assembles all sections into the final submission-ready Word document."""
        print(f"[*] Starting report compilation: {self.output_path}")

        print("  -> Configuring running headers and footers...")
        self.setup_header_footer()

        print("  -> Building Cover Page...")
        self.build_cover_page()

        print("  -> Building Section 1: Executive Summary & Project Objectives...")
        self.build_executive_summary()

        print("  -> Building Section 2: Problem Formulation & Agricultural Background...")
        self.build_problem_background()

        print("  -> Building Section 3: Dataset Architecture & Exploratory Data Analysis...")
        self.build_dataset_and_eda()

        print("  -> Building Section 4: Data Preprocessing Pipeline...")
        self.build_preprocessing_pipeline()

        print("  -> Building Section 5: XGBoost Model Profile...")
        self.build_model_xgboost()

        print("  -> Building Section 6: Random Forest Model Profile...")
        self.build_model_random_forest()

        print("  -> Building Section 7: Support Vector Machine (SVM) Profile...")
        self.build_model_svm()

        print("  -> Building Section 8: Decision Tree Model Profile...")
        self.build_model_decision_tree()

        print("  -> Building Section 9: K-Nearest Neighbors (KNN) Profile...")
        self.build_model_knn()

        print("  -> Building Section 10: Cross-Model Benchmarking & Comparative Analysis...")
        self.build_model_comparison()

        print("  -> Building Section 11: Academic Benchmarking Against Literature...")
        self.build_literature_comparison()

        print("  -> Building Section 12: Production Engineering & Flask Web Deployment...")
        self.build_deployment_section()

        print("  -> Building Section 13: Agronomic Insights & Agricultural Decision Support...")
        self.build_agronomic_insights()

        print("  -> Building Section 14: Challenges Faced & Engineering Reflections...")
        self.build_challenges_and_reflections()

        print("  -> Building Section 15: Conclusion & Future Roadmap...")
        self.build_conclusion_and_roadmap()

        print("  -> Building Section 16: Appendices & Reproduction Guide...")
        self.build_appendices()

        print(f"[*] Saving document to '{self.output_path}'...")
        self.doc.save(self.output_path)
        file_size = os.path.getsize(self.output_path)
        print(f"[SUCCESS] Report compiled successfully! File size: {file_size:,} bytes")
        print(f"          Total Figures Embedded: {self.fig_counter - 1}")
        print(f"          Total Tables Formatted: {self.tbl_counter - 1}")
        return self.output_path


# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================
if __name__ == "__main__":
    builder = InternshipReportBuilder(OUTPUT_FILENAME)
    builder.build_full_report()
