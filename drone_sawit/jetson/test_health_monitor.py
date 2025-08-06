import unittest
from health_monitor import health_report

class TestHealthMonitor(unittest.TestCase):
    def test_health_report_structure(self):
        report = health_report()
        self.assertIn('jetson', report)
        self.assertIn('pixhawk', report)
        self.assertIn('arduino', report)

if __name__ == "__main__":
    unittest.main()
