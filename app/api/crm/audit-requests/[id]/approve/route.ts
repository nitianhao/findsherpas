import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { updateAuditRequestStatus, getAuditRequestById } from "@/lib/crm/queries/audit-requests";

export async function POST(
  _req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const cookieStore = await cookies();
  const auth = cookieStore.get("crm-auth");
  if (!auth) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { id } = await params;
  
  const request = await getAuditRequestById(id);
  if (!request) {
    return NextResponse.json({ error: "Request not found" }, { status: 404 });
  }

  if (request.status !== "ready_for_review") {
    return NextResponse.json(
      { error: "Request is not ready for review" },
      { status: 400 }
    );
  }

  await updateAuditRequestStatus(id, "approved");

  return NextResponse.json({ ok: true });
}
