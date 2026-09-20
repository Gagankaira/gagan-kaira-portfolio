# Azure Data Engineer Job Application Engine

Purpose: discover, score, deduplicate, and prepare a 50+ job application queue for Gagan's Azure Data Engineer profile.

## Target profile
- 5.2 years
- Azure, Azure Data Factory, ADLS Gen2, Azure Databricks, PySpark, Python, SQL, Synapse
- ETL/ELT, Delta Lake, data warehousing, Azure DevOps/CI-CD
- Preferred: Hyderabad, Bengaluru, Pune, Chennai, Gurugram, Noida, India remote
- Target titles: Azure Data Engineer, Senior Azure Data Engineer, Azure Databricks Engineer, Databricks Data Engineer, Senior Data Engineer (Azure)

## Safety / source policy
- Prefer official company career pages and public job feeds.
- Do not bypass CAPTCHAs, authentication, robots.txt, anti-bot controls, or rate limits.
- Do not automatically submit applications or impersonate the candidate.
- The engine prepares an application queue and opens the direct application page for human review/submission.

## Pipeline
1. Discover public job pages.
2. Normalize title/company/location/date/ID/URL.
3. Deduplicate by job ID, canonical URL, and title/company/location.
4. Score against the target profile.
5. Keep the top 50+ qualified jobs.
6. Generate tailored application notes.
7. Track status: discovered -> ready -> submitted -> screening -> interview -> offer/rejected.

The web application can be extended with Playwright for human-in-the-loop navigation where a site permits it.
