# test_pipeline.py – End-to-end and unit tests for Drone Sawit Jetson modules
import unittest
import os
import pandas as pd
from ai_output_loader import load_ai_predictions
from route_generator import generate_plan
from spray_command_mapper import build_spray_commands

class TestDroneSawitPipeline(unittest.TestCase):
    def test_ai_output_loader(self):
        trees = load_ai_predictions()
        self.assertIsInstance(trees, list)
        self.assertGreater(len(trees), 0)
    def test_route_generation(self):
        trees = load_ai_predictions()
        generate_plan(trees, output_file="test_route.plan")
        self.assertTrue(os.path.exists("test_route.plan"))
    def test_spray_command_mapper(self):
        trees = load_ai_predictions()
        build_spray_commands(trees, dosage_file="pollen_dosage_table.csv")
        self.assertTrue(os.path.exists("spray_commands_linked.csv"))

if __name__ == "__main__":
    unittest.main()
