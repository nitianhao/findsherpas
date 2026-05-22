const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  ImageRun, Header, Footer, AlignmentType, LevelFormat,
  ExternalHyperlink, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageBreak, PageNumber, TabStopType, TabStopPosition,
} = require("docx");

const PROJECT_ROOT = path.resolve(__dirname, "..", "..");

// ============================================================
// DATA
// ============================================================

const COLORS = {
  primary: "009ba3",
  primaryFg: "fafafa",
  fg: "0a0a0a",
  muted: "737373",
  border: "e5e5e5",
  accent: "dcf8fa",
  secondary: "f5f5f5",
  critical: "e40014",
  moderate: "fcbb00",
  minor: "009588",
  pass: "009ba3",
  white: "FFFFFF",
};

const SEV_BG = {
  Critical: "fef2f2",
  Moderate: "fefce8",
  Minor: "f0fdf4",
  Pass: "dcf8fa",
};

const SEV_COLOR = {
  Critical: COLORS.critical,
  Moderate: "b38600",
  Minor: COLORS.minor,
  Pass: COLORS.pass,
};

// Page dimensions (US Letter)
const PAGE_W = 12240;
const PAGE_H = 15840;
const MARGIN = 1440;
const CONTENT_W = PAGE_W - 2 * MARGIN; // 9360

// ============================================================
// Scorecard data
// ============================================================
const scorecard = [
  { status: "Critical", capability: "Product Discovery", summary: "1 of 4 queries failed critically. Product Discovery is not functional." },
  { status: "Critical", capability: "Typo Tolerance", summary: "13 of 15 queries failed critically. Typo Tolerance is not functional." },
  { status: "Critical", capability: "Language Understanding", summary: "3 of 4 queries failed critically. Language Understanding is not functional." },
  { status: "Critical", capability: "Shopping Context", summary: "10 of 10 queries failed critically. Shopping Context is not functional." },
  { status: "Moderate", capability: "Brand & Model Search", summary: "2 of 4 queries showed issues. Brand & Model Search needs improvement." },
  { status: "Minor", capability: "Filters & Constraints", summary: "Minor issues detected in 1 of 3 queries. Filters & Constraints is mostly functional." },
];

// Severity distribution
const sevDist = [
  { severity: "Critical", count: "8" },
  { severity: "Moderate", count: "13" },
  { severity: "Minor", count: "9" },
  { severity: "Pass", count: "10" },
];

const failureModes = [
  { mode: "Poor ranking", count: "28" },
  { mode: "No fuzzy matching", count: "1" },
  { mode: "Constraint dropped", count: "1" },
];

// Roadmap
const roadmap = [
  { num: 1, title: "Fix relevance score ranking across all search types", desc: "This addresses the core ranking problem affecting Product Discovery, Typo Tolerance, Language Understanding, and Shopping Context.", impact: "Critical", effort: "Quick Win" },
  { num: 2, title: "Implement fuzzy matching for pharmaceutical brand names", desc: "This fixes the complete failure to find Voltaren products when customers search \"Voltren\" and similar typos.", impact: "Critical", effort: "Medium Effort" },
  { num: 3, title: "Add German compound word processing", desc: "This improves Typo Tolerance for merged words like \"k\u00f6rperlotion\", \"feuchtigkeitscreme\", and \"schmerzgel\".", impact: "Critical", effort: "Medium Effort" },
  { num: 4, title: "Configure price constraint recognition for special characters", desc: "This fixes the Shopping Context issue where \"$15\" in \"omega-3 $15\" is ignored completely, showing expensive products.", impact: "Moderate", effort: "Quick Win" },
  { num: 5, title: "Boost exact product type matches over brand matches", desc: "This addresses Product Discovery cases where customers search for specific product types (like \"k\u00f6rperpflege\") but get unrelated results.", impact: "Moderate", effort: "Quick Win" },
  { num: 6, title: "Improve partial query handling for brand searches", desc: "This fixes Brand & Model Search issues where partial queries like \"physio\" and \"coll\" return relevant but poorly ranked results.", impact: "Moderate", effort: "Medium Effort" },
  { num: 7, title: "Add seasonal keyword boosting", desc: "This enhances Shopping Context by prioritizing products with seasonal terms like \"Winter\" when customers use them.", impact: "Minor", effort: "Quick Win" },
];

// Benchmarks
const benchmarks = [
  { metric: "Relevant result in top 3", siteValue: "38%", industryAvg: "80%+", source: "Baymard Institute" },
  { metric: "Average best result position", siteValue: "#6", industryAvg: "#1\u20132", source: "Industry best practice" },
  { metric: "Irrelevant #1 result", siteValue: "8%", industryAvg: "<10%", source: "Industry best practice" },
];

// What's working
const whatsWorking = [
  "Filters & Constraints is mostly functional \u2014 minor issues only. Minor issues detected in 1 of 3 queries.",
  "Retrieval is working \u2014 relevant results were found in 23 of 40 queries. The primary issue is ranking, not finding: the right products appear, just not in the right order.",
  "Close to correct on 5 queries (\"Voltren\", \"weihnachtsgeschenke familie\", \"baby hautpflege sensitiv\"): the best result was within the top 3 positions.",
];

// Methodology steps
const methodSteps = [
  { num: "1", title: "Site Discovery", desc: "Automated analysis of your site\u2019s structure, navigation categories, brands, and featured products to understand what you sell and how your search works." },
  { num: "2", title: "Test Design", desc: "Site-type-aware selection from a library of 26 test categories. Categories are chosen based on your site\u2019s commerce model and product catalog." },
  { num: "3", title: "Query Generation", desc: "AI-generated realistic customer queries grounded in the actual products, brands, and categories found on your site \u2014 not generic." },
  { num: "4", title: "Result Collection", desc: "Automated search execution collecting the top results for each test query exactly as your customers would see them." },
  { num: "5", title: "Relevance Scoring", desc: "Each result scored on a 0.0\u20131.0 scale by a specialized relevance model, producing an objective measure of how well each result matches the query." },
  { num: "6", title: "Failure Analysis", desc: "Each query classified by failure mode (e.g., poor ranking, constraint dropped, no fuzzy matching) and severity." },
  { num: "7", title: "Report Assembly", desc: "Findings synthesized into this actionable narrative with prioritized recommendations ordered by business impact." },
];

// Deep dives
const deepDives = JSON.parse(fs.readFileSync("/tmp/shop_apotheke_deep_dives.json", "utf-8"));

// Appendix
const appendix = [
  ["1","coll","Partial query","Critical","#15","Poor ranking"],
  ["2","k\u00f6rper pflege","Locale variation","Critical","#13","Poor ranking"],
  ["3","gesundheit","Broad category","Critical","#11","Poor ranking"],
  ["4","physio","Partial query","Critical","#11","Poor ranking"],
  ["5","medikamente","Synonym","Critical","#11","Poor ranking"],
  ["6","arzneimittel","Plural / singular","Critical","#11","Poor ranking"],
  ["7","erk\u00e4ltung winter","Seasonal / occasion","Critical","#10","Poor ranking"],
  ["8","Voltren","Typo","Critical","#1","No fuzzy matching"],
  ["9","anti-ageing","Locale variation","Moderate","#15","Poor ranking"],
  ["10","schmerzgel","Merged words","Moderate","#10","Poor ranking"],
  ["11","k\u00f6rper lotion","Split word","Moderate","#10","Poor ranking"],
  ["12","anti aging","Split word","Moderate","#10","Poor ranking"],
  ["13","bepan","Partial query","Moderate","#9","Poor ranking"],
  ["14","trockene haut pflege","Use case","Moderate","#9","Poor ranking"],
  ["15","Weleda k\u00f6rperpflege","Brand search","Moderate","#9","Poor ranking"],
  ["16","feuchtigkeitscreme","Merged words","Moderate","#8","Poor ranking"],
  ["17","haut pflege","Split word","Moderate","#7","Poor ranking"],
  ["18","vitamin c 1000mg @ shop apotheke","Special character","Moderate","#7","Poor ranking"],
  ["19","sport regeneration creme","Use case","Moderate","#7","Poor ranking"],
  ["20","kontaktlinse","Plural / singular","Moderate","#6","Poor ranking"],
  ["21","omega-3 $15","Special character","Moderate","#5","Constraint dropped"],
  ["22","Asprin","Typo","Minor","#6","Poor ranking"],
  ["23","hautcreme","Synonym","Minor","#6","Poor ranking"],
  ["24","babypflege","Synonym","Minor","#5","Poor ranking"],
  ["25","k\u00f6rperlotion","Merged words","Minor","#4","Poor ranking"],
  ["26","eucerin k\u00f6rpercreme trockene haut","Multi-attribute","Minor","#4","Poor ranking"],
  ["27","weihnachtsgeschenke familie","Seasonal / occasion","Minor","#3","Poor ranking"],
  ["28","geschenk f\u00fcr mama k\u00f6rperpflege","Use case","Minor","#3","Poor ranking"],
  ["29","baby hautpflege sensitiv","Use case","Minor","#2","Poor ranking"],
  ["30","faq","Abbreviation","Minor","#2","Poor ranking"],
  ["31","Eucerin","Brand search","Pass","#1","\u2014"],
  ["32","beauty","Broad category","Pass","#1","\u2014"],
  ["33","schmerzmittel","Synonym","Pass","#1","\u2014"],
  ["34","ibu","Abbreviation","Pass","#1","\u2014"],
  ["35","weleda bio k\u00f6rperlotion","Multi-attribute","Pass","#1","\u2014"],
  ["36","Bepanthol DERMA Feuchtigkeitsspendende K\u00f6rperlotion","Direct match","Pass","#1","\u2014"],
  ["37","PHYSIOGEL Daily Moisture Therapy Intensiv Creme","Direct match","Pass","#1","\u2014"],
  ["38","Bepanthen","Typo","Pass","#1","\u2014"],
  ["39","Eucrin","Typo","Pass","#1","\u2014"],
  ["40","ratiopharm ibuprofen 400mg","Multi-attribute","Pass","#1","\u2014"],
];

// ============================================================
// HELPERS
// ============================================================

const noBorder = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };
const thinBorder = { style: BorderStyle.SINGLE, size: 1, color: COLORS.border };
const thinBorders = { top: thinBorder, bottom: thinBorder, left: thinBorder, right: thinBorder };

function sectionLabel(text) {
  return new Paragraph({
    spacing: { before: 120, after: 60 },
    children: [new TextRun({ text: text.toUpperCase(), font: "Arial", size: 14, bold: true, color: COLORS.primary, characterSpacing: 60 })],
  });
}

function heading2(text) {
  return new Paragraph({
    spacing: { before: 80, after: 200 },
    children: [new TextRun({ text, font: "Arial", size: 30, bold: true, color: COLORS.fg })],
  });
}

function heading3(text) {
  return new Paragraph({
    spacing: { before: 240, after: 120 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 3, color: COLORS.primary, space: 4 } },
    children: [new TextRun({ text, font: "Arial", size: 24, bold: true, color: COLORS.fg })],
  });
}

function bodyText(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 140 },
    children: [new TextRun({ text, font: "Arial", size: 20, color: opts.color || COLORS.fg, ...(opts.bold ? { bold: true } : {}), ...(opts.italics ? { italics: true } : {}) })],
  });
}

function emptyLine() {
  return new Paragraph({ spacing: { after: 0 }, children: [] });
}

function sevBadgeRun(severity) {
  return new TextRun({
    text: ` ${severity} `,
    font: "Arial",
    size: 16,
    bold: true,
    color: SEV_COLOR[severity] || COLORS.fg,
  });
}

function truncate(str, len) {
  if (!str) return "";
  return str.length > len ? str.substring(0, len - 1) + "\u2026" : str;
}

// ============================================================
// BUILD DOCUMENT
// ============================================================

async function main() {
  const children = [];

  // ---- COVER PAGE ----
  children.push(new Paragraph({ spacing: { before: 600 }, children: [] }));
  children.push(new Paragraph({
    spacing: { after: 100 },
    children: [new TextRun({ text: "Michal Pekarcik", font: "Arial", size: 20, bold: true, color: COLORS.fg })],
  }));

  children.push(new Paragraph({ spacing: { before: 400, after: 80 }, children: [] }));
  children.push(new Paragraph({
    spacing: { after: 120 },
    children: [new TextRun({ text: "Search Audit Report", font: "Arial", size: 48, bold: true, color: COLORS.fg })],
  }));
  children.push(new Paragraph({
    spacing: { after: 60 },
    children: [new TextRun({ text: "Shop Apotheke", font: "Arial", size: 32, color: COLORS.primary, bold: true })],
  }));
  children.push(new Paragraph({
    spacing: { after: 200 },
    children: [
      new TextRun({ text: "April 10, 2026  |  ", font: "Arial", size: 18, color: COLORS.muted }),
      new ExternalHyperlink({
        children: [new TextRun({ text: "LinkedIn", font: "Arial", size: 18, color: COLORS.primary, underline: {} })],
        link: "https://www.linkedin.com/in/michalpekarcik/",
      }),
    ],
  }));

  // Screenshot
  try {
    const imgData = fs.readFileSync(path.join(PROJECT_ROOT, "reports", "redcare screenshot.jpg"));
    children.push(new Paragraph({
      spacing: { after: 200 },
      children: [new ImageRun({
        type: "jpg",
        data: imgData,
        transformation: { width: 600, height: 338 },
        altText: { title: "Shop Apotheke", description: "Screenshot of Shop Apotheke website", name: "screenshot" },
      })],
    }));
  } catch (e) {
    // skip screenshot if not found
  }

  children.push(new Paragraph({ children: [new PageBreak()] }));

  // ---- EXECUTIVE SUMMARY ----
  children.push(sectionLabel("Executive Summary"));
  children.push(heading2("Shop Apotheke\u2019s search performed well on 0 of 6 capabilities."));
  children.push(bodyText("We tested 40 realistic customer queries across 6 core search capabilities. No capability passed all tests."));
  children.push(bodyText("The most severe example: a customer searching \"coll\" had to scroll to position #15 to find the best matching result."));

  children.push(new Paragraph({ children: [new PageBreak()] }));

  // ---- CAPABILITY SCORECARD ----
  children.push(sectionLabel("Capability Scorecard"));
  children.push(heading2("Capabilities tested: 6"));

  // Scorecard table
  const scHeaderCells = ["Status", "Capability", "Summary"].map((h, i) => {
    const widths = [1400, 2400, 5560];
    return new TableCell({
      width: { size: widths[i], type: WidthType.DXA },
      borders: { top: noBorder, left: noBorder, right: noBorder, bottom: { style: BorderStyle.SINGLE, size: 2, color: COLORS.border } },
      margins: { top: 60, bottom: 60, left: 80, right: 80 },
      children: [new Paragraph({ children: [new TextRun({ text: h.toUpperCase(), font: "Arial", size: 14, bold: true, color: COLORS.muted, characterSpacing: 40 })] })],
    });
  });

  const scRows = [new TableRow({ children: scHeaderCells })];
  for (const sc of scorecard) {
    const sevColor = SEV_COLOR[sc.status] || COLORS.fg;
    scRows.push(new TableRow({
      children: [
        new TableCell({
          width: { size: 1400, type: WidthType.DXA },
          borders: { top: noBorder, left: noBorder, right: noBorder, bottom: { style: BorderStyle.SINGLE, size: 1, color: COLORS.border } },
          margins: { top: 80, bottom: 80, left: 80, right: 80 },
          children: [new Paragraph({ children: [new TextRun({ text: sc.status, font: "Arial", size: 18, bold: true, color: sevColor })] })],
        }),
        new TableCell({
          width: { size: 2400, type: WidthType.DXA },
          borders: { top: noBorder, left: noBorder, right: noBorder, bottom: { style: BorderStyle.SINGLE, size: 1, color: COLORS.border } },
          margins: { top: 80, bottom: 80, left: 80, right: 80 },
          children: [new Paragraph({ children: [new TextRun({ text: sc.capability, font: "Arial", size: 18, bold: true, color: COLORS.fg })] })],
        }),
        new TableCell({
          width: { size: 5560, type: WidthType.DXA },
          borders: { top: noBorder, left: noBorder, right: noBorder, bottom: { style: BorderStyle.SINGLE, size: 1, color: COLORS.border } },
          margins: { top: 80, bottom: 80, left: 80, right: 80 },
          children: [new Paragraph({ children: [new TextRun({ text: sc.summary, font: "Arial", size: 17, color: COLORS.muted })] })],
        }),
      ],
    }));
  }

  children.push(new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [1400, 2400, 5560],
    rows: scRows,
  }));

  children.push(new Paragraph({ children: [new PageBreak()] }));

  // ---- TEST RESULTS ----
  children.push(sectionLabel("Test Results"));
  children.push(heading2("40 queries tested"));

  // Severity distribution table
  const sevHeader = new TableRow({
    children: [
      new TableCell({ width: { size: 4680, type: WidthType.DXA }, borders: { ...noBorders, bottom: thinBorder }, margins: { top: 50, bottom: 50, left: 80, right: 80 }, children: [new Paragraph({ children: [new TextRun({ text: "SEVERITY", font: "Arial", size: 14, bold: true, color: COLORS.muted, characterSpacing: 40 })] })] }),
      new TableCell({ width: { size: 4680, type: WidthType.DXA }, borders: { ...noBorders, bottom: thinBorder }, margins: { top: 50, bottom: 50, left: 80, right: 80 }, children: [new Paragraph({ children: [new TextRun({ text: "QUERIES", font: "Arial", size: 14, bold: true, color: COLORS.muted, characterSpacing: 40 })] })] }),
    ],
  });

  const sevRows = [sevHeader];
  for (const s of sevDist) {
    const bg = s.severity === "Critical" ? "fef2f2" : s.severity === "Moderate" ? "fefce8" : s.severity === "Minor" ? "f0fdf4" : "dcf8fa";
    sevRows.push(new TableRow({
      children: [
        new TableCell({
          width: { size: 4680, type: WidthType.DXA },
          borders: { ...noBorders, bottom: { style: BorderStyle.SINGLE, size: 1, color: COLORS.border } },
          margins: { top: 50, bottom: 50, left: 80, right: 80 },
          shading: { fill: bg, type: ShadingType.CLEAR },
          children: [new Paragraph({ children: [new TextRun({ text: s.severity, font: "Arial", size: 18, bold: true, color: SEV_COLOR[s.severity] })] })],
        }),
        new TableCell({
          width: { size: 4680, type: WidthType.DXA },
          borders: { ...noBorders, bottom: { style: BorderStyle.SINGLE, size: 1, color: COLORS.border } },
          margins: { top: 50, bottom: 50, left: 80, right: 80 },
          shading: { fill: bg, type: ShadingType.CLEAR },
          children: [new Paragraph({ children: [new TextRun({ text: s.count, font: "Arial", size: 18, color: COLORS.fg })] })],
        }),
      ],
    }));
  }

  children.push(new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [4680, 4680],
    rows: sevRows,
  }));

  children.push(emptyLine());

  // Failure modes table
  const fmHeader = new TableRow({
    children: [
      new TableCell({ width: { size: 4680, type: WidthType.DXA }, borders: { ...noBorders, bottom: thinBorder }, margins: { top: 50, bottom: 50, left: 80, right: 80 }, children: [new Paragraph({ children: [new TextRun({ text: "FAILURE MODE", font: "Arial", size: 14, bold: true, color: COLORS.muted, characterSpacing: 40 })] })] }),
      new TableCell({ width: { size: 4680, type: WidthType.DXA }, borders: { ...noBorders, bottom: thinBorder }, margins: { top: 50, bottom: 50, left: 80, right: 80 }, children: [new Paragraph({ children: [new TextRun({ text: "QUERIES", font: "Arial", size: 14, bold: true, color: COLORS.muted, characterSpacing: 40 })] })] }),
    ],
  });
  const fmRows = [fmHeader];
  for (const fm of failureModes) {
    fmRows.push(new TableRow({
      children: [
        new TableCell({ width: { size: 4680, type: WidthType.DXA }, borders: { ...noBorders, bottom: { style: BorderStyle.SINGLE, size: 1, color: COLORS.border } }, margins: { top: 50, bottom: 50, left: 80, right: 80 }, children: [new Paragraph({ children: [new TextRun({ text: fm.mode, font: "Arial", size: 18, color: COLORS.fg })] })] }),
        new TableCell({ width: { size: 4680, type: WidthType.DXA }, borders: { ...noBorders, bottom: { style: BorderStyle.SINGLE, size: 1, color: COLORS.border } }, margins: { top: 50, bottom: 50, left: 80, right: 80 }, children: [new Paragraph({ children: [new TextRun({ text: fm.count, font: "Arial", size: 18, color: COLORS.fg })] })] }),
      ],
    }));
  }

  children.push(new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [4680, 4680],
    rows: fmRows,
  }));

  children.push(new Paragraph({ children: [new PageBreak()] }));

  // ---- PRIORITIZED ROADMAP ----
  children.push(sectionLabel("Recommendations"));
  children.push(heading2("Prioritized Roadmap"));

  for (const item of roadmap) {
    children.push(new Paragraph({
      spacing: { before: 200, after: 40 },
      children: [
        new TextRun({ text: `${item.num}. `, font: "Arial", size: 22, bold: true, color: COLORS.primary }),
        new TextRun({ text: item.title, font: "Arial", size: 22, bold: true, color: COLORS.fg }),
      ],
    }));
    children.push(new Paragraph({
      spacing: { after: 40 },
      children: [new TextRun({ text: item.desc, font: "Arial", size: 18, color: COLORS.muted })],
    }));
    children.push(new Paragraph({
      spacing: { after: 120 },
      children: [
        new TextRun({ text: `${item.impact}`, font: "Arial", size: 16, bold: true, color: item.impact === "Critical" ? COLORS.critical : item.impact === "Moderate" ? "b38600" : COLORS.minor }),
        new TextRun({ text: "  |  ", font: "Arial", size: 16, color: COLORS.muted }),
        new TextRun({ text: item.effort, font: "Arial", size: 16, bold: true, color: item.effort === "Quick Win" ? COLORS.minor : "b38600" }),
      ],
    }));
  }

  children.push(new Paragraph({ children: [new PageBreak()] }));

  // ---- BENCHMARKS ----
  children.push(sectionLabel("Industry Context"));
  children.push(heading2("How You Compare"));

  const bmHeaders = ["Metric", "Your Site", "Industry Avg", "Source"];
  const bmWidths = [2800, 1800, 1800, 2960];
  const bmHeaderRow = new TableRow({
    children: bmHeaders.map((h, i) => new TableCell({
      width: { size: bmWidths[i], type: WidthType.DXA },
      borders: { ...noBorders, bottom: { style: BorderStyle.SINGLE, size: 2, color: COLORS.border } },
      margins: { top: 60, bottom: 60, left: 80, right: 80 },
      children: [new Paragraph({ children: [new TextRun({ text: h.toUpperCase(), font: "Arial", size: 14, bold: true, color: COLORS.muted, characterSpacing: 40 })] })],
    })),
  });

  const bmDataRows = benchmarks.map(b => new TableRow({
    children: [
      new TableCell({ width: { size: 2800, type: WidthType.DXA }, borders: { ...noBorders, bottom: { style: BorderStyle.SINGLE, size: 1, color: COLORS.border } }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [new TextRun({ text: b.metric, font: "Arial", size: 18, color: COLORS.fg })] })] }),
      new TableCell({ width: { size: 1800, type: WidthType.DXA }, borders: { ...noBorders, bottom: { style: BorderStyle.SINGLE, size: 1, color: COLORS.border } }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [new TextRun({ text: b.siteValue, font: "Arial", size: 18, bold: true, color: COLORS.critical })] })] }),
      new TableCell({ width: { size: 1800, type: WidthType.DXA }, borders: { ...noBorders, bottom: { style: BorderStyle.SINGLE, size: 1, color: COLORS.border } }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [new TextRun({ text: b.industryAvg, font: "Arial", size: 18, bold: true, color: COLORS.pass })] })] }),
      new TableCell({ width: { size: 2960, type: WidthType.DXA }, borders: { ...noBorders, bottom: { style: BorderStyle.SINGLE, size: 1, color: COLORS.border } }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [new TextRun({ text: b.source, font: "Arial", size: 17, color: COLORS.muted, italics: true })] })] }),
    ],
  }));

  children.push(new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: bmWidths,
    rows: [bmHeaderRow, ...bmDataRows],
  }));

  children.push(new Paragraph({ children: [new PageBreak()] }));

  // ---- DETAILED ANALYSIS (Deep Dives) ----
  children.push(sectionLabel("Detailed Analysis"));

  for (const dd of deepDives) {
    children.push(heading3(dd.capability));
    if (dd.intro) {
      children.push(bodyText(dd.intro, { color: COLORS.muted }));
    }

    for (const ex of dd.examples) {
      // Query header
      children.push(new Paragraph({
        spacing: { before: 200, after: 40 },
        shading: { fill: COLORS.secondary, type: ShadingType.CLEAR },
        border: { top: thinBorder, bottom: thinBorder, left: thinBorder, right: thinBorder },
        children: [
          new TextRun({ text: `  "${ex.query}"`, font: "Courier New", size: 18, bold: true, color: COLORS.fg }),
        ],
      }));
      if (ex.category_info) {
        children.push(new Paragraph({
          spacing: { after: 80 },
          children: [new TextRun({ text: `  ${ex.category_info}`, font: "Arial", size: 15, color: COLORS.muted })],
        }));
      }

      // Actual vs Ideal comparison table
      if (ex.actual.length > 0 || ex.ideal.length > 0) {
        const maxRows = Math.max(ex.actual.length, ex.ideal.length);
        const compRows = [];

        // Headers
        compRows.push(new TableRow({
          children: [
            new TableCell({
              width: { size: 4680, type: WidthType.DXA },
              shading: { fill: "fef2f2", type: ShadingType.CLEAR },
              borders: thinBorders,
              margins: { top: 50, bottom: 50, left: 80, right: 80 },
              children: [new Paragraph({ children: [new TextRun({ text: "CUSTOMER SAW", font: "Arial", size: 14, bold: true, color: COLORS.critical, characterSpacing: 40 })] })],
            }),
            new TableCell({
              width: { size: 4680, type: WidthType.DXA },
              shading: { fill: "f0fdf4", type: ShadingType.CLEAR },
              borders: thinBorders,
              margins: { top: 50, bottom: 50, left: 80, right: 80 },
              children: [new Paragraph({ children: [new TextRun({ text: "SHOULD HAVE SEEN", font: "Arial", size: 14, bold: true, color: COLORS.minor, characterSpacing: 40 })] })],
            }),
          ],
        }));

        for (let i = 0; i < maxRows; i++) {
          compRows.push(new TableRow({
            children: [
              new TableCell({
                width: { size: 4680, type: WidthType.DXA },
                shading: { fill: "fef2f2", type: ShadingType.CLEAR },
                borders: thinBorders,
                margins: { top: 30, bottom: 30, left: 80, right: 80 },
                children: [new Paragraph({ children: [
                  new TextRun({ text: `#${i + 1} `, font: "Arial", size: 16, bold: true, color: COLORS.muted }),
                  new TextRun({ text: truncate(ex.actual[i] || "", 55), font: "Arial", size: 16, color: COLORS.fg }),
                ] })],
              }),
              new TableCell({
                width: { size: 4680, type: WidthType.DXA },
                shading: { fill: "f0fdf4", type: ShadingType.CLEAR },
                borders: thinBorders,
                margins: { top: 30, bottom: 30, left: 80, right: 80 },
                children: [new Paragraph({ children: [
                  new TextRun({ text: i < ex.ideal.length ? `#${i + 1} ` : "", font: "Arial", size: 16, bold: true, color: COLORS.muted }),
                  new TextRun({ text: truncate(ex.ideal[i] || "", 55), font: "Arial", size: 16, color: COLORS.fg }),
                ] })],
              }),
            ],
          }));
        }

        children.push(new Table({
          width: { size: CONTENT_W, type: WidthType.DXA },
          columnWidths: [4680, 4680],
          rows: compRows,
        }));
      }

      if (ex.displacement) {
        children.push(new Paragraph({
          spacing: { before: 40, after: 120 },
          children: [new TextRun({ text: ex.displacement, font: "Arial", size: 16, italics: true, color: COLORS.muted })],
        }));
      }
    }
  }

  children.push(new Paragraph({ children: [new PageBreak()] }));

  // ---- WHAT'S WORKING ----
  children.push(sectionLabel("Positive Findings"));
  children.push(heading2("What\u2019s Working"));

  for (const item of whatsWorking) {
    children.push(new Paragraph({
      spacing: { after: 120 },
      indent: { left: 360 },
      children: [
        new TextRun({ text: "\u2022  ", font: "Arial", size: 20, color: COLORS.pass }),
        new TextRun({ text: item, font: "Arial", size: 18, color: COLORS.fg }),
      ],
    }));
  }

  children.push(new Paragraph({ children: [new PageBreak()] }));

  // ---- METHODOLOGY ----
  children.push(sectionLabel("How We Did It"));
  children.push(heading2("The Audit Pipeline"));
  children.push(bodyText("This audit was conducted using a seven-phase automated search quality assessment. 40 test queries were generated and executed against your live search, then scored and analyzed for relevance."));

  for (const step of methodSteps) {
    children.push(new Paragraph({
      spacing: { before: 140, after: 40 },
      children: [
        new TextRun({ text: `${step.num}. ${step.title}`, font: "Arial", size: 20, bold: true, color: COLORS.primary }),
      ],
    }));
    children.push(new Paragraph({
      spacing: { after: 80 },
      indent: { left: 360 },
      children: [new TextRun({ text: step.desc, font: "Arial", size: 17, color: COLORS.muted })],
    }));
  }

  children.push(new Paragraph({ children: [new PageBreak()] }));

  // ---- APPENDIX ----
  children.push(sectionLabel("Full Data"));
  children.push(heading2("Appendix: Complete Test Results"));

  const appHeaders = ["#", "Query", "Category", "Severity", "Best Pos", "Failure Mode"];
  const appWidths = [500, 2800, 1500, 1200, 1000, 2360];

  const appHeaderRow = new TableRow({
    children: appHeaders.map((h, i) => new TableCell({
      width: { size: appWidths[i], type: WidthType.DXA },
      shading: { fill: COLORS.secondary, type: ShadingType.CLEAR },
      borders: thinBorders,
      margins: { top: 40, bottom: 40, left: 60, right: 60 },
      children: [new Paragraph({ children: [new TextRun({ text: h, font: "Arial", size: 13, bold: true, color: COLORS.muted })] })],
    })),
  });

  const appDataRows = appendix.map((row, idx) => {
    const bg = idx % 2 === 0 ? COLORS.white : COLORS.secondary;
    const sevText = row[3];
    return new TableRow({
      children: row.map((cell, i) => {
        const isSev = i === 3;
        return new TableCell({
          width: { size: appWidths[i], type: WidthType.DXA },
          shading: { fill: bg, type: ShadingType.CLEAR },
          borders: thinBorders,
          margins: { top: 30, bottom: 30, left: 60, right: 60 },
          children: [new Paragraph({ children: [new TextRun({
            text: truncate(cell, 40),
            font: "Arial",
            size: 14,
            bold: isSev,
            color: isSev ? (SEV_COLOR[sevText] || COLORS.fg) : COLORS.fg,
          })] })],
        });
      }),
    });
  });

  children.push(new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: appWidths,
    rows: [appHeaderRow, ...appDataRows],
  }));

  // ============================================================
  // ASSEMBLE DOCUMENT
  // ============================================================

  const doc = new Document({
    styles: {
      default: {
        document: { run: { font: "Arial", size: 20 } },
      },
    },
    sections: [{
      properties: {
        page: {
          size: { width: PAGE_W, height: PAGE_H },
          margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN },
        },
      },
      headers: {
        default: new Header({
          children: [new Paragraph({
            tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
            border: { bottom: { style: BorderStyle.SINGLE, size: 1, color: COLORS.border, space: 4 } },
            children: [
              new TextRun({ text: "Michal Pekarcik", font: "Arial", size: 16, bold: true, color: COLORS.fg }),
              new TextRun({ text: "\tSearch Audit Report", font: "Arial", size: 16, color: COLORS.muted }),
            ],
          })],
        }),
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
            children: [
              new TextRun({ text: "Shop Apotheke  |  April 2026", font: "Arial", size: 14, color: COLORS.muted }),
              new TextRun({ text: "\tPage ", font: "Arial", size: 14, color: COLORS.muted }),
              new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 14, color: COLORS.muted }),
            ],
          })],
        }),
      },
      children,
    }],
  });

  const buffer = await Packer.toBuffer(doc);
  const outPath = path.join(
    PROJECT_ROOT,
    "reports",
    "www_shop-apotheke_com",
    "www_shop-apotheke_com_20260410_100841_report.docx",
  );
  fs.writeFileSync(outPath, buffer);
  console.log("DOCX written to:", outPath);
}

main().catch(err => { console.error(err); process.exit(1); });
