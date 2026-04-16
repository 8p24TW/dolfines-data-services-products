-- AlterTable
ALTER TABLE "Site"
ADD COLUMN "site_timezone" TEXT DEFAULT 'Europe/Paris',
ADD COLUMN "irradiance_basis" TEXT,
ADD COLUMN "module_tilt_deg" DOUBLE PRECISION,
ADD COLUMN "tariff_eur_mwh" DOUBLE PRECISION;

-- CreateTable
CREATE TABLE "SolarInverterUnit" (
    "id" TEXT NOT NULL,
    "siteId" TEXT NOT NULL,
    "tag" TEXT NOT NULL,
    "dc_capacity_kwp" DOUBLE PRECISION NOT NULL,
    "ac_capacity_kw" DOUBLE PRECISION,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "SolarInverterUnit_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "SolarInverterUnit_siteId_tag_key" ON "SolarInverterUnit"("siteId", "tag");

-- AddForeignKey
ALTER TABLE "SolarInverterUnit" ADD CONSTRAINT "SolarInverterUnit_siteId_fkey" FOREIGN KEY ("siteId") REFERENCES "Site"("id") ON DELETE CASCADE ON UPDATE CASCADE;
