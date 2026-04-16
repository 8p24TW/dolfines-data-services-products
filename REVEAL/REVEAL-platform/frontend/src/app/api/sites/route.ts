import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { getCurrentUserRecord } from "@/lib/server/auth";
import { buildSiteCreateInput, mapSite } from "@/lib/server/site-mapper";

export const runtime = "nodejs";

export async function GET() {
  try {
    const { user } = await getCurrentUserRecord();
    const where = user
      ? {
          OR: [
            { users: { some: { id: user.id } } },
            { organizationId: user.organizationId },
          ],
        }
      : undefined;

    const sites = await prisma.site.findMany({
      where,
      include: { solar_module_types: true, solar_inverter_units: true },
      orderBy: { display_name: "asc" },
    });

    return NextResponse.json(sites.map(mapSite));
  } catch (error) {
    if (error instanceof Error && error.message === "UNAUTHORIZED") {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    return NextResponse.json({ error: "Failed to load sites" }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const { user } = await getCurrentUserRecord();
    const body = await request.json();

    const created = await prisma.site.create({
      data: buildSiteCreateInput(body, {
        ownerId: user?.id ?? null,
        organizationId: user?.organizationId ?? null,
      }),
      include: { solar_module_types: true, solar_inverter_units: true },
    });

    return NextResponse.json(mapSite(created), { status: 201 });
  } catch (error) {
    if (error instanceof Error && error.message === "UNAUTHORIZED") {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    return NextResponse.json({ error: "Failed to create site" }, { status: 500 });
  }
}
