import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { hashPassword } from "@/lib/server/passwords";
import { sendWelcomeEmail } from "@/lib/server/password-reset";

const EXTERNAL_ORGANIZATION = "External Access";

export async function POST(request: Request) {
  try {
    const body = await request.json().catch(() => null);

    const email = typeof body?.email === "string" ? body.email.trim().toLowerCase() : "";
    const password = typeof body?.password === "string" ? body.password.trim() : "";
    const name = typeof body?.name === "string" ? body.name.trim() : "";

    if (!name || !email || !password) {
      return NextResponse.json(
        { message: "Name, email, and password are required." },
        { status: 400 }
      );
    }

    if (password.length < 8) {
      return NextResponse.json(
        { message: "Password must be at least 8 characters long." },
        { status: 400 }
      );
    }

    const existingUser = await prisma.user.findUnique({
      where: { email },
    });

    if (existingUser) {
      return NextResponse.json(
        { message: "An account already exists for this email address." },
        { status: 409 }
      );
    }

    const organization = await prisma.organization.upsert({
      where: { name: EXTERNAL_ORGANIZATION },
      update: {},
      create: { name: EXTERNAL_ORGANIZATION },
    });

    const hashedPassword = await hashPassword(password);
    const user = await prisma.user.create({
      data: {
        email,
        password: hashedPassword,
        display_name: name,
        plan_type: "unlimited",
        organizationId: organization.id,
      },
    });

    void sendWelcomeEmail(user.email, user.display_name).catch((mailError) => {
      console.error("welcome-email-error", mailError);
    });

    return NextResponse.json({
      id: user.id,
      email: user.email,
      name: user.display_name,
    });
  } catch (error) {
    console.error("register-route-error", error);

    const message =
      error instanceof Error
        ? error.message
        : "Registration service is unavailable right now.";

    return NextResponse.json(
      {
        message:
          process.env.NODE_ENV === "production"
            ? "Registration service is unavailable right now."
            : message,
      },
      { status: 500 }
    );
  }
}
