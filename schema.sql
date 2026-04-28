-- =========================
-- PostgreSQL Schema
-- Charity Donation App
-- Run this once against your PostgreSQL database
-- =========================

-- =========================
-- TABLES
-- =========================

CREATE TABLE users (
    "UserID"         SERIAL PRIMARY KEY,
    "FullName"       VARCHAR(100)  NOT NULL,
    "Email"          VARCHAR(100)  UNIQUE NOT NULL,
    "PasswordHash"   VARCHAR(255)  NOT NULL,
    "UserRole"       VARCHAR(20)   NOT NULL CHECK ("UserRole" IN ('Admin','Donor','NGO')),
    "Phone"          VARCHAR(20),
    "Address"        VARCHAR(255),
    "ProfilePicture" VARCHAR(255),
    "CreatedAt"      TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ngos (
    "NGOID"          SERIAL PRIMARY KEY,
    "UserID"         INT  UNIQUE REFERENCES users("UserID") ON DELETE CASCADE,
    "Mission"        TEXT,
    "TaxID"          VARCHAR(50)  UNIQUE NOT NULL,
    "IsVerified"     BOOLEAN      DEFAULT false,
    "Phone"          VARCHAR(20),
    "Address"        VARCHAR(255),
    "ProfilePicture" VARCHAR(255)
);

CREATE TABLE campaigns (
    "CampaignID"    SERIAL PRIMARY KEY,
    "NGOID"         INT           NOT NULL REFERENCES ngos("NGOID") ON DELETE CASCADE,
    "Title"         VARCHAR(200)  NOT NULL,
    "Description"   TEXT,
    "TargetGoal"    DECIMAL(15,2) NOT NULL CHECK ("TargetGoal" > 0),
    "CurrentAmount" DECIMAL(15,2) NOT NULL DEFAULT 0 CHECK ("CurrentAmount" >= 0),
    "StartDate"     DATE          NOT NULL,
    "EndDate"       DATE          NOT NULL,
    CONSTRAINT chk_campaign_dates CHECK ("EndDate" >= "StartDate")
);

CREATE TABLE donations (
    "DonationID"   SERIAL PRIMARY KEY,
    "DonorID"      INT           NOT NULL REFERENCES users("UserID") ON DELETE CASCADE,
    "CampaignID"   INT           NOT NULL REFERENCES campaigns("CampaignID") ON DELETE CASCADE,
    "Amount"       DECIMAL(15,2) NOT NULL CHECK ("Amount" > 0),
    "DonationDate" TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE beneficiaries (
    "BeneficiaryID"   SERIAL PRIMARY KEY,
    "CampaignID"      INT          NOT NULL REFERENCES campaigns("CampaignID") ON DELETE CASCADE,
    "BeneficiaryName" VARCHAR(100) NOT NULL,
    "Details"         TEXT
);

-- =========================
-- TRIGGER: Auto-update campaign amount on donation insert
-- =========================
CREATE OR REPLACE FUNCTION update_campaign_amount()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE campaigns
    SET "CurrentAmount" = "CurrentAmount" + NEW."Amount"
    WHERE "CampaignID" = NEW."CampaignID";
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_campaign_amount
AFTER INSERT ON donations
FOR EACH ROW
EXECUTE FUNCTION update_campaign_amount();

-- =========================
-- VIEWS
-- =========================

CREATE VIEW view_campaigncards AS
SELECT
    c."CampaignID",
    c."Title",
    c."Description",
    c."TargetGoal",
    c."CurrentAmount",
    (c."CurrentAmount" * 100.0 / c."TargetGoal") AS "ProgressPercent",
    u."FullName" AS "NGOName",
    c."EndDate",
    (c."EndDate" - CURRENT_DATE) AS "DaysLeft"
FROM campaigns c
JOIN ngos n ON c."NGOID" = n."NGOID"
JOIN users u ON n."UserID" = u."UserID";

CREATE VIEW view_campaignprogress AS
SELECT
    "CampaignID",
    "Title",
    "TargetGoal",
    "CurrentAmount",
    ("CurrentAmount" * 100.0 / "TargetGoal") AS "ProgressPercent",
    CASE
        WHEN CURRENT_DATE < "StartDate" THEN 'Upcoming'
        WHEN CURRENT_DATE BETWEEN "StartDate" AND "EndDate" THEN 'Active'
        ELSE 'Closed'
    END AS "Status"
FROM campaigns;

CREATE VIEW view_campaigncompletion AS
SELECT
    "CampaignID",
    "Title",
    "TargetGoal",
    "CurrentAmount",
    ("CurrentAmount" * 100.0 / "TargetGoal") AS "CompletionPercent",
    CASE
        WHEN "CurrentAmount" >= "TargetGoal" THEN 'Completed'
        WHEN "CurrentAmount" > 0             THEN 'In Progress'
        ELSE 'Not Started'
    END AS "Status"
FROM campaigns;

CREATE VIEW view_donorsummary AS
SELECT
    u."UserID",
    u."FullName",
    COUNT(d."DonationID")      AS "TotalDonations",
    COALESCE(SUM(d."Amount"),0) AS "TotalAmountDonated"
FROM users u
LEFT JOIN donations d ON u."UserID" = d."DonorID"
WHERE u."UserRole" = 'Donor'
GROUP BY u."UserID", u."FullName";

CREATE VIEW view_ngostats AS
SELECT
    n."NGOID",
    u."FullName"                  AS "NGOName",
    COUNT(c."CampaignID")         AS "TotalCampaigns",
    COALESCE(SUM(c."CurrentAmount"),0) AS "TotalRaised",
    COALESCE(SUM(c."TargetGoal"),0)    AS "TotalGoal"
FROM ngos n
JOIN users u ON n."UserID" = u."UserID"
LEFT JOIN campaigns c ON n."NGOID" = c."NGOID"
GROUP BY n."NGOID", u."FullName";

CREATE VIEW view_topdonors AS
SELECT
    u."UserID",
    u."FullName",
    SUM(d."Amount") AS "TotalDonation"
FROM users u
JOIN donations d ON u."UserID" = d."DonorID"
GROUP BY u."UserID", u."FullName";

CREATE VIEW view_recentdonations AS
SELECT
    u."FullName"  AS "DonorName",
    c."Title"     AS "CampaignTitle",
    d."Amount",
    d."DonationDate"
FROM donations d
JOIN users     u ON d."DonorID"    = u."UserID"
JOIN campaigns c ON d."CampaignID" = c."CampaignID"
ORDER BY d."DonationDate" DESC
LIMIT 10;

-- =========================
-- SAMPLE DATA
-- =========================

INSERT INTO users ("FullName", "Email", "PasswordHash", "UserRole") VALUES
    ('Admin User',  'admin@test.com',  'pass@123', 'Admin'),
    ('Ali Khan',    'ali@test.com',    'pass123',  'NGO'),
    ('Sara Ahmed',  'sara@test.com',   'pass123',  'Donor'),
    ('Usman Tariq', 'usman@test.com',  'pass123',  'NGO'),
    ('Ayesha Noor', 'ayesha@test.com', 'pass123',  'Donor');

INSERT INTO ngos ("UserID", "Mission", "TaxID", "IsVerified")
    SELECT "UserID", 'Tree Plantation', 'TAX001', true FROM users WHERE "Email" = 'ali@test.com';

INSERT INTO ngos ("UserID", "Mission", "TaxID", "IsVerified")
    SELECT "UserID", 'Education Support', 'TAX002', true FROM users WHERE "Email" = 'usman@test.com';

INSERT INTO campaigns ("NGOID", "Title", "Description", "TargetGoal", "CurrentAmount", "StartDate", "EndDate")
    SELECT "NGOID", 'Plant Trees', 'Plant 10,000 trees', 50000, 0, '2026-01-01', '2026-12-01'
    FROM ngos WHERE "TaxID" = 'TAX001';

INSERT INTO campaigns ("NGOID", "Title", "Description", "TargetGoal", "CurrentAmount", "StartDate", "EndDate")
    SELECT "NGOID", 'Education Fund', 'Support poor students', 80000, 0, '2026-02-01', '2026-12-01'
    FROM ngos WHERE "TaxID" = 'TAX002';

INSERT INTO campaigns ("NGOID", "Title", "Description", "TargetGoal", "CurrentAmount", "StartDate", "EndDate")
    SELECT "NGOID", 'Clean Water', 'Provide clean water to villages', 60000, 0, '2026-03-01', '2026-12-01'
    FROM ngos WHERE "TaxID" = 'TAX001';

INSERT INTO campaigns ("NGOID", "Title", "Description", "TargetGoal", "CurrentAmount", "StartDate", "EndDate")
    SELECT "NGOID", 'School Supplies', 'Books and stationery for children', 40000, 0, '2026-01-15', '2026-12-30'
    FROM ngos WHERE "TaxID" = 'TAX002';

INSERT INTO campaigns ("NGOID", "Title", "Description", "TargetGoal", "CurrentAmount", "StartDate", "EndDate")
    SELECT "NGOID", 'Green Pakistan', 'Environmental awareness campaign', 30000, 0, '2026-04-01', '2026-12-01'
    FROM ngos WHERE "TaxID" = 'TAX001';

-- Donations (trigger auto-updates CurrentAmount)
INSERT INTO donations ("DonorID", "CampaignID", "Amount")
    SELECT
        (SELECT "UserID" FROM users WHERE "Email" = 'sara@test.com'),
        (SELECT "CampaignID" FROM campaigns WHERE "Title" = 'Plant Trees'),
        2000;

INSERT INTO donations ("DonorID", "CampaignID", "Amount")
    SELECT
        (SELECT "UserID" FROM users WHERE "Email" = 'ayesha@test.com'),
        (SELECT "CampaignID" FROM campaigns WHERE "Title" = 'Education Fund'),
        3000;

INSERT INTO donations ("DonorID", "CampaignID", "Amount")
    SELECT
        (SELECT "UserID" FROM users WHERE "Email" = 'sara@test.com'),
        (SELECT "CampaignID" FROM campaigns WHERE "Title" = 'Clean Water'),
        1500;

INSERT INTO donations ("DonorID", "CampaignID", "Amount")
    SELECT
        (SELECT "UserID" FROM users WHERE "Email" = 'ayesha@test.com'),
        (SELECT "CampaignID" FROM campaigns WHERE "Title" = 'School Supplies'),
        2500;

INSERT INTO donations ("DonorID", "CampaignID", "Amount")
    SELECT
        (SELECT "UserID" FROM users WHERE "Email" = 'sara@test.com'),
        (SELECT "CampaignID" FROM campaigns WHERE "Title" = 'Green Pakistan'),
        1000;

INSERT INTO beneficiaries ("CampaignID", "BeneficiaryName", "Details")
    SELECT "CampaignID", 'Green Society',  'Tree plantation volunteers' FROM campaigns WHERE "Title" = 'Plant Trees';

INSERT INTO beneficiaries ("CampaignID", "BeneficiaryName", "Details")
    SELECT "CampaignID", 'Student Aid Org', 'Helping poor students'     FROM campaigns WHERE "Title" = 'Education Fund';

INSERT INTO beneficiaries ("CampaignID", "BeneficiaryName", "Details")
    SELECT "CampaignID", 'Water NGO',      'Clean water supply'         FROM campaigns WHERE "Title" = 'Clean Water';

INSERT INTO beneficiaries ("CampaignID", "BeneficiaryName", "Details")
    SELECT "CampaignID", 'School Trust',   'Providing books and stationery' FROM campaigns WHERE "Title" = 'School Supplies';

INSERT INTO beneficiaries ("CampaignID", "BeneficiaryName", "Details")
    SELECT "CampaignID", 'Eco Group',      'Environment awareness'      FROM campaigns WHERE "Title" = 'Green Pakistan';
