import crypto from "node:crypto";
import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const formData = await request.formData();
    const metadataRaw = String(formData.get("metadata") ?? "{}");
    const metadata = JSON.parse(metadataRaw) as Record<string, unknown>;
    const files = Array.from(formData.values()).filter((item): item is File => item instanceof File);
    const packageName = `REVEAL_submission_${Date.now()}_${crypto.randomUUID().slice(0, 8)}.zip`;

    await prisma.portalSubmission.create({
      data: {
        contactName: String(metadata.contactName ?? ""),
        contactEmail: String(metadata.contactEmail ?? ""),
        company: String(metadata.company ?? ""),
        contractRef: metadata.contractRef ? String(metadata.contractRef) : null,
        notes: metadata.notes ? String(metadata.notes) : null,
        numSites: Number(metadata.numSites ?? 0),
        dataYear: Number(metadata.dataYear ?? new Date().getFullYear()),
        packageName,
        metadata: {
          ...metadata,
          uploadedFileCount: files.length,
          uploadedFiles: files.map((file) => file.name),
        },
      },
    });

    return NextResponse.json({
      success: true,
      packageName,
      sharePointUrl: null,
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to submit portal package" },
      { status: 500 }
    );
  }
}
