from __future__ import annotations

from pathlib import Path
from textwrap import wrap

import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "pdf"
TMP_DIR = ROOT / "tmp" / "pdfs"
PDF_PATH = OUTPUT_DIR / "utrecht_low_contaminant_diet_report.pdf"
MD_PATH = OUTPUT_DIR / "utrecht_low_contaminant_diet_report.md"
HEATMAP_PATH = TMP_DIR / "utrecht_diet_heatmap.png"
BAR_PATH = TMP_DIR / "utrecht_diet_bar.png"


FOOD_ROWS = [
    {
        "food": "Utrecht tap water",
        "pfas": 0.5,
        "mercury": 0.0,
        "arsenic": 0.0,
        "cadmium": 0.0,
        "acrylamide": 0.0,
        "bpa": 0.0,
        "why": "Vitens water in Utrecht is mainly groundwater-based; RIVM still says tap water is safe, and groundwater is the lower-PFAS source type versus river water.",
        "action": "Keep as default drink.",
    },
    {
        "food": "Oats / oatmeal",
        "pfas": 0.0,
        "mercury": 0.0,
        "arsenic": 0.2,
        "cadmium": 0.5,
        "acrylamide": 0.0,
        "bpa": 0.0,
        "why": "Low concern staple compared with rice products and fried snacks.",
        "action": "Strong staple choice.",
    },
    {
        "food": "Wheat bread, not over-toasted",
        "pfas": 0.0,
        "mercury": 0.0,
        "arsenic": 0.3,
        "cadmium": 0.6,
        "acrylamide": 0.4,
        "bpa": 0.0,
        "why": "Bread shows up in MCP cadmium and lead contributor groups; acrylamide rises when bread is browned heavily.",
        "action": "Fine in normal amounts; toast lightly.",
    },
    {
        "food": "Boiled potatoes",
        "pfas": 0.0,
        "mercury": 0.0,
        "arsenic": 0.1,
        "cadmium": 0.6,
        "acrylamide": 0.0,
        "bpa": 0.0,
        "why": "Potatoes are a cadmium attention food in the MCP, but boiling avoids the acrylamide spike from frying.",
        "action": "Good staple rotation item.",
    },
    {
        "food": "Beans, lentils, tofu",
        "pfas": 0.0,
        "mercury": 0.0,
        "arsenic": 0.2,
        "cadmium": 0.5,
        "acrylamide": 0.0,
        "bpa": 0.1,
        "why": "Useful low-contaminant protein anchor when bought dry, chilled, or in glass/carton rather than cans.",
        "action": "Make these your default protein base.",
    },
    {
        "food": "Chicken / turkey",
        "pfas": 0.3,
        "mercury": 0.0,
        "arsenic": 0.0,
        "cadmium": 0.1,
        "acrylamide": 0.0,
        "bpa": 0.0,
        "why": "Lower contaminant concern than fish, shellfish, game meat, or offal in this review frame.",
        "action": "Good occasional animal protein.",
    },
    {
        "food": "Yogurt / kwark",
        "pfas": 0.6,
        "mercury": 0.0,
        "arsenic": 0.0,
        "cadmium": 0.0,
        "acrylamide": 0.0,
        "bpa": 0.0,
        "why": "Dairy is a PFAS context in NVWA and the MCP, but monitored Dutch milk values are low.",
        "action": "Prefer over frequent cheese if minimizing PFAS.",
    },
    {
        "food": "Cheese",
        "pfas": 0.9,
        "mercury": 0.0,
        "arsenic": 0.0,
        "cadmium": 0.0,
        "acrylamide": 0.0,
        "bpa": 0.0,
        "why": "Dairy lane, but more concentrated and easier to overuse as a daily protein source.",
        "action": "Keep modest; not your main protein.",
    },
    {
        "food": "Farmed salmon / trout",
        "pfas": 1.6,
        "mercury": 0.8,
        "arsenic": 0.0,
        "cadmium": 0.0,
        "acrylamide": 0.0,
        "bpa": 0.0,
        "why": "Fish is the biggest PFAS contributor in Dutch RIVM work; cultured salmon/trout is still a cleaner fish choice than high-mercury or self-caught options.",
        "action": "Keep to occasional use if you want fish.",
    },
    {
        "food": "Predatory fish / tuna / swordfish / shark",
        "pfas": 2.0,
        "mercury": 3.0,
        "arsenic": 0.0,
        "cadmium": 0.0,
        "acrylamide": 0.0,
        "bpa": 0.2,
        "why": "MCP mercury focus is large predatory fish; Dutch consumer advice also treats several species as higher-risk.",
        "action": "Best avoided for a low-contaminant pattern.",
    },
    {
        "food": "Commercial eggs",
        "pfas": 1.3,
        "mercury": 0.0,
        "arsenic": 0.0,
        "cadmium": 0.0,
        "acrylamide": 0.0,
        "bpa": 0.0,
        "why": "Dutch commercial eggs are monitored and usually below legal PFAS limits, but eggs are still a PFAS-sensitive lane.",
        "action": "Moderate use is fine; not a daily staple if minimizing PFAS.",
    },
    {
        "food": "Home-produced eggs",
        "pfas": 3.0,
        "mercury": 0.0,
        "arsenic": 0.0,
        "cadmium": 0.0,
        "acrylamide": 0.0,
        "bpa": 0.0,
        "why": "RIVM explicitly advised against eating home-produced eggs nationwide because PFAS can be high.",
        "action": "Avoid.",
    },
    {
        "food": "Rice / rice cakes / rice drinks",
        "pfas": 0.0,
        "mercury": 0.0,
        "arsenic": 2.5,
        "cadmium": 0.2,
        "acrylamide": 0.0,
        "bpa": 0.0,
        "why": "MCP inorganic arsenic focus explicitly flags rice and rice-based products.",
        "action": "Do not use as a daily staple; rotate with oats, potatoes, pasta, bread.",
    },
    {
        "food": "Doritos / chips / fries",
        "pfas": 0.1,
        "mercury": 0.0,
        "arsenic": 0.1,
        "cadmium": 0.2,
        "acrylamide": 3.0,
        "bpa": 0.0,
        "why": "Acrylamide is one of the clearest avoidable contaminant lanes in Dutch guidance, and chips are a major contributor.",
        "action": "Strongly reduce.",
    },
    {
        "food": "Coffee",
        "pfas": 0.0,
        "mercury": 0.0,
        "arsenic": 0.0,
        "cadmium": 0.0,
        "acrylamide": 1.8,
        "bpa": 0.0,
        "why": "Dutch guidance identifies coffee as an adult acrylamide contributor.",
        "action": "Moderate and alternate with tea and water.",
    },
    {
        "food": "Canned foods / canned drinks",
        "pfas": 0.0,
        "mercury": 0.0,
        "arsenic": 0.0,
        "cadmium": 0.0,
        "acrylamide": 0.0,
        "bpa": 2.0,
        "why": "The MCP keeps canned foods and beverage-contact contexts explicit for BPA review.",
        "action": "Prefer fresh, frozen, glass, or carton where practical.",
    },
    {
        "food": "Game meat / offal",
        "pfas": 0.0,
        "mercury": 0.0,
        "arsenic": 0.0,
        "cadmium": 0.8,
        "acrylamide": 0.0,
        "bpa": 0.0,
        "why": "MCP lead support makes game meat and offal explicit high-attention foods.",
        "action": "Avoid if the goal is lowest contaminant burden.",
    },
    {
        "food": "Molluscs / shellfish",
        "pfas": 1.0,
        "mercury": 0.8,
        "arsenic": 1.2,
        "cadmium": 2.5,
        "acrylamide": 0.0,
        "bpa": 0.0,
        "why": "MCP cadmium registry separates molluscs because occurrence can be comparatively elevated.",
        "action": "Occasional only, not a routine protein source.",
    },
]

CONTAMINANTS = ["pfas", "mercury", "arsenic", "cadmium", "acrylamide", "bpa"]
CONTAMINANT_LABELS = ["PFAS", "Mercury", "Arsenic", "Cadmium", "Acrylamide", "BPA"]
SOURCE_URLS = [
    ("RIVM PFAS intake in the Netherlands, 2023", "https://www.rivm.nl/en/news/new-study-confirms-people-in-netherlands-are-ingesting-too-much-levels-of-pfas"),
    ("RIVM PFAS in drinking water, 2022", "https://www.rivm.nl/en/news/pfas-levels-in-drinking-water-from-river-water-need-to-be-brought-down"),
    ("RIVM home-produced eggs advisory, 2025", "https://www.rivm.nl/en/news/rivm-advises-against-eating-home-produced-eggs"),
    ("NVWA PFAS in foods inspection results, 2025", "https://www.nvwa.nl/onderwerpen/voedselveiligheid/contaminanten-in-levensmiddelen/inspectieresultaten/2025/pfas-in-levensmiddelen"),
    ("NVWA PFAS egg measurements, 2024", "https://www.nvwa.nl/onderwerpen/voedselveiligheid/contaminanten-in-levensmiddelen/inspectieresultaten/2024/meetgegevens-pfas-in-eieren"),
    ("EFSA PFAS TWI, 2020", "https://www.efsa.europa.eu/en/news/pfas-food-efsa-assesses-risks-and-sets-tolerable-intake"),
    ("Voedingscentrum acrylamide factsheet", "https://www.voedingscentrum.nl/Assets/Uploads/voedingscentrum/Documents/Professionals/Pers/Factsheets/Factsheet%20acrylamide.pdf"),
    ("Voedingscentrum fish guidance", "https://www.voedingscentrum.nl/nl/service/vraag-en-antwoord/zwanger-en-baby/is-het-goed-om-vis-te-eten-tijdens-je-zwangerschap-.aspx"),
    ("RIVM Wheel of Five contaminants report", "https://www.rivm.nl/bibliotheek/rapporten/2017-0124.pdf"),
    ("Vitens sustainable drinking water overview", "https://www.vitens.nl/Over-Vitens/Elke-druppel-duurzaam/Rubriek-Duurzaam-drinkwaterbedrijf"),
    ("Vitens Utrecht groundwater context", "https://www.vitens.nl/over-water/projecten/utrecht"),
]

MCP_NOTES = [
    "PFAS monitoring contexts in the MCP explicitly include food-wide PFAS, fish and seafood, eggs, and milk and dairy.",
    "Mercury review in the MCP explicitly keeps large predatory fish visible.",
    "Cadmium support highlights breads, potatoes, leafy vegetables, and bivalve molluscs.",
    "Inorganic arsenic support explicitly highlights rice, rice cakes, rice drinks, and rice-based infant foods.",
    "Acrylamide support explicitly includes fried potato products and coffee products.",
    "BPA support explicitly includes canned foods and beverage-contact contexts.",
]


def score_row(row: dict[str, float | str]) -> float:
    return round(sum(float(row[key]) for key in CONTAMINANTS), 2)


def bucket(score: float) -> str:
    if score <= 1.0:
        return "Very low"
    if score <= 2.2:
        return "Low"
    if score <= 4.0:
        return "Moderate"
    if score <= 6.0:
        return "Elevated"
    return "High"


def top_issues(row: dict[str, float | str]) -> str:
    pairs = [(label, float(row[key])) for key, label in zip(CONTAMINANTS, CONTAMINANT_LABELS)]
    pairs = [pair for pair in sorted(pairs, key=lambda item: item[1], reverse=True) if pair[1] > 0.4]
    return ", ".join(label for label, _ in pairs[:3]) or "No standout contaminant lane"


def generate_figures() -> None:
    names = [row["food"] for row in FOOD_ROWS]
    matrix = np.array([[float(row[c]) for c in CONTAMINANTS] for row in FOOD_ROWS])
    total_scores = [score_row(row) for row in FOOD_ROWS]

    plt.style.use("seaborn-v0_8-whitegrid")

    fig, ax = plt.subplots(figsize=(9.5, 8.5))
    im = ax.imshow(matrix, cmap="YlOrRd", vmin=0, vmax=3, aspect="auto")
    ax.set_xticks(range(len(CONTAMINANT_LABELS)))
    ax.set_xticklabels(CONTAMINANT_LABELS, rotation=30, ha="right")
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(["\n".join(wrap(name, 18)) for name in names], fontsize=8)
    ax.set_title("Contaminant concern matrix for common food sources\nHeuristic score: 0 low to 3 high", fontsize=13, pad=12)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Concern score", rotation=90)
    fig.tight_layout()
    fig.savefig(HEATMAP_PATH, dpi=180, bbox_inches="tight")
    plt.close(fig)

    ranked = sorted(zip(names, total_scores), key=lambda item: item[1])
    fig, ax = plt.subplots(figsize=(9.5, 7.0))
    ax.barh(range(len(ranked)), [score for _, score in ranked], color="#2f6b4f")
    ax.set_yticks(range(len(ranked)))
    ax.set_yticklabels(["\n".join(wrap(name, 22)) for name, _ in ranked], fontsize=8)
    ax.set_xlabel("Total concern score")
    ax.set_title("Overall contaminant concern by food source\nLower is cleaner in this review frame", fontsize=13, pad=12)
    ax.set_xlim(0, 6.7)
    fig.tight_layout()
    fig.savefig(BAR_PATH, dpi=180, bbox_inches="tight")
    plt.close(fig)


def make_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TitleCenter",
            parent=styles["Title"],
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#173b2d"),
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodySmall",
            parent=styles["BodyText"],
            fontSize=9.2,
            leading=12,
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Section",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#173b2d"),
            fontSize=14,
            leading=18,
            spaceBefore=8,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Callout",
            parent=styles["BodyText"],
            fontSize=10,
            leading=14,
            backColor=colors.HexColor("#eef5f1"),
            borderPadding=10,
            borderColor=colors.HexColor("#b7d2c1"),
            borderWidth=0.5,
            borderRadius=4,
            spaceAfter=8,
        )
    )
    return styles


def build_summary_table(styles):
    headers = ["Food source", "Main issue lanes", "Total score", "Rating", "Best use"]
    rows = []
    for row in sorted(FOOD_ROWS, key=score_row):
        rows.append(
            [
                Paragraph(f"<b>{row['food']}</b>", styles["BodySmall"]),
                Paragraph(top_issues(row), styles["BodySmall"]),
                Paragraph(f"{score_row(row):.1f}", styles["BodySmall"]),
                Paragraph(bucket(score_row(row)), styles["BodySmall"]),
                Paragraph(str(row["action"]), styles["BodySmall"]),
            ]
        )
    table = Table([headers] + rows, colWidths=[4.2 * cm, 4.1 * cm, 2.0 * cm, 2.2 * cm, 5.0 * cm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#173b2d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d0ddd6")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fbf8")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def build_pattern_table(styles):
    data = [
        ["Category", "Lowest-contaminant default", "What to limit or avoid"],
        ["Drinks", "Utrecht tap water, plain tea", "High canned-drink use; bottled drinks with no clear advantage"],
        ["Breakfasts", "Oatmeal, yogurt/kwark, fruit", "Frequent browned toast, sweet biscuits"],
        ["Staples", "Oats, wheat bread, potatoes, pasta", "Rice as a daily staple; rice cakes; fries and chips"],
        ["Proteins", "Beans, lentils, tofu, chicken, yogurt/kwark", "Predatory fish, shellfish, game meat, offal"],
        ["Fish lane", "At most occasional aquaculture salmon or trout", "Tuna, swordfish, shark, self-caught fish"],
        ["Eggs", "Commercial eggs in moderation", "Home-produced eggs"],
        ["Dairy", "Yogurt/kwark before cheese", "Large daily cheese portions as a default protein"],
        ["Packaged foods", "Fresh, frozen, glass, carton", "Regular canned foods or canned drinks"],
        ["Cooking", "Boil, steam, stew, light baking", "Dark frying, dark toasting, frequent chips/fried snacks"],
    ]
    table = Table(data, colWidths=[3.0 * cm, 7.0 * cm, 7.8 * cm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#275845")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d0ddd6")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fbf8")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def write_markdown() -> None:
    lines = [
        "# Cleanest and Safest Diet for Utrecht, Netherlands",
        "",
        "## Bottom line",
        "",
        "The lowest-contaminant practical pattern for Utrecht is a mostly plant-based diet built around tap water, oats, wheat bread, potatoes, pasta, beans, lentils, tofu, fruit, vegetables, and modest amounts of yogurt or kwark. If fish is kept at all, use cultured salmon or trout occasionally, not as a daily or high-volume staple.",
        "",
        "The clearest foods to reduce are home-produced eggs, predatory fish, self-caught fish, shellfish as a routine protein source, rice-based staples, Doritos/chips/fries, heavily browned toast, canned foods as a default, and game meat or offal.",
        "",
        "## Why this is the recommendation",
        "",
        "- Dutch RIVM says PFAS exposure in the Netherlands is already too high on average, with food contributing more than drinking water and fish as the biggest contributor.",
        "- RIVM still says tap water is safe to drink, and groundwater-based drinking water is the lower-PFAS source type compared with river water.",
        "- The MCP's own review registries flag large predatory fish for mercury, rice products for inorganic arsenic, breads/potatoes/leafy vegetables and molluscs for cadmium, fried potato products and coffee for acrylamide, and canned-food or beverage-contact contexts for BPA.",
        "- Dutch and EU monitoring shows commercial eggs and dairy are not zero-risk PFAS lanes, but they are far cleaner than Dutch home-produced eggs.",
        "",
        "## Personal diet swaps",
        "",
        "- Keep Utrecht tap water as your default drink.",
        "- Replace Doritos and chips with fruit, yogurt, soup, or simple bread-and-hummus type snacks.",
        "- Keep cheese as a flavor item, not your main protein.",
        "- If you want fish, keep it occasional and prefer aquaculture salmon or trout over tuna or predatory fish.",
        "- Use oats, potatoes, bread, and pasta more often than rice products.",
        "- Favor fresh, frozen, glass, and carton packaging over cans when practical.",
        "",
        "## Evidence base",
        "",
    ]
    for label, url in SOURCE_URLS:
        lines.append(f"- [{label}]({url})")
    lines.append("")
    lines.append("## MCP support used")
    lines.append("")
    for note in MCP_NOTES:
        lines.append(f"- {note}")
    MD_PATH.write_text("\n".join(lines))


def build_pdf() -> None:
    styles = make_styles()
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title="Cleanest and Safest Diet for Utrecht, Netherlands",
        author="OpenAI Codex",
    )
    story = []

    story.append(Paragraph("Cleanest and Safest Diet for Utrecht, Netherlands", styles["TitleCenter"]))
    story.append(
        Paragraph(
            "Contaminant-focused review using Dutch official sources and the Dietary MCP contaminant support layers. "
            "This is a pragmatic food-choice report, not a medical diagnosis or a personal biomonitoring result.",
            styles["Callout"],
        )
    )

    story.append(Paragraph("Executive Summary", styles["Section"]))
    story.append(
        Paragraph(
            "If the goal is to minimize contaminant exposure while keeping a realistic Dutch diet, the cleanest pattern is "
            "mostly plant-based and minimally packaged: Utrecht tap water, oatmeal, wheat bread that is not browned hard, "
            "potatoes and pasta instead of rice-heavy eating, lots of fruit and vegetables, beans/lentils/tofu as the main protein, "
            "and yogurt or kwark more often than cheese. Fish should be a small side lane rather than a mainstay; if you keep fish, "
            "cultured salmon or trout is the cleaner compromise. The clearest foods to cut back are Doritos/chips/fries, home-produced eggs, "
            "predatory fish, self-caught fish, shellfish as a routine protein, canned foods, and game meat or offal.",
            styles["BodyText"],
        )
    )
    story.append(Spacer(1, 0.25 * cm))
    story.append(
        Paragraph(
            "Why this conclusion: RIVM says PFAS exposure in the Netherlands is already too high on average and that fish is the biggest "
            "food contributor. NVWA monitoring shows commercial Dutch eggs and dairy are generally below legal or indicative PFAS levels, "
            "but they are not zero. RIVM also explicitly advised against eating Dutch home-produced eggs because PFAS can be high. "
            "Separate from PFAS, the MCP review packs highlight large predatory fish for mercury, rice products for inorganic arsenic, "
            "fried potato products and coffee for acrylamide, breads/potatoes/leafy vegetables and molluscs for cadmium, and canned "
            "foods or beverage-contact contexts for BPA.",
            styles["BodyText"],
        )
    )

    story.append(Spacer(1, 0.35 * cm))
    story.append(Image(str(BAR_PATH), width=17.3 * cm, height=12.4 * cm))
    story.append(Spacer(1, 0.25 * cm))
    story.append(
        Paragraph(
            "Figure 1. Overall contaminant concern by food source. This is a category-level heuristic based on Dutch and EU evidence, "
            "not a lab analysis of a specific brand or batch.",
            styles["BodySmall"],
        )
    )

    story.append(Paragraph("How the review was built", styles["Section"]))
    story.append(
        Paragraph(
            "The review combines two inputs: official Dutch and EU food-safety evidence, and the Dietary MCP's supported contaminant "
            "families. The MCP does not provide a personal exposure model for every retail product. Instead, it provides governed "
            "review contexts for PFAS, mercury, cadmium, lead, inorganic arsenic, acrylamide, and BPA-related food-contact lanes. "
            "I used those MCP food-attention lanes to rank common food sources for a Utrecht resident and then overlaid Dutch official "
            "context where available.",
            styles["BodyText"],
        )
    )
    for note in MCP_NOTES:
        story.append(Paragraph(f"- {note}", styles["BodySmall"]))

    story.append(Paragraph("Comparison table", styles["Section"]))
    story.append(build_summary_table(styles))

    story.append(PageBreak())
    story.append(Paragraph("Concern matrix", styles["Section"]))
    story.append(Image(str(HEATMAP_PATH), width=17.4 * cm, height=15.5 * cm))
    story.append(Spacer(1, 0.15 * cm))
    story.append(
        Paragraph(
            "Figure 2. Heatmap of contaminant concern lanes. The darkest blocks show where the food source is a clear attention item in "
            "Dutch guidance or the MCP support data.",
            styles["BodySmall"],
        )
    )

    story.append(Paragraph("What the cleanest practical diet looks like", styles["Section"]))
    story.append(build_pattern_table(styles))
    story.append(Spacer(1, 0.2 * cm))
    story.append(
        Paragraph(
            "<b>Best day-to-day pattern.</b> Drink tap water and tea. Use oatmeal or yogurt plus fruit for breakfast. Build lunch around "
            "wheat bread, hummus, chicken, cottage cheese, or tofu spreads, with fruit or raw vegetables. Build dinners around potatoes, "
            "pasta, or bread plus beans/lentils/tofu/chicken and a lot of vegetables. Keep cheese as a topping or side, not a core protein. "
            "If you still want fish, make it occasional and choose aquaculture salmon or trout rather than tuna, eel, swordfish, or self-caught fish.",
            styles["BodyText"],
        )
    )
    story.append(Spacer(1, 0.15 * cm))
    story.append(
        Paragraph(
            "<b>Fastest risk reductions.</b> Cut Doritos/chips to near-zero. Avoid home-produced eggs. Do not make rice or rice cakes a daily habit. "
            "Choose glass/carton/fresh over cans when practical. Keep toast and potatoes gold-yellow, not dark. Alternate coffee with water and tea.",
            styles["BodyText"],
        )
    )

    story.append(Paragraph("Implications for a Utrecht resident", styles["Section"]))
    story.append(
        Paragraph(
            "For Utrecht specifically, tap water remains the default recommendation. Vitens serves Utrecht and says its drinking water comes mostly "
            "from groundwater sources, while RIVM says groundwater-based drinking water is the lower-PFAS source type compared with river-water-based "
            "drinking water. RIVM still considers Dutch tap water safe to drink, so the cleanest contaminant strategy is not switching to bottled water. "
            "It is changing the food pattern: less fish overall, much less fried snack food, less canned food, fewer rice-heavy habits, and no home eggs.",
            styles["BodyText"],
        )
    )

    story.append(Paragraph("References", styles["Section"]))
    for label, url in SOURCE_URLS:
        story.append(Paragraph(f"- <a href='{url}' color='blue'>{label}</a>", styles["BodySmall"]))

    doc.build(story)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    generate_figures()
    write_markdown()
    build_pdf()
    print(PDF_PATH)
    print(MD_PATH)


if __name__ == "__main__":
    main()
