import { createHmac } from "node:crypto";
import { handleUpload, type HandleUploadBody } from "@vercel/blob/client";
import { NextRequest, NextResponse } from "next/server";

const ALLOWED_TYPES = [
  "image/jpeg", "image/png", "image/webp", "image/gif", "image/avif",
  "video/mp4", "video/webm", "audio/mpeg", "audio/mp4", "audio/ogg", "audio/wav",
  "application/pdf",
];

export async function POST(request: NextRequest) {
  try {
    const body = await request.json() as HandleUploadBody;
    if (body.type === "blob.generate-client-token") {
      const expected = createHmac("sha256", process.env.AUTH_SECRET!).update("crm-session").digest("hex");
      if (request.cookies.get("crm_session")?.value !== expected) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
      }
    }
    const response = await handleUpload({
      body,
      request,
      onBeforeGenerateToken: async (pathname) => {
        if (!/^articles\/[a-zA-Z0-9._-]+$/.test(pathname)) throw new Error("Invalid upload path.");
        return {
          allowedContentTypes: ALLOWED_TYPES,
          maximumSizeInBytes: 100 * 1024 * 1024,
          addRandomSuffix: true,
        };
      },
      onUploadCompleted: async () => {},
    });
    return NextResponse.json(response);
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : "Upload failed." }, { status: 400 });
  }
}
