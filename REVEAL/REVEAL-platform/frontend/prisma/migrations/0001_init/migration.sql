-- CreateSchema
CREATE SCHEMA IF NOT EXISTS "public";

-- CreateEnum
CREATE TYPE "PlanType" AS ENUM ('one_shot', 'unlimited');

-- CreateEnum
CREATE TYPE "SiteType" AS ENUM ('solar', 'wind');

-- CreateEnum
CREATE TYPE "SiteStatus" AS ENUM ('operational', 'maintenance', 'offline');

-- CreateEnum
CREATE TYPE "ReportType" AS ENUM ('comprehensive', 'daily', 'monthly');

-- CreateEnum
CREATE TYPE "ReportStatus" AS ENUM ('queued', 'running', 'complete', 'error');

-- CreateEnum
CREATE TYPE "ReportLanguage" AS ENUM ('en', 'fr');

-- CreateTable
CREATE TABLE "Organization" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Organization_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "User" (
    "id" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "password" TEXT,
    "display_name" TEXT NOT NULL,
    "plan_type" "PlanType" NOT NULL,
    "organizationId" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "User_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Site" (
    "id" TEXT NOT NULL,
    "display_name" TEXT NOT NULL,
    "country" TEXT NOT NULL,
    "region" TEXT NOT NULL,
    "cod" DATE NOT NULL,
    "technology" TEXT NOT NULL,
    "site_type" "SiteType" NOT NULL,
    "status" "SiteStatus" NOT NULL,
    "lat" DOUBLE PRECISION NOT NULL,
    "lon" DOUBLE PRECISION NOT NULL,
    "cap_ac_kw" DOUBLE PRECISION NOT NULL,
    "cap_dc_kwp" DOUBLE PRECISION NOT NULL,
    "n_inverters" INTEGER NOT NULL,
    "inv_ac_kw" DOUBLE PRECISION NOT NULL,
    "inv_model" TEXT NOT NULL,
    "n_modules" INTEGER NOT NULL,
    "module_wp" DOUBLE PRECISION NOT NULL,
    "module_brand" TEXT,
    "dc_ac_ratio" DOUBLE PRECISION NOT NULL,
    "design_pr" DOUBLE PRECISION NOT NULL,
    "operating_pr_target" DOUBLE PRECISION NOT NULL,
    "interval_min" INTEGER NOT NULL,
    "irr_threshold" DOUBLE PRECISION NOT NULL,
    "power_threshold" DOUBLE PRECISION NOT NULL,
    "temp_coeff" DOUBLE PRECISION,
    "data_dir" TEXT,
    "owner_id" TEXT,
    "plan_type" "PlanType",
    "hub_height_m" DOUBLE PRECISION,
    "tip_height_m" DOUBLE PRECISION,
    "rotor_diameter_m" DOUBLE PRECISION,
    "expected_aep_gwh" DOUBLE PRECISION,
    "organizationId" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Site_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "SolarModuleType" (
    "id" TEXT NOT NULL,
    "siteId" TEXT NOT NULL,
    "manufacturer" TEXT,
    "model" TEXT NOT NULL,
    "module_wp" DOUBLE PRECISION NOT NULL,
    "quantity" INTEGER NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "SolarModuleType_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Report" (
    "id" TEXT NOT NULL,
    "siteId" TEXT NOT NULL,
    "reportType" "ReportType" NOT NULL,
    "reportDate" DATE,
    "generatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "lang" "ReportLanguage" NOT NULL,
    "filename" TEXT NOT NULL,
    "downloadUrl" TEXT NOT NULL,
    "sizeBytes" INTEGER,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Report_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ReportJob" (
    "id" TEXT NOT NULL,
    "siteId" TEXT NOT NULL,
    "reportType" "ReportType" NOT NULL,
    "reportDate" DATE,
    "lang" "ReportLanguage" NOT NULL,
    "status" "ReportStatus" NOT NULL,
    "progress" INTEGER NOT NULL DEFAULT 0,
    "pdfUrl" TEXT,
    "error" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "ReportJob_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "PortalSubmission" (
    "id" TEXT NOT NULL,
    "organizationId" TEXT,
    "contactName" TEXT NOT NULL,
    "contactEmail" TEXT NOT NULL,
    "company" TEXT NOT NULL,
    "contractRef" TEXT,
    "notes" TEXT,
    "numSites" INTEGER NOT NULL,
    "dataYear" INTEGER NOT NULL,
    "packageName" TEXT,
    "sharePointUrl" TEXT,
    "metadata" JSONB,
    "submittedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "PortalSubmission_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "_UserSiteAccess" (
    "A" TEXT NOT NULL,
    "B" TEXT NOT NULL,

    CONSTRAINT "_UserSiteAccess_AB_pkey" PRIMARY KEY ("A","B")
);

-- CreateIndex
CREATE UNIQUE INDEX "Organization_name_key" ON "Organization"("name");

-- CreateIndex
CREATE UNIQUE INDEX "User_email_key" ON "User"("email");

-- CreateIndex
CREATE INDEX "_UserSiteAccess_B_index" ON "_UserSiteAccess"("B");

-- AddForeignKey
ALTER TABLE "User" ADD CONSTRAINT "User_organizationId_fkey" FOREIGN KEY ("organizationId") REFERENCES "Organization"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Site" ADD CONSTRAINT "Site_organizationId_fkey" FOREIGN KEY ("organizationId") REFERENCES "Organization"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "SolarModuleType" ADD CONSTRAINT "SolarModuleType_siteId_fkey" FOREIGN KEY ("siteId") REFERENCES "Site"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Report" ADD CONSTRAINT "Report_siteId_fkey" FOREIGN KEY ("siteId") REFERENCES "Site"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ReportJob" ADD CONSTRAINT "ReportJob_siteId_fkey" FOREIGN KEY ("siteId") REFERENCES "Site"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "PortalSubmission" ADD CONSTRAINT "PortalSubmission_organizationId_fkey" FOREIGN KEY ("organizationId") REFERENCES "Organization"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "_UserSiteAccess" ADD CONSTRAINT "_UserSiteAccess_A_fkey" FOREIGN KEY ("A") REFERENCES "Site"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "_UserSiteAccess" ADD CONSTRAINT "_UserSiteAccess_B_fkey" FOREIGN KEY ("B") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;

