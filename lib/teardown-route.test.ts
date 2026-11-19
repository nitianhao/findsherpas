import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock the InstantDB client
const mockTransact = vi.fn();
const mockQuery = vi.fn();

vi.mock("@/lib/crm/instant-db", () => ({
  adminDb: {
    transact: mockTransact,
    query: mockQuery,
    tx: {
      auditRequests: new Proxy({}, {
        get: (_target, id) => ({
          update: (data: Record<string, unknown>) => ["update", "auditRequests", id, data],
          link: (links: Record<string, string>) => ["link", "auditRequests", id, links],
        }),
      }),
    },
  },
  id: () => "test-request-id",
}));

// Mock the company and contact queries
vi.mock("@/lib/crm/queries/companies", () => ({
  getCompanies: vi.fn().mockResolvedValue({ companies: [] }),
  createCompany: vi.fn().mockResolvedValue({ id: "test-company-id" }),
}));

vi.mock("@/lib/crm/queries/contacts", () => ({
  getContacts: vi.fn().mockResolvedValue({ contacts: [] }),
  createContact: vi.fn().mockResolvedValue({ id: "test-contact-id" }),
}));

import { POST } from "../app/api/teardown/route";

const validRequest = {
  store_url: "https://example-store.com",
  email: "test@company.com",
  name: "Test User",
  problem_queries: "search for 'red shoes' returns nothing",
};

function request(body: unknown) {
  return new Request("http://localhost/api/teardown", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

describe("teardown request API", () => {
  beforeEach(() => {
    mockTransact.mockReset();
    mockQuery.mockReset();
    // Default: no existing requests (no rate limiting triggered)
    mockQuery.mockResolvedValue({ auditRequests: [] });
    mockTransact.mockResolvedValue({});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("rejects missing required fields", async () => {
    const cases = [
      { email: "test@co.com", name: "Test" },
      { store_url: "https://ex.com", name: "Test" },
      { store_url: "https://ex.com", email: "test@co.com" },
      {},
    ];

    for (const body of cases) {
      const response = await POST(request(body));
      expect(response.status).toBe(400);
    }
    expect(mockTransact).not.toHaveBeenCalled();
  });

  it("rejects invalid URLs", async () => {
    const response = await POST(request({
      ...validRequest,
      store_url: "not-a-url",
    }));
    expect(response.status).toBe(400);
    const json = await response.json();
    expect(json.error).toContain("valid store URL");
  });

  it("rejects invalid emails", async () => {
    const response = await POST(request({
      ...validRequest,
      email: "not-an-email",
    }));
    expect(response.status).toBe(400);
    const json = await response.json();
    expect(json.error).toContain("valid email");
  });

  it("rejects oversized inputs", async () => {
    const response = await POST(request({
      ...validRequest,
      problem_queries: "a".repeat(2001),
    }));
    expect(response.status).toBe(400);
    const json = await response.json();
    expect(json.error).toContain("shorten");
  });

  it("creates request and links to company/contact on valid submission", async () => {
    const response = await POST(request(validRequest));
    
    expect(response.status).toBe(200);
    const json = await response.json();
    expect(json.ok).toBe(true);
    expect(json.id).toBe("test-request-id");
    
    expect(mockTransact).toHaveBeenCalledOnce();
    const txOps = mockTransact.mock.calls[0][0];
    
    // Should have update and two link operations
    expect(txOps).toHaveLength(3);
    
    // First op should be the update
    expect(txOps[0][0]).toBe("update");
    expect(txOps[0][1]).toBe("auditRequests");
    expect(txOps[0][3].store_url).toBe(validRequest.store_url);
    expect(txOps[0][3].status).toBe("new");
    
    // Should link to company and contact
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect(txOps.some((op: any[]) => op[0] === "link" && op[3]?.company)).toBe(true);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect(txOps.some((op: any[]) => op[0] === "link" && op[3]?.contact)).toBe(true);
  });

  it("enforces rate limiting by domain", async () => {
    // Simulate existing requests for the same domain
    const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000).toISOString();
    mockQuery.mockResolvedValue({
      auditRequests: [
        { rate_limit_key: "domain:example-store.com", created_at: oneHourAgo },
        { rate_limit_key: "domain:example-store.com", created_at: oneHourAgo },
      ],
    });

    const response = await POST(request(validRequest));
    
    expect(response.status).toBe(429);
    const json = await response.json();
    expect(json.error).toContain("already been requested");
  });

  it("allows requests from new domains", async () => {
    // Simulate existing requests for a different domain
    mockQuery.mockResolvedValue({
      auditRequests: [
        { rate_limit_key: "domain:other-store.com", created_at: new Date().toISOString() },
      ],
    });

    const response = await POST(request(validRequest));
    expect(response.status).toBe(200);
  });
});
