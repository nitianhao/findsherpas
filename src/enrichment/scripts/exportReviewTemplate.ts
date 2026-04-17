import * as path from "path";
import * as fs from "fs";
import * as crypto from "crypto";
import Papa from "papaparse";

const ROOT_DIR = path.resolve(__dirname, "..", "..", "..");

// ---------------------------------------------------------------------------
// Generate deterministic review ID
// ---------------------------------------------------------------------------

function makeReviewId(
  sourceFile: string,
  rowIndex: string,
  role: string,
  bucket: string,
  candidateName: string,
): string {
  const raw = `${sourceFile}|${rowIndex}|${role}|${bucket}|${candidateName}`;
  return crypto.createHash("md5").update(raw).digest("hex").slice(0, 12);
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

function main() {
  const inputPath = path.join(ROOT_DIR, "docs", "review-queue.csv");
  if (!fs.existsSync(inputPath)) {
    console.error("FATAL: review-queue.csv not found at", inputPath);
    process.exit(1);
  }

  const raw = fs.readFileSync(inputPath, "utf-8");
  const parsed = Papa.parse(raw, {
    header: true,
    skipEmptyLines: true,
    transformHeader: (h) => h.trim(),
  });

  const rows = parsed.data as Record<string, string>[];
  console.log(`Loaded ${rows.length} review items from review-queue.csv\n`);

  // Build output rows with reviewId, humanDecision, humanNotes columns
  const outputRows: Record<string, string>[] = [];

  for (const row of rows) {
    const reviewId = makeReviewId(
      row.workbook ?? "",
      row.rowIndex ?? "",
      row.role ?? "",
      row.bucket ?? "",
      row.candidateName ?? "",
    );

    outputRows.push({
      reviewId,
      ...row,
      humanDecision: "",
      humanNotes: "",
    });
  }

  // Generate CSV
  const csv = Papa.unparse(outputRows);
  const outputPath = path.join(ROOT_DIR, "docs", "review-queue-for-human-review.csv");
  fs.writeFileSync(outputPath, csv, "utf-8");

  console.log(`Created: ${outputPath}`);
  console.log(`Rows: ${outputRows.length}`);
  console.log("");
  console.log("=== HOW TO FILL IN THE REVIEW CSV ===");
  console.log("");
  console.log("1. Open docs/review-queue-for-human-review.csv in Excel or Google Sheets");
  console.log("2. For each row, fill in the 'humanDecision' column with one of:");
  console.log("");
  console.log("   APPROVE_CANDIDATE         - Approve name + LinkedIn + email (if email bucket)");
  console.log("   APPROVE_ROLE_ONLY         - Approve name only");
  console.log("   APPROVE_ROLE_AND_LINKEDIN - Approve name + LinkedIn");
  console.log("   APPROVE_EMAIL_ONLY        - Approve email only (for email-related items)");
  console.log("   KEEP_EXISTING             - Keep current workbook value, skip candidate");
  console.log("   REJECT_CANDIDATE          - Reject this candidate entirely");
  console.log("   NEEDS_MORE_RESEARCH       - Flag for later investigation");
  console.log("   SKIP                      - No action (same as leaving blank)");
  console.log("");
  console.log("3. Optionally add notes in the 'humanNotes' column");
  console.log("4. Save the file");
  console.log("5. Run: npm run enrichment:review:process");
}

main();
