const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('google_apps_script/Code.gs', 'utf8');
const context = {
  Utilities: { parseCsv: text => text.trim().split(/\r?\n/).map(line => line.split(',')) }
};
vm.createContext(context);
vm.runInContext(source, context);
const csv = [
  'aircraft_id,site,family,planned_delivery,inspection_count,finding_count,open_findings,high_open,overdue_actions',
  'SIM-MSN-10001,Hamburg,A320neo,2027-01-02,8,3,2,1,1',
  'SIM-MSN-10002,Hamburg,A320neo,2027-01-03,8,4,1,0,2',
  'SIM-MSN-10003,Toulouse,A321neo,2027-01-04,8,2,1,1,0'
].join('\n');
const report = context.parseTowerCsv(csv);
assert.equal(report.summary.length, 2);
assert.equal(report.summary[0].site, 'Hamburg');
assert.equal(report.summary[0].aircraft, 2);
assert.equal(report.summary[0].open, 3);
assert.equal(report.summary[0].overdue, 3);
assert.equal(report.summary[1].site, 'Toulouse');
assert.throws(() => context.parseTowerCsv('aircraft_id,site\na,b'), /Missing CSV column/);
assert.throws(() => context.parseTowerCsv(csv.replace(',8,3,2,1,1', ',-1,3,2,1,1')), /Invalid nonnegative metric/);
console.log('Google Apps Script reporting tests passed');
