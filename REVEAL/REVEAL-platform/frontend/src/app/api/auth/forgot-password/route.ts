import { NextRequest, NextResponse } from "next/server";
import { createPasswordReset } from "@/lib/server/password-reset";

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => null);
  const email = body?.email;

  if (typeof email !== "string" || !email.trim()) {
    return NextResponse.json(
      { message: "Please enter your email address." },
      { status: 400 }
    );
  }

  const baseUrl = process.env.NEXTAUTH_URL ?? request.nextUrl.origin;
  const result = await createPasswordReset(email, baseUrl);

  return NextResponse.json({
    message:
      "If this email is registered, a password reset link has been prepared.",
    mailed: result.mailed ?? false,
    devResetUrl: result.devResetUrl,
  });
}
