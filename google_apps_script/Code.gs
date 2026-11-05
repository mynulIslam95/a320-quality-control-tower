/**
 * Google Workspace reporting companion for the synthetic Quality Control Tower.
 * Upload the dashboard's Export CSV file to Drive and set the script property
 * QUALITY_TOWER_CSV_FILE_ID to its Drive file ID.
 * No Airbus, Skywise or operational systems are accessed.
 */
const CSV_PROPERTY = 'QUALITY_TOWER_CSV_FILE_ID';
const DATA_TAB = 'Tower Data';
const REPORT_TAB = 'Site Summary';
const REQUIRED = ['aircraft_id','site','inspection_count','finding_count','open_findings','high_open','overdue_actions'];

function parseTowerCsv(csvText) {
  const rows = Utilities.parseCsv(csvText);
  if (rows.length < 2) throw new Error('CSV must contain a header and data rows.');
  const header = rows[0].map(value => String(value).trim());
  const positions = {};
  header.forEach((value, index) => { positions[value] = index; });
  REQUIRED.forEach(name => {
    if (positions[name] === undefined) throw new Error('Missing CSV column: ' + name);
  });
  const data = rows.slice(1).filter(row => String(row[positions.aircraft_id] || '').trim());
  if (!data.length) throw new Error('CSV contains no aircraft records.');
  const sites = {};
  data.forEach(row => {
    const site = String(row[positions.site]).trim();
    if (!site) throw new Error('Missing production site.');
    if (!sites[site]) sites[site] = {site:site, aircraft:0, inspections:0, findings:0, open:0, high:0, overdue:0};
    const group = sites[site];
    group.aircraft += 1;
    [['inspection_count','inspections'],['finding_count','findings'],['open_findings','open'],
     ['high_open','high'],['overdue_actions','overdue']].forEach(pair => {
      const raw = String(row[positions[pair[0]]]).trim();
      const value = Number(raw);
      if (raw === '' || !Number.isFinite(value) || value < 0)
        throw new Error('Invalid nonnegative metric ' + pair[0] + ' for ' + row[positions.aircraft_id]);
      group[pair[1]] += value;
    });
  });
  return {rows:rows, summary:Object.values(sites).sort((a,b) => a.site.localeCompare(b.site))};
}

function refreshTowerReport() {
  const id = PropertiesService.getScriptProperties().getProperty(CSV_PROPERTY);
  if (!id) throw new Error('Configure script property ' + CSV_PROPERTY + ' first.');
  const csv = DriveApp.getFileById(id).getBlob().getDataAsString('UTF-8');
  const result = parseTowerCsv(csv); // Validate before modifying any spreadsheet tabs.
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  const dataTab = spreadsheet.getSheetByName(DATA_TAB) || spreadsheet.insertSheet(DATA_TAB);
  const reportTab = spreadsheet.getSheetByName(REPORT_TAB) || spreadsheet.insertSheet(REPORT_TAB);
  dataTab.clearContents();
  dataTab.getRange(1,1,result.rows.length,result.rows[0].length).setValues(result.rows);
  const output = [['Site','Aircraft','Inspections','Findings','Open findings','High severity open','Overdue actions']]
    .concat(result.summary.map(s => [s.site,s.aircraft,s.inspections,s.findings,s.open,s.high,s.overdue]));
  reportTab.clearContents();
  reportTab.getRange(1,1,output.length,7).setValues(output);
  reportTab.getRange(1,1,1,7).setFontWeight('bold');
  reportTab.autoResizeColumns(1,7);
  return result.summary;
}

function installMondayRefresh() {
  ScriptApp.getProjectTriggers()
    .filter(trigger => trigger.getHandlerFunction() === 'refreshTowerReport')
    .forEach(trigger => ScriptApp.deleteTrigger(trigger));
  ScriptApp.newTrigger('refreshTowerReport').timeBased()
    .onWeekDay(ScriptApp.WeekDay.MONDAY).atHour(9).create();
}
