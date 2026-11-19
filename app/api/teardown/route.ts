import { NextResponse } from "next/server";
import { adminDb, id } from "@/lib/crm/instant-db";
import { createCompany, getCompanies } from "@/lib/crm/queries/companies";
import { createContact, getContacts } from "@/lib/crm/queries/contacts";

interface TeardownRequest {
  store_url: string;
  email: string;
  name: string;
  problem_queries?: string;
}

function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function isValidUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

function extractDomain(url: string): string {
  try {
    const parsed = new URL(url);
    return parsed.hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function extractEmailDomain(email: string): string {
  const parts = email.split("@");
  return parts[1]?.toLowerCase() || "";
}

async function checkRateLimit(domain: string, emailDomain: string): Promise<{ allowed: boolean; reason?: string }> {
  const now = new Date();
  const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString();
  const oneWeekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString();

  try {
    const data = await adminDb.query({ auditRequests: {} });
    const requests = (data.auditRequests || []) as Array<{
      rate_limit_key: string;
      created_at: string;
    }>;

    // Check domain rate limit: max 2 requests per week for the same store domain
    const domainKey = `domain:${domain}`;
    const domainRequests = requests.filter(
      (r) => r.rate_limit_key === domainKey && r.created_at >= oneWeekAgo
    );
    if (domainRequests.length >= 2) {
      return { allowed: false, reason: "This store has already been requested recently. Please wait a week before requesting again." };
    }

    // Check email domain rate limit: max 5 requests per day from the same email domain
    const emailKey = `email:${emailDomain}`;
    const emailRequests = requests.filter(
      (r) => r.rate_limit_key === emailKey && r.created_at >= oneDayAgo
    );
    if (emailRequests.length >= 5) {
      return { allowed: false, reason: "Too many requests from this email domain today. Please try again tomorrow." };
    }

    return { allowed: true };
  } catch (error) {
    console.error("Rate limit check failed:", error);
    return { allowed: true };
  }
}

async function findOrCreateCompany(domain: string, storeUrl: string): Promise<string> {
  const { companies } = await getCompanies({ search: domain, limit: 1 });
  
  if (companies.length > 0) {
    return companies[0].id;
  }

  const company = await createCompany({
    name: domain,
    website: storeUrl,
    status: "prospect",
    notes: "Created from teardown request",
  });
  
  return company.id;
}

async function findOrCreateContact(
  companyId: string,
  email: string,
  name: string
): Promise<string> {
  const { contacts } = await getContacts({ search: email, limit: 1 });
  
  const existingContact = contacts.find(
    (c) => c.email?.toLowerCase() === email.toLowerCase()
  );
  
  if (existingContact) {
    return existingContact.id;
  }

  const contact = await createContact({
    company_id: companyId,
    email,
    name,
    status: "active",
    notes: "Created from teardown request",
  });
  
  return contact.id;
}

export async function POST(req: Request) {
  let body: TeardownRequest | null = null;
  
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid request body" }, { status: 400 });
  }

  if (!body || typeof body !== "object") {
    return NextResponse.json({ error: "Invalid request body" }, { status: 400 });
  }

  const storeUrl = typeof body.store_url === "string" ? body.store_url.trim() : "";
  const email = typeof body.email === "string" ? body.email.trim().toLowerCase() : "";
  const name = typeof body.name === "string" ? body.name.trim() : "";
  const problemQueries = typeof body.problem_queries === "string" ? body.problem_queries.trim() : "";

  if (!storeUrl || !email || !name) {
    return NextResponse.json(
      { error: "Store URL, email, and name are required" },
      { status: 400 }
    );
  }

  if (!isValidUrl(storeUrl)) {
    return NextResponse.json(
      { error: "Please enter a valid store URL (e.g., https://yourstore.com)" },
      { status: 400 }
    );
  }

  if (!isValidEmail(email)) {
    return NextResponse.json({ error: "Please enter a valid email address" }, { status: 400 });
  }

  if (name.length > 200 || email.length > 254 || storeUrl.length > 2000 || problemQueries.length > 2000) {
    return NextResponse.json(
      { error: "Please shorten your input and try again" },
      { status: 400 }
    );
  }

  const domain = extractDomain(storeUrl);
  const emailDomain = extractEmailDomain(email);

  const rateCheck = await checkRateLimit(domain, emailDomain);
  if (!rateCheck.allowed) {
    return NextResponse.json({ error: rateCheck.reason }, { status: 429 });
  }

  try {
    const companyId = await findOrCreateCompany(domain, storeUrl);
    const contactId = await findOrCreateContact(companyId, email, name);

    const requestId = id();
    const now = new Date().toISOString();

    await adminDb.transact([
      adminDb.tx.auditRequests[requestId].update({
        store_url: storeUrl,
        email,
        name,
        problem_queries: problemQueries || null,
        status: "new",
        rate_limit_key: `domain:${domain}`,
        created_at: now,
        updated_at: now,
      }),
      adminDb.tx.auditRequests[requestId].link({ company: companyId }),
      adminDb.tx.auditRequests[requestId].link({ contact: contactId }),
    ]);

    return NextResponse.json({ ok: true, id: requestId });
  } catch (error) {
    console.error("Failed to create teardown request:", error);
    return NextResponse.json(
      { error: "Failed to submit request. Please try again." },
      { status: 500 }
    );
  }
}
