import { NextRequest, NextResponse } from "next/server";
import { resetPassword } from "@/lib/server/password-reset";

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => null);
  const token = body?.token;
  const password = body?.password;

  if (typeof token !== "string" || typeof password !== "string") {
    return NextResponse.json(
      { message: "Missing token or password." },
      { status: 400 }
    );
  }

  const result = await resetPassword(token, password);

  if (!result.ok) {
    return NextResponse.json({ message: result.message }, { status: 400 });
  }

  return NextResponse.json({ message: "Your password has been updated." });
}
