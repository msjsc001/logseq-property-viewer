import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from backend.file_watcher import file_watcher
from run_app import wait_for_service


class _HealthHandler(BaseHTTPRequestHandler):
    payload = {"status": "ok", "app": "property-query"}

    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(self.payload).encode("utf-8"))

    def log_message(self, format, *args):  # noqa: A003
        return


class RunAppAndWatcherTests(unittest.TestCase):
    def setUp(self):
        file_watcher.stop_watching()
        file_watcher.clear_pending_changes()
        file_watcher.set_last_apply_failures([])

    def tearDown(self):
        file_watcher.stop_watching()
        file_watcher.clear_pending_changes()
        file_watcher.set_last_apply_failures([])

    def test_wait_for_service_requires_the_expected_app_signature(self):
        server = HTTPServer(("127.0.0.1", 0), _HealthHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            self.assertTrue(wait_for_service(f"http://127.0.0.1:{server.server_port}", timeout=2))
            _HealthHandler.payload = {"status": "ok", "app": "other-service"}
            self.assertFalse(wait_for_service(f"http://127.0.0.1:{server.server_port}", timeout=1))
        finally:
            server.shutdown()
            server.server_close()
            _HealthHandler.payload = {"status": "ok", "app": "property-query"}

    def test_watcher_supports_non_standard_roots_and_path_switching(self):
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            Path(first_dir, "note.md").write_text("- a\n  status:: done\n", encoding="utf-8")
            Path(second_dir, "other.md").write_text("- b\n  status:: open\n", encoding="utf-8")

            self.assertTrue(file_watcher.start_watching(first_dir))
            self.assertEqual(file_watcher.get_status()["path"], first_dir)
            self.assertTrue(file_watcher.start_watching(second_dir))
            self.assertEqual(file_watcher.get_status()["path"], second_dir)


if __name__ == "__main__":
    unittest.main()
