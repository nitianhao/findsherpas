import * as path from "path";
import * as fs from "fs";
import { ALL_CONFIGS } from "../schema/workbookConfigs";
import { loadPrimarySheet, getHeaderRow } from "../io/workbookService";
import * as XLSX from "xlsx";
import type { WriteAction } from "../types/writeback";

const ROOT_DIR = path.resolve(__dirname, "..", "..", "..");

// ---------------------------------------------------------------------------
// Read cell from worksheet by header name and row index
// ---------------------------------------------------------------------------

function readCell(
  worksheet: XLSX.WorkSheet,
  rowIndex: number,
  columnName: string,
): string {
  const headers = getHeaderRow(worksheet);
  const colIdx = headers.indexOf(columnName);
  if (colIdx < 0) return "";
  const addr = XLSX.utils.encode_cell({ r: rowIndex, c: colIdx });
  const cell = worksheet[addr];
  return cell ? String(cell.v).trim() : "";
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

function main() {
  console.log("=== WRITEBACK VERIFICATION ===\n");

  // Load the apply report
  const reportPath = path.join(ROOT_DIR, "docs", "writeback-apply-report.json");
  if (!fs.existsSync(reportPath)) {
    console.error("FATAL: No apply report found at", reportPath);
    process.exit(1);
  }

  const report = JSON.parse(fs.readFileSync(reportPath, "utf-8"));
  const actions: WriteAction[] = report.actions;

  console.log(`Apply report loaded: ${actions.length} total actions\n`);

  // Reload workbooks fresh from disk
  const worksheetsByFile = new Map<string, XLSX.WorkSheet>();
  for (const config of ALL_CONFIGS) {
    const { worksheet } = loadPrimarySheet(config, ROOT_DIR);
    worksheetsByFile.set(config.filename, worksheet);
    console.log(`Reloaded from disk: ${config.filename}`);
  }
  console.log("");

  // Verify WRITE_CELL actions
  const writeCells = actions.filter((a: WriteAction) => a.actionType === "WRITE_CELL");
  const skipExisting = actions.filter((a: WriteAction) => a.actionType === "SKIP_EXISTING_VALUE");
  const skipNotApproved = actions.filter((a: WriteAction) => a.actionType === "SKIP_NOT_APPROVED");
  const skipBlocked = actions.filter((a: WriteAction) => a.actionType === "SKIP_BLOCKED");

  let writePass = 0;
  let writeFail = 0;
  const writeResults: Array<{
    action: WriteAction;
    actualValue: string;
    passed: boolean;
  }> = [];

  console.log(`--- Verifying ${writeCells.length} WRITE_CELL actions ---\n`);

  for (const action of writeCells) {
    const ws = worksheetsByFile.get(action.sourceFile);
    if (!ws) {
      console.error(`  FAIL: No worksheet for ${action.sourceFile}`);
      writeFail++;
      writeResults.push({ action, actualValue: "", passed: false });
      continue;
    }

    const actual = readCell(ws, action.rowIndex, action.columnName);
    const expected = action.newValue ?? "";
    const passed = actual === expected;

    if (passed) {
      writePass++;
      console.log(
        `  [PASS] ${action.companyName.padEnd(22)} ${action.columnName.padEnd(28)} => "${actual}"`,
      );
    } else {
      writeFail++;
      console.log(
        `  [FAIL] ${action.companyName.padEnd(22)} ${action.columnName.padEnd(28)} expected="${expected}" actual="${actual}"`,
      );
    }

    writeResults.push({ action, actualValue: actual, passed });
  }

  console.log(`\nWrite verification: ${writePass}/${writeCells.length} passed, ${writeFail} failed\n`);

  // Verify SKIP_EXISTING_VALUE — existing value should still be there
  let skipExistPass = 0;
  let skipExistFail = 0;
  const skipExistResults: Array<{
    action: WriteAction;
    actualValue: string;
    passed: boolean;
  }> = [];

  console.log(`--- Verifying ${skipExisting.length} SKIP_EXISTING_VALUE actions ---\n`);

  for (const action of skipExisting) {
    const ws = worksheetsByFile.get(action.sourceFile);
    if (!ws) continue;

    const actual = readCell(ws, action.rowIndex, action.columnName);
    // The old value should still be there (not overwritten with new value)
    const passed = actual === action.oldValue;

    if (passed) {
      skipExistPass++;
      console.log(
        `  [PASS] ${action.companyName.padEnd(22)} ${action.columnName.padEnd(28)} preserved="${actual}"`,
      );
    } else {
      skipExistFail++;
      console.log(
        `  [FAIL] ${action.companyName.padEnd(22)} ${action.columnName.padEnd(28)} expected="${action.oldValue}" actual="${actual}"`,
      );
    }

    skipExistResults.push({ action, actualValue: actual, passed });
  }

  if (skipExisting.length > 0) {
    console.log(`\nSkip-existing verification: ${skipExistPass}/${skipExisting.length} passed, ${skipExistFail} failed\n`);
  }

  // Verify SKIP_NOT_APPROVED — value should NOT have been written
  let skipNotApprovedPass = 0;
  let skipNotApprovedFail = 0;
  const skipNotApprovedResults: Array<{
    action: WriteAction;
    actualValue: string;
    passed: boolean;
  }> = [];

  console.log(`--- Verifying ${skipNotApproved.length} SKIP_NOT_APPROVED actions ---\n`);

  for (const action of skipNotApproved) {
    const ws = worksheetsByFile.get(action.sourceFile);
    if (!ws) continue;

    // Skip column-missing checks (no column to read)
    const headers = getHeaderRow(ws);
    if (!headers.includes(action.columnName)) {
      console.log(
        `  [SKIP] ${action.companyName.padEnd(22)} ${action.columnName.padEnd(28)} column not in worksheet`,
      );
      continue;
    }

    const actual = readCell(ws, action.rowIndex, action.columnName);
    // The new value should NOT be there; old value should remain
    const passed = actual !== action.newValue || actual === action.oldValue;

    if (passed) {
      skipNotApprovedPass++;
      console.log(
        `  [PASS] ${action.companyName.padEnd(22)} ${action.columnName.padEnd(28)} cell="${actual}" (not-approved value not written)`,
      );
    } else {
      skipNotApprovedFail++;
      console.log(
        `  [FAIL] ${action.companyName.padEnd(22)} ${action.columnName.padEnd(28)} cell="${actual}" — not-approved value was written!`,
      );
    }

    skipNotApprovedResults.push({ action, actualValue: actual, passed });
  }

  if (skipNotApproved.length > 0) {
    console.log(`\nSkip-not-approved verification: ${skipNotApprovedPass}/${skipNotApproved.length} passed, ${skipNotApprovedFail} failed\n`);
  }

  // Verify SKIP_BLOCKED — value should NOT have been written
  let skipBlockedPass = 0;
  let skipBlockedFail = 0;

  console.log(`--- Verifying ${skipBlocked.length} SKIP_BLOCKED actions ---\n`);

  for (const action of skipBlocked) {
    const ws = worksheetsByFile.get(action.sourceFile);
    if (!ws) continue;

    const headers = getHeaderRow(ws);
    if (!headers.includes(action.columnName)) continue;

    const actual = readCell(ws, action.rowIndex, action.columnName);
    const passed = actual !== action.newValue || actual === action.oldValue;

    if (passed) {
      skipBlockedPass++;
    } else {
      skipBlockedFail++;
      console.log(
        `  [FAIL] ${action.companyName.padEnd(22)} ${action.columnName.padEnd(28)} cell="${actual}" — blocked value was written!`,
      );
    }
  }

  if (skipBlocked.length > 0) {
    console.log(`Skip-blocked verification: ${skipBlockedPass}/${skipBlocked.length} passed, ${skipBlockedFail} failed\n`);
  } else {
    console.log("  (no SKIP_BLOCKED actions to verify)\n");
  }

  // Spot-check: email columns should have no weak inferred emails
  console.log("--- Spot-check: email columns for weak inferred values ---\n");
  const emailColumns = [
    "CEO Email",
    "Head of Product Email",
    "Head of Ecommerce Email",
    "Head of Growth / CMO Email",
  ];

  let emailIssues = 0;
  for (const config of ALL_CONFIGS) {
    const ws = worksheetsByFile.get(config.filename)!;
    const headers = getHeaderRow(ws);
    const range = XLSX.utils.decode_range(ws["!ref"] ?? "A1");

    for (const emailCol of emailColumns) {
      const colIdx = headers.indexOf(emailCol);
      if (colIdx < 0) continue;

      // Check if any email cell was written by our pipeline
      // (compare against writeCells to see if we wrote to any email column)
      const emailWrites = writeCells.filter(
        (a) => a.sourceFile === config.filename && a.columnName === emailCol,
      );
      if (emailWrites.length > 0) {
        emailIssues++;
        console.log(`  [FAIL] ${config.filename} — ${emailCol}: ${emailWrites.length} email writes found!`);
      }
    }
  }

  if (emailIssues === 0) {
    console.log("  [PASS] No email columns received writes (all weak emails correctly blocked)\n");
  }

  // Overall result
  const totalFails = writeFail + skipExistFail + skipNotApprovedFail + skipBlockedFail + emailIssues;
  console.log("=== OVERALL ===\n");
  if (totalFails === 0) {
    console.log("VERIFICATION PASSED — all checks clean\n");
  } else {
    console.log(`VERIFICATION FAILED — ${totalFails} issue(s) found\n`);
  }

  // Write outputs
  const docsDir = path.resolve(ROOT_DIR, "docs");
  if (!fs.existsSync(docsDir)) fs.mkdirSync(docsDir, { recursive: true });

  const verificationData = {
    timestamp: new Date().toISOString(),
    overallPassed: totalFails === 0,
    writeCells: { total: writeCells.length, passed: writePass, failed: writeFail },
    skipExisting: { total: skipExisting.length, passed: skipExistPass, failed: skipExistFail },
    skipNotApproved: { total: skipNotApproved.length, passed: skipNotApprovedPass, failed: skipNotApprovedFail },
    skipBlocked: { total: skipBlocked.length, passed: skipBlockedPass, failed: skipBlockedFail },
    emailSpotCheck: { issues: emailIssues },
    writeResults,
    skipExistResults,
    skipNotApprovedResults,
  };

  const jsonPath = path.join(docsDir, "writeback-verification.json");
  fs.writeFileSync(jsonPath, JSON.stringify(verificationData, null, 2), "utf-8");
  console.log(`JSON: ${jsonPath}`);

  const mdPath = path.join(docsDir, "writeback-verification.md");
  fs.writeFileSync(mdPath, generateVerificationMarkdown(verificationData), "utf-8");
  console.log(`Markdown: ${mdPath}`);
}

function generateVerificationMarkdown(data: any): string {
  const lines: string[] = [
    "# Writeback Verification Report",
    "",
    `Generated: ${data.timestamp.slice(0, 10)}`,
    `Overall: **${data.overallPassed ? "PASSED" : "FAILED"}**`,
    "",
    "## Results",
    "",
    "| Check | Total | Passed | Failed |",
    "|-------|-------|--------|--------|",
    `| WRITE_CELL persisted | ${data.writeCells.total} | ${data.writeCells.passed} | ${data.writeCells.failed} |`,
    `| SKIP_EXISTING preserved | ${data.skipExisting.total} | ${data.skipExisting.passed} | ${data.skipExisting.failed} |`,
    `| SKIP_NOT_APPROVED not written | ${data.skipNotApproved.total} | ${data.skipNotApproved.passed} | ${data.skipNotApproved.failed} |`,
    `| SKIP_BLOCKED not written | ${data.skipBlocked.total} | ${data.skipBlocked.passed} | ${data.skipBlocked.failed} |`,
    `| Email spot-check | -- | -- | ${data.emailSpotCheck.issues} issues |`,
    "",
    "## Persisted Writes",
    "",
    "| Company | Column | Value | Verified |",
    "|---------|--------|-------|----------|",
  ];

  for (const r of data.writeResults) {
    lines.push(
      `| ${r.action.companyName} | ${r.action.columnName} | ${r.actualValue} | ${r.passed ? "PASS" : "FAIL"} |`,
    );
  }

  if (data.skipExistResults.length > 0) {
    lines.push("", "## Preserved Existing Values", "");
    lines.push("| Company | Column | Preserved Value | Verified |");
    lines.push("|---------|--------|-----------------|----------|");
    for (const r of data.skipExistResults) {
      lines.push(
        `| ${r.action.companyName} | ${r.action.columnName} | ${r.actualValue} | ${r.passed ? "PASS" : "FAIL"} |`,
      );
    }
  }

  if (data.skipNotApprovedResults.length > 0) {
    lines.push("", "## Not-Approved Values (confirmed not written)", "");
    lines.push("| Company | Column | Cell Value | Would-Write | Verified |");
    lines.push("|---------|--------|------------|-------------|----------|");
    for (const r of data.skipNotApprovedResults) {
      lines.push(
        `| ${r.action.companyName} | ${r.action.columnName} | ${r.actualValue || "(empty)"} | ${r.action.newValue} | ${r.passed ? "PASS" : "FAIL"} |`,
      );
    }
  }

  return lines.join("\n");
}

main();
