import * as XLSX from "xlsx";
import * as fs from "fs";
import * as path from "path";
import type {
  WorkbookConfig,
  ProspectRowNormalized,
  ColumnMapping,
} from "../types/prospect";
import { OUTPUT_EMAIL_COLUMNS } from "../schema/workbookConfigs";

// ---------------------------------------------------------------------------
// Backup
// ---------------------------------------------------------------------------

/**
 * Creates a timestamped backup copy of the file if no backup exists for this
 * exact second. Returns the backup path, or null if a backup already existed.
 */
export function createBackup(filePath: string): string | null {
  const dir = path.dirname(filePath);
  const ext = path.extname(filePath);
  const base = path.basename(filePath, ext);
  const ts = new Date()
    .toISOString()
    .replace(/[-:T]/g, "")
    .slice(0, 14)
    .replace(/^(\d{8})(\d{6})/, "$1-$2");
  const backupName = `${base}.backup-${ts}${ext}`;
  const backupPath = path.join(dir, backupName);

  if (fs.existsSync(backupPath)) return null;

  fs.copyFileSync(filePath, backupPath);
  return backupPath;
}

// ---------------------------------------------------------------------------
// Load
// ---------------------------------------------------------------------------

export function loadWorkbook(filePath: string): XLSX.WorkBook {
  return XLSX.readFile(filePath, { cellStyles: true });
}

export function loadPrimarySheet(
  config: WorkbookConfig,
  rootDir: string,
): { workbook: XLSX.WorkBook; worksheet: XLSX.WorkSheet; filePath: string } {
  const filePath = path.resolve(rootDir, config.filename);
  if (!fs.existsSync(filePath)) {
    throw new Error(`Workbook not found: ${filePath}`);
  }
  const workbook = loadWorkbook(filePath);
  const worksheet = workbook.Sheets[config.primarySheet];
  if (!worksheet) {
    throw new Error(
      `Sheet "${config.primarySheet}" not found in ${config.filename}`,
    );
  }
  return { workbook, worksheet, filePath };
}

// ---------------------------------------------------------------------------
// Headers
// ---------------------------------------------------------------------------

export function getHeaderRow(worksheet: XLSX.WorkSheet): string[] {
  const range = XLSX.utils.decode_range(worksheet["!ref"] ?? "A1");
  const headers: string[] = [];
  for (let c = range.s.c; c <= range.e.c; c++) {
    const addr = XLSX.utils.encode_cell({ r: 0, c });
    const cell = worksheet[addr];
    headers.push(cell ? String(cell.v).trim() : "");
  }
  return headers;
}

/**
 * Adds missing output columns to the end of the header row.
 * Returns the list of columns that were actually added.
 */
export function ensureOutputColumns(
  worksheet: XLSX.WorkSheet,
  requiredColumns: readonly string[] = OUTPUT_EMAIL_COLUMNS,
): string[] {
  const headers = getHeaderRow(worksheet);
  const added: string[] = [];
  const range = XLSX.utils.decode_range(worksheet["!ref"] ?? "A1");

  for (const col of requiredColumns) {
    if (!headers.includes(col)) {
      const newCol = range.e.c + 1 + added.length;
      const addr = XLSX.utils.encode_cell({ r: 0, c: newCol });
      worksheet[addr] = { t: "s", v: col };
      added.push(col);
    }
  }

  if (added.length > 0) {
    range.e.c += added.length;
    worksheet["!ref"] = XLSX.utils.encode_range(range);
  }

  return added;
}

// ---------------------------------------------------------------------------
// Read normalized rows
// ---------------------------------------------------------------------------

function cellStr(
  worksheet: XLSX.WorkSheet,
  row: number,
  col: number,
): string {
  const addr = XLSX.utils.encode_cell({ r: row, c: col });
  const cell = worksheet[addr];
  if (!cell) return "";
  return String(cell.v).trim();
}

export function readNormalizedRows(
  config: WorkbookConfig,
  rootDir: string,
): ProspectRowNormalized[] {
  const { worksheet, filePath } = loadPrimarySheet(config, rootDir);
  const headers = getHeaderRow(worksheet);
  const range = XLSX.utils.decode_range(worksheet["!ref"] ?? "A1");
  const rows: ProspectRowNormalized[] = [];

  const colIndex = (name: string | undefined): number => {
    if (!name) return -1;
    return headers.indexOf(name);
  };

  const cm: ColumnMapping = config.columns;

  for (let r = range.s.r + 1; r <= range.e.r; r++) {
    const get = (colName: string | undefined): string => {
      const idx = colIndex(colName);
      return idx >= 0 ? cellStr(worksheet, r, idx) : "";
    };

    const originalRow: Record<string, string> = {};
    for (let c = range.s.c; c <= range.e.c; c++) {
      const h = headers[c];
      if (h) originalRow[h] = cellStr(worksheet, r, c);
    }

    // Skip entirely empty rows
    const companyName = get(cm.companyName);
    if (!companyName) continue;

    rows.push({
      sourceFile: path.basename(filePath),
      sheetName: config.primarySheet,
      rowIndex: r,
      region: config.region,
      companyName,
      websiteUrl: get(cm.websiteUrl),
      country: get(cm.country) || config.defaultCountry,
      category: get(cm.category),
      estimatedRevenue: get(cm.estimatedRevenue),
      linkedinCompanyPage: get(cm.linkedinCompanyPage),
      ceoName: get(cm.ceoName),
      ceoLinkedin: get(cm.ceoLinkedin),
      ceoEmail: get(cm.ceoEmail),
      headOfProductName: get(cm.headOfProductName),
      headOfProductEmail: get(cm.headOfProductEmail),
      headOfEcommerceName: get(cm.headOfEcommerceName),
      headOfEcommerceEmail: get(cm.headOfEcommerceEmail),
      headOfGrowthName: get(cm.headOfGrowthName),
      headOfGrowthEmail: get(cm.headOfGrowthEmail),
      notes: get(cm.notes),
      originalRow,
    });
  }

  return rows;
}

// ---------------------------------------------------------------------------
// Write helpers
// ---------------------------------------------------------------------------

/**
 * Write a value into a cell identified by header name and 1-based data row.
 * Row 1 = first data row (Excel row 2).
 */
export function writeCellByHeader(
  worksheet: XLSX.WorkSheet,
  rowNumber: number,
  headerName: string,
  value: string,
): void {
  const headers = getHeaderRow(worksheet);
  const colIdx = headers.indexOf(headerName);
  if (colIdx < 0) {
    throw new Error(`Header "${headerName}" not found in worksheet`);
  }
  const addr = XLSX.utils.encode_cell({ r: rowNumber, c: colIdx });
  // Do not overwrite existing non-empty cells
  const existing = worksheet[addr];
  if (existing && String(existing.v).trim() !== "") return;

  worksheet[addr] = { t: "s", v: value };
}

export function saveWorkbookInPlace(
  workbook: XLSX.WorkBook,
  filePath: string,
): void {
  XLSX.writeFile(workbook, filePath, { cellStyles: true });
}
