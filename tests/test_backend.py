import os
import tempfile
import unittest
from pathlib import Path

class BackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        os.environ['QUALITY_DB'] = str(Path(cls.tmp.name) / 'quality.db')
        from app import backend
        backend.DB = Path(os.environ['QUALITY_DB'])
        backend.init_db()
        cls.app = backend

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_dataset_counts(self):
        metrics = self.app.analytics()['metrics']
        self.assertEqual(metrics['aircraft'], 120)
        self.assertEqual(metrics['inspections'], 960)
        self.assertEqual(metrics['findings'], 365)

    def test_site_filter(self):
        self.assertEqual(self.app.analytics('Hamburg')['metrics']['aircraft'], 30)
        self.assertEqual(sum(s['aircraft'] for s in self.app.analytics()['by_site']), 120)

    def test_detail(self):
        detail = self.app.aircraft_detail('SIM-MSN-10042')
        self.assertEqual(detail['aircraft']['aircraft_id'], 'SIM-MSN-10042')
        self.assertEqual(len(detail['inspections']), 8)
        self.assertEqual(len(detail['milestones']), 3)

    def test_action_update(self):
        action = self.app.query('SELECT action_id,status FROM actions LIMIT 1')[0]
        self.app.update_action(action['action_id'], 'Closed')
        self.assertEqual(self.app.query('SELECT status FROM actions WHERE action_id=?',(action['action_id'],))[0]['status'],'Closed')
        with self.assertRaises(ValueError): self.app.update_action(action['action_id'], 'Invalid')

    def test_finding_update(self):
        finding = self.app.query('SELECT finding_id FROM findings LIMIT 1')[0]
        self.app.update_finding(finding['finding_id'],'In Progress')
        self.assertEqual(self.app.query('SELECT status FROM findings WHERE finding_id=?',(finding['finding_id'],))[0]['status'],'In Progress')

    def test_feature_request(self):
        r=self.app.add_request({'title':'Inspection trend','detail':'Compare weekly trends','priority':'High'})
        self.app.update_request(r['id'],'Feasible')
        self.assertEqual(self.app.feasibility()[0]['status'],'Feasible')
        with self.assertRaises(ValueError):self.app.add_request({'title':'No'})

    def test_csv_export(self):
        csv=self.app.export_csv('Hamburg').decode()
        self.assertEqual(len(csv.strip().splitlines()),31)
        self.assertIn('SIM-MSN-10001',csv)

    def test_idempotent_init(self):
        self.app.init_db()
        self.assertEqual(self.app.analytics()['metrics']['aircraft'],120)

if __name__=='__main__': unittest.main()
