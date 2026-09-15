import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { POST } from "../app/api/contact/route";

const { send } = vi.hoisted(() => ({ send: vi.fn() }));
vi.mock("resend", () => ({
  Resend: class {
    emails = { send };
  },
}));

const enquiry = {
  name: "Test visitor",
  email: "visitor@example.test",
  company: "Test store",
  message: "Search relevance enquiry.",
};
const request = (body: unknown) =>
  new Request("http://localhost/api/contact", {
    method: "POST",
    body: JSON.stringify(body),
  });

describe("contact delivery", () => {
  beforeEach(() => {
    send.mockReset();
    vi.stubEnv("RESEND_API_KEY", "test-key");
  });
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("rejects malformed and incorrectly typed payloads before sending", async () => {
    for (const body of [
      null,
      [],
      "text",
      { ...enquiry, name: 17 },
      { ...enquiry, email: "invalid" },
    ]) {
      expect((await POST(request(body))).status).toBe(400);
    }
    expect(send).not.toHaveBeenCalled();
  });

  it("rejects oversized messages and accepts the honeypot without sending", async () => {
    expect(
      (await POST(request({ ...enquiry, message: "a".repeat(10001) }))).status,
    ).toBe(400);
    expect(
      (await POST(request({ ...enquiry, website: "bot-filled" }))).status,
    ).toBe(200);
    expect(send).not.toHaveBeenCalled();
  });

  it("does not claim delivery when the provider is unconfigured", async () => {
    vi.stubEnv("RESEND_API_KEY", "");
    const response = await POST(request(enquiry));
    expect(response.status).toBe(503);
    expect((await response.json()).error).toContain(
      "email michal@findsherpas.com",
    );
    expect(send).not.toHaveBeenCalled();
  });

  it("reports provider failure without leaking provider details", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    send.mockResolvedValue({
      data: null,
      error: { message: "Private provider detail" },
    });
    const response = await POST(request(enquiry));
    expect(response.status).toBe(502);
    expect((await response.json()).error).not.toContain(
      "Private provider detail",
    );
  });

  it("returns success only after the provider accepts the email", async () => {
    send.mockResolvedValue({ data: { id: "test-email-id" }, error: null });
    const response = await POST(request(enquiry));
    expect(response.status).toBe(200);
    expect(await response.json()).toMatchObject({
      ok: true,
      delivery: "email",
      id: "test-email-id",
    });
    expect(send).toHaveBeenCalledWith(
      expect.objectContaining({
        replyTo: enquiry.email,
        text: expect.stringContaining(enquiry.message),
      }),
    );
  });
});
