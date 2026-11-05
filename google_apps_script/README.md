# Google Sheets reporting companion

This Google Apps Script imports a **synthetic** Quality Control Tower CSV export from Google Drive and generates a site-level summary in Google Sheets. It demonstrates Apps Script, Google Workspace reporting, data validation and scheduled automation. It does not connect to Airbus or Skywise.

## Setup
1. Run the local dashboard with `python -m app.backend` and click **Export CSV**.
2. Upload the CSV to Google Drive, retaining its Drive file ID.
3. Create a Google Sheet, open **Extensions > Apps Script** and paste `Code.gs`.
4. In **Project Settings > Script properties**, set `QUALITY_TOWER_CSV_FILE_ID` to the Drive file ID.
5. Run `refreshTowerReport` and authorize the requested Google permissions. The script creates **Tower Data** and **Site Summary** tabs.
6. Optionally run `installMondayRefresh` to schedule refreshes on Mondays at 09:00 in the script's timezone.

**Important:** The scheduled script rereads the same Drive CSV. To receive updated dashboard data, replace the file's contents without changing its Drive ID. This is not a live synchronization service.

The script validates required columns and nonnegative metrics before writing to the Sheet. Google Drive and Sheets access require manual authorization and have not been live-tested.
