import * as fs from "fs";
import * as path from "path";
import * as crypto from "crypto";
import type { CompanyDiscoveryResult } from "../types/discovery";

const CACHE_DIR = path.resolve(
  __dirname,
  "..",
  "..",
  "..",
  ".cache",
  "enrichment",
  "discovery",
);

function cacheKey(
  sourceFile: string,
  sheetName: string,
  rowIndex: number,
  websiteUrl: string,
): string {
  const domain = extractDomain(websiteUrl);
  const raw = `${sourceFile}|${sheetName}|${rowIndex}|${domain}`;
  return crypto.createHash("md5").update(raw).digest("hex");
}

function extractDomain(url: string): string {
  try {
    const parsed = new URL(
      url.startsWith("http") ? url : `https://${url}`,
    );
    return parsed.hostname.replace(/^www\./, "").toLowerCase();
  } catch {
    return url.toLowerCase();
  }
}

function ensureCacheDir() {
  if (!fs.existsSync(CACHE_DIR)) {
    fs.mkdirSync(CACHE_DIR, { recursive: true });
  }
}

export function getCachedDiscoveryResult(
  sourceFile: string,
  sheetName: string,
  rowIndex: number,
  websiteUrl: string,
): CompanyDiscoveryResult | null {
  const key = cacheKey(sourceFile, sheetName, rowIndex, websiteUrl);
  const filePath = path.join(CACHE_DIR, `${key}.json`);
  if (!fs.existsSync(filePath)) return null;
  try {
    const data = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(data) as CompanyDiscoveryResult;
  } catch {
    return null;
  }
}

export function setCachedDiscoveryResult(
  sourceFile: string,
  sheetName: string,
  rowIndex: number,
  websiteUrl: string,
  result: CompanyDiscoveryResult,
): void {
  ensureCacheDir();
  const key = cacheKey(sourceFile, sheetName, rowIndex, websiteUrl);
  const filePath = path.join(CACHE_DIR, `${key}.json`);
  fs.writeFileSync(filePath, JSON.stringify(result, null, 2), "utf-8");
}
