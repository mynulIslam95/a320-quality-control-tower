CREATE TABLE IF NOT EXISTS aircraft (aircraft_id TEXT PRIMARY KEY, site TEXT NOT NULL, family TEXT NOT NULL, planned_delivery TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS inspections (inspection_id TEXT PRIMARY KEY, aircraft_id TEXT NOT NULL REFERENCES aircraft(aircraft_id), inspection_date TEXT NOT NULL, area TEXT NOT NULL, result TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS findings (finding_id TEXT PRIMARY KEY, inspection_id TEXT NOT NULL REFERENCES inspections(inspection_id), severity TEXT NOT NULL, status TEXT NOT NULL, description TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS actions (action_id TEXT PRIMARY KEY, finding_id TEXT NOT NULL REFERENCES findings(finding_id), owner TEXT NOT NULL, due_date TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS milestones (milestone_id TEXT PRIMARY KEY, aircraft_id TEXT NOT NULL REFERENCES aircraft(aircraft_id), stage TEXT NOT NULL, target_date TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS requests (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, detail TEXT NOT NULL, priority TEXT NOT NULL, status TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_inspections_aircraft ON inspections(aircraft_id);
CREATE INDEX IF NOT EXISTS idx_findings_inspection ON findings(inspection_id);
CREATE INDEX IF NOT EXISTS idx_actions_finding ON actions(finding_id);
