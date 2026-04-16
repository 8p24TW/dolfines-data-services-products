import { NextResponse } from "next/server";
import { postJsonToPythonService } from "@/lib/server/python-service";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const response = await postJsonToPythonService("/market/retrofit-bess", body);
    return NextResponse.json(await response.json());
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to evaluate retrofit BESS case" },
      { status: 500 }
    );
  }
}
