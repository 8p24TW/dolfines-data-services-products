import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

async function main() {
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const outputDir = path.resolve(process.cwd(), "backups");
  const outputPath = path.join(outputDir, `reveal-production-snapshot-${timestamp}.json`);

  const [organizations, users, sites] = await Promise.all([
    prisma.organization.findMany({
      orderBy: { name: "asc" },
    }),
    prisma.user.findMany({
      orderBy: { email: "asc" },
      include: {
        sites: {
          select: {
            id: true,
            display_name: true,
          },
          orderBy: { display_name: "asc" },
        },
      },
    }),
    prisma.site.findMany({
      orderBy: { display_name: "asc" },
      include: {
        users: {
          select: {
            id: true,
            email: true,
            display_name: true,
          },
          orderBy: { email: "asc" },
        },
        solar_module_types: true,
        solar_inverter_units: true,
      },
    }),
  ]);

  await mkdir(outputDir, { recursive: true });
  await writeFile(
    outputPath,
    JSON.stringify(
      {
        exportedAt: new Date().toISOString(),
        organizations,
        users,
        sites,
      },
      null,
      2
    ),
    "utf8"
  );

  console.log(`REVEAL production snapshot written to ${outputPath}`);
}

main()
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
