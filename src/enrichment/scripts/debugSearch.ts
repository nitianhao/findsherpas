import { runGoogleSearch, releaseGooglePage, isGoogleInCaptchaBackoff } from "../search/adapters/googleSearchAdapter";
import { runBingSearch, releaseBingPage } from "../search/adapters/bingSearchAdapter";
import { closeBrowser } from "../browser/browserPool";

async function main() {
  const query = 'Tuckernuck CEO LinkedIn';

  console.log("=== Testing Google ===");
  console.log("CAPTCHA backoff?", isGoogleInCaptchaBackoff());
  try {
    const gResults = await runGoogleSearch(query);
    console.log(`Google returned ${gResults.length} results`);
    for (const r of gResults.slice(0, 5)) {
      console.log(`  [${r.rank}] ${r.title}`);
      console.log(`       ${r.url}`);
    }
  } catch (err: any) {
    console.error("Google error:", err.message);
  }

  console.log("\n=== Testing Bing ===");
  try {
    const bResults = await runBingSearch(query);
    console.log(`Bing returned ${bResults.length} results`);
    for (const r of bResults.slice(0, 5)) {
      console.log(`  [${r.rank}] ${r.title}`);
      console.log(`       ${r.url}`);
    }
  } catch (err: any) {
    console.error("Bing error:", err.message);
  }

  await releaseGooglePage();
  await releaseBingPage();
  await closeBrowser();
}

main().catch((e) => { console.error(e); process.exit(1); });
