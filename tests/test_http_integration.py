"""HTTP integration checks for the local quality dashboard."""
import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class HTTPIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        os.environ["QUALITY_DB"] = str(Path(cls.temp.name) / "quality.db")
        from app import backend
        backend.DB = Path(os.environ["QUALITY_DB"])
        backend.init_db()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), backend.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.temp.cleanup()

    def request(self, path, payload=None):
        body = None if payload is None else json.dumps(payload).encode()
        req = Request(self.base + path, data=body,
                      headers={"Content-Type": "application/json"} if body else {},
                      method="POST" if body else "GET")
        try:
            with urlopen(req, timeout=5) as response:
                return response.status, response.headers, response.read()
        except HTTPError as error:
            return error.code, error.headers, error.read()

    def test_frontend_assets_served(self):
        for path, expected in [("/", b"Quality Control Tower"),
                               ("/app.js", b"loadDetail"),
                               ("/style.css", b"body")]:
            with self.subTest(path=path):
                code, _, body = self.request(path)
                self.assertEqual(code, 200)
                self.assertIn(expected, body)

    def test_analytics_and_filter(self):
        code, _, body = self.request("/api/analytics?site=Hamburg")
        self.assertEqual(code, 200)
        data = json.loads(body)
        self.assertEqual(data["metrics"]["aircraft"], 30)
        self.assertTrue(all(row["site"] == "Hamburg" for row in data["aircraft"]))

    def test_aircraft_detail_and_missing(self):
        code, _, body = self.request("/api/aircraft/SIM-MSN-10042")
        self.assertEqual(code, 200)
        self.assertEqual(len(json.loads(body)["inspections"]), 8)
        code, _, _ = self.request("/api/aircraft/NOT-FOUND")
        self.assertEqual(code, 404)

    def test_status_update_and_validation(self):
        from app import backend
        action = backend.query("SELECT action_id FROM actions LIMIT 1")[0]["action_id"]
        code, _, body = self.request("/api/actions/" + action, {"status": "Closed"})
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["status"], "Closed")
        code, _, _ = self.request("/api/actions/" + action, {"status": "Invalid"})
        self.assertEqual(code, 400)

    def test_request_lifecycle(self):
        code, _, body = self.request("/api/requests", {
            "title": "Weekly defect trends", "detail": "Quality trend analysis", "priority": "High"
        })
        self.assertEqual(code, 200)
        identifier = json.loads(body)["id"]
        code, _, body = self.request(f"/api/requests/{identifier}", {"status": "Feasible"})
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["status"], "Feasible")

    def test_csv_export(self):
        code, headers, body = self.request("/api/export?site=Hamburg")
        self.assertEqual(code, 200)
        self.assertIn("text/csv", headers["Content-Type"])
        self.assertEqual(len(body.decode().strip().splitlines()), 31)

    def test_invalid_site_and_unknown_route(self):
        self.assertEqual(self.request("/api/analytics?site=Invalid")[0], 400)
        self.assertEqual(self.request("/not-a-page")[0], 404)


if __name__ == "__main__":
    unittest.main()
