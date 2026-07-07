import tempfile
import unittest
from pathlib import Path

from src.ingestion import orchestrator


class OrchestratorTests(unittest.TestCase):
    def test_discover_ingestion_scripts_excludes_orchestrator_and_init(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            scripts_dir = Path(tmp_dir)
            (scripts_dir / "weather_data_collector.py").write_text("print('x')", encoding="utf-8")
            (scripts_dir / "wunderground.py").write_text("print('x')", encoding="utf-8")
            (scripts_dir / "orchestrator.py").write_text("print('x')", encoding="utf-8")
            (scripts_dir / "__init__.py").write_text("", encoding="utf-8")
            (scripts_dir / "notes.txt").write_text("ignore", encoding="utf-8")

            scripts = orchestrator.discover_ingestion_scripts(scripts_dir)

            self.assertEqual([script.name for script in scripts], ["weather_data_collector.py", "wunderground.py"])


if __name__ == "__main__":
    unittest.main()
