/**
 * One-time backfill: create the REVEAL demo site and connect every existing
 * user to it. Safe to run multiple times — fully idempotent.
 *
 * Usage:
 *   npx ts-node --project tsconfig.json prisma/backfill-demo-site.ts
 * or via Railway one-off:
 *   npx tsx prisma/backfill-demo-site.ts
 */
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

const DEMO_SITE_ID = "REVEAL_DEMO_SITE";

const DEMO_INVERTERS = [
  { tag: "INV1",  module_count: 594,  dc_capacity_kwp: 273.24 },
  { tag: "INV2",  module_count: 702,  dc_capacity_kwp: 322.92 },
  { tag: "INV3",  module_count: 684,  dc_capacity_kwp: 314.64 },
  { tag: "INV4",  module_count: 684,  dc_capacity_kwp: 314.64 },
  { tag: "INV5",  module_count: 666,  dc_capacity_kwp: 306.36 },
  { tag: "INV6",  module_count: 738,  dc_capacity_kwp: 339.48 },
  { tag: "INV7",  module_count: 684,  dc_capacity_kwp: 314.64 },
  { tag: "INV8",  module_count: 720,  dc_capacity_kwp: 331.20 },
  { tag: "INV9",  module_count: 702,  dc_capacity_kwp: 322.92 },
  { tag: "INV10", module_count: 720,  dc_capacity_kwp: 331.20 },
  { tag: "INV11", module_count: 720,  dc_capacity_kwp: 331.20 },
  { tag: "INV12", module_count: 504,  dc_capacity_kwp: 231.84 },
  { tag: "INV13", module_count: 720,  dc_capacity_kwp: 331.20 },
  { tag: "INV14", module_count: 702,  dc_capacity_kwp: 322.92 },
  { tag: "INV15", module_count: 684,  dc_capacity_kwp: 314.64 },
  { tag: "INV16", module_count: 738,  dc_capacity_kwp: 339.48 },
  { tag: "INV17", module_count: 720,  dc_capacity_kwp: 331.20 },
  { tag: "INV18", module_count: 720,  dc_capacity_kwp: 331.20 },
  { tag: "INV19", module_count: 720,  dc_capacity_kwp: 331.20 },
  { tag: "INV20", module_count: 720,  dc_capacity_kwp: 331.20 },
  { tag: "INV21", module_count: 720,  dc_capacity_kwp: 331.20 },
  { tag: "INV22", module_count: 720,  dc_capacity_kwp: 331.20 },
  { tag: "INV23", module_count: 720,  dc_capacity_kwp: 331.20 },
  { tag: "INV24", module_count: 720,  dc_capacity_kwp: 331.20 },
  { tag: "INV25", module_count: 720,  dc_capacity_kwp: 331.20 },
  { tag: "INV26", module_count: 666,  dc_capacity_kwp: 306.36 },
  { tag: "INV27", module_count: 720,  dc_capacity_kwp: 331.20 },
  { tag: "INV28", module_count: 648,  dc_capacity_kwp: 298.08 },
  { tag: "INV29", module_count: 720,  dc_capacity_kwp: 331.20 },
  { tag: "INV30", module_count: 720,  dc_capacity_kwp: 331.20 },
  { tag: "INV31", module_count: 486,  dc_capacity_kwp: 223.56 },
];

async function main() {
  // 1. Create the demo site if it doesn't exist
  const existing = await prisma.site.findUnique({ where: { id: DEMO_SITE_ID } });

  if (!existing) {
    console.log("Creating REVEAL demo site...");
    await prisma.site.create({
      data: {
        id: DEMO_SITE_ID,
        display_name: "REVEAL",
        country: "France",
        region: "Nouvelle Aquitaine",
        cod: new Date("2022-03-01T00:00:00.000Z"),
        technology: "Ground-mounted (CdTe thin-film)",
        site_type: "solar",
        status: "operational",
        lat: 44.689139,
        lon: -0.564833,
        cap_ac_kw: 7750,
        cap_dc_kwp: 9844.92,
        n_inverters: 31,
        inv_ac_kw: 250,
        inv_model: "SG250HX",
        n_modules: 21402,
        module_wp: 460,
        module_brand: "First Solar",
        site_timezone: "Europe/Paris",
        irradiance_basis: "poa",
        module_tilt_deg: 15,
        tariff_eur_mwh: 85,
        dc_ac_ratio: 1.2703,
        design_pr: 0.8,
        operating_pr_target: 0.8,
        interval_min: 10,
        irr_threshold: 50,
        power_threshold: 0,
        has_bess: false,
        retrofit_bess_enabled: false,
        solar_inverter_units: {
          create: DEMO_INVERTERS.map((inv) => ({
            tag: inv.tag,
            module_count: inv.module_count,
            dc_capacity_kwp: inv.dc_capacity_kwp,
          })),
        },
      },
    });
    console.log("  ✓ Demo site created");
  } else {
    console.log("Demo site already exists — skipping creation");
  }

  // 2. Connect every user to the demo site
  const allUsers = await prisma.user.findMany({ select: { id: true, email: true } });
  console.log(`Connecting ${allUsers.length} users to the demo site...`);

  await prisma.site.update({
    where: { id: DEMO_SITE_ID },
    data: {
      users: {
        connect: allUsers.map((u) => ({ id: u.id })),
      },
    },
  });

  console.log(`  ✓ ${allUsers.length} users connected`);
  allUsers.forEach((u) => console.log(`    - ${u.email}`));
}

main()
  .then(async () => {
    await prisma.$disconnect();
    console.log("\nDone.");
  })
  .catch(async (error) => {
    console.error(error);
    await prisma.$disconnect();
    process.exit(1);
  });
