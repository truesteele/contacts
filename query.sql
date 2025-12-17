SELECT 
  id,
  first_name,
  last_name,
  first_name || ' ' || last_name AS "Full Name",
  company,
  -- Sanitize position field for CSV export
  REGEXP_REPLACE(
    REPLACE(
      REPLACE(position, ',', ' - '), 
      ';', ' - '
    ), 
    E'[\n\r]+', ' ', 'g'
  ) AS position,
  email,
  email_2,
  work_email,
  personal_email,
  linkedin_url,
  -- Company-related fields that help with email discovery
  company_experience,
  company_domain_experience,
  -- Sanitize headline field for CSV export
  REGEXP_REPLACE(
    REPLACE(
      REPLACE(headline, ',', ' - '), 
      ';', ' - '
    ), 
    E'[\n\r]+', ' ', 'g'
  ) AS headline,
  location_name,
  country,
  taxonomy_classification,
  work_email_discovery_status,
  -- More specific action categorization based on email status
  CASE
    WHEN work_email_discovery_status = 'clay_attempted' THEN 'Already Processed By Clay'
    ELSE 'Need Email Discovery'
  END AS email_action
FROM 
  contacts
WHERE 
  taxonomy_classification::text NOT LIKE 'Low Priority%'
  -- All fields must be either NULL or empty strings
  AND (work_email IS NULL OR work_email = '' OR work_email = 'null') 
  AND (personal_email IS NULL OR personal_email = '' OR personal_email = 'null')
  AND (email IS NULL OR email = '')
  AND (email_2 IS NULL OR email_2 = '')
  -- Explicit check to exclude any records with the text value 'null'
  AND (
    (work_email != 'null' OR work_email IS NULL) AND
    (personal_email != 'null' OR personal_email IS NULL)
  )
  -- Include LinkedIn URL to help with email discovery
  AND linkedin_url IS NOT NULL 
  AND linkedin_url != ''
  -- Only consider records from specific taxonomy classifications that are high priority
  AND (
    taxonomy_classification::text LIKE 'Strategic Business Prospects%'
    OR taxonomy_classification::text LIKE 'Knowledge & Industry Network%'
    OR taxonomy_classification::text LIKE 'Support Network%'
  )
ORDER BY
  -- Order by whether Clay has already attempted discovery
  -- Put records that haven't been attempted yet first
  CASE WHEN work_email_discovery_status IS NULL THEN 0 
       WHEN work_email_discovery_status != 'clay_attempted' THEN 0
       ELSE 1 END,
  -- Prioritize records with company domain information
  CASE WHEN company_domain_experience IS NOT NULL 
       AND company_domain_experience != '' 
       AND company_domain_experience != 'NO_DOMAIN_FOUND' THEN 0 ELSE 1 END,
  -- Then by taxonomy classification importance
  CASE 
    WHEN taxonomy_classification::text LIKE 'Strategic Business Prospects%' THEN 0
    WHEN taxonomy_classification::text LIKE 'Knowledge & Industry Network%' THEN 1
    WHEN taxonomy_classification::text LIKE 'Support Network%' THEN 2
    ELSE 3
  END,
  -- Then by company name presence
  CASE WHEN company IS NOT NULL AND company != '' THEN 0 ELSE 1 END,
  -- Then alphabetically by name
  last_name, 
  first_name; 

-- First, let's diagnose the issue by looking at the specific record
SELECT 
  id,
  first_name,
  last_name,
  personal_email,
  email,
  work_email,
  COALESCE(work_email, email, personal_email) AS best_email,
  -- Check for whitespace or empty strings
  LENGTH(TRIM(personal_email)) AS personal_email_length,
  personal_email = '' AS is_personal_email_empty,
  personal_email IS NULL AS is_personal_email_null
FROM 
  contacts
WHERE 
  id = 1520;

-- Fixed version of the MailerLite contacts view - standalone definition
CREATE OR REPLACE VIEW vw_contacts_for_mailerlite AS
SELECT 
  id,
  first_name,
  last_name,
  COALESCE(
    NULLIF(TRIM(work_email), ''), 
    NULLIF(TRIM(email), ''), 
    NULLIF(TRIM(personal_email), '')
  )::character varying AS best_email,
  email,
  work_email,
  personal_email,
  company,
  position,
  taxonomy_classification,
  email_verified,
  unsubscribed,
  synced_to_mailerlite
FROM 
  contacts
WHERE 
  email_verified = TRUE
  AND unsubscribed = FALSE
  AND (
    (email IS NOT NULL AND TRIM(email) != '') OR 
    (work_email IS NOT NULL AND TRIM(work_email) != '') OR 
    (personal_email IS NOT NULL AND TRIM(personal_email) != '')
  );

-- Fixed version of the unsubscribed contacts view - standalone definition
CREATE OR REPLACE VIEW vw_unsubscribed_contacts AS
SELECT 
  id,
  first_name,
  last_name,
  COALESCE(
    NULLIF(TRIM(work_email), ''), 
    NULLIF(TRIM(email), ''), 
    NULLIF(TRIM(personal_email), '')
  )::character varying AS best_email,
  email,
  work_email,
  personal_email,
  unsubscribed_at,
  unsubscribe_source
FROM 
  contacts
WHERE 
  unsubscribed = TRUE;

-- Here are the clean view definitions by themselves for easy copying:

/*
-- MailerLite view definition
CREATE OR REPLACE VIEW vw_contacts_for_mailerlite AS
SELECT 
  id,
  first_name,
  last_name,
  COALESCE(
    NULLIF(TRIM(work_email), ''), 
    NULLIF(TRIM(email), ''), 
    NULLIF(TRIM(personal_email), '')
  )::character varying AS best_email,
  email,
  work_email,
  personal_email,
  company,
  position,
  taxonomy_classification,
  email_verified,
  unsubscribed,
  synced_to_mailerlite
FROM 
  contacts
WHERE 
  email_verified = TRUE
  AND unsubscribed = FALSE
  AND (
    (email IS NOT NULL AND TRIM(email) != '') OR 
    (work_email IS NOT NULL AND TRIM(work_email) != '') OR 
    (personal_email IS NOT NULL AND TRIM(personal_email) != '')
  );
*/

/*
-- Unsubscribed contacts view definition
CREATE OR REPLACE VIEW vw_unsubscribed_contacts AS
SELECT 
  id,
  first_name,
  last_name,
  COALESCE(
    NULLIF(TRIM(work_email), ''), 
    NULLIF(TRIM(email), ''), 
    NULLIF(TRIM(personal_email), '')
  )::character varying AS best_email,
  email,
  work_email,
  personal_email,
  unsubscribed_at,
  unsubscribe_source
FROM 
  contacts
WHERE 
  unsubscribed = TRUE;
*/

-- Alternatively, you can drop and recreate the views:
/*
DROP VIEW IF EXISTS vw_contacts_for_mailerlite;
CREATE VIEW vw_contacts_for_mailerlite AS
SELECT 
  id,
  first_name,
  last_name,
  COALESCE(
    NULLIF(TRIM(work_email), ''), 
    NULLIF(TRIM(email), ''), 
    NULLIF(TRIM(personal_email), '')
  )::character varying AS best_email,
  email,
  work_email,
  personal_email,
  company,
  position,
  taxonomy_classification,
  email_verified,
  unsubscribed,
  synced_to_mailerlite
FROM 
  contacts
WHERE 
  email_verified = TRUE
  AND unsubscribed = FALSE
  AND (
    (email IS NOT NULL AND TRIM(email) != '') OR 
    (work_email IS NOT NULL AND TRIM(work_email) != '') OR 
    (personal_email IS NOT NULL AND TRIM(personal_email) != '')
  );

DROP VIEW IF EXISTS vw_unsubscribed_contacts;
CREATE VIEW vw_unsubscribed_contacts AS
SELECT 
  id,
  first_name,
  last_name,
  COALESCE(
    NULLIF(TRIM(work_email), ''), 
    NULLIF(TRIM(email), ''), 
    NULLIF(TRIM(personal_email), '')
  )::character varying AS best_email,
  email,
  work_email,
  personal_email,
  unsubscribed_at,
  unsubscribe_source
FROM 
  contacts
WHERE 
  unsubscribed = TRUE;
*/ 