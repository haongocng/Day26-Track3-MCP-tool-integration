import sys
import os
import json
import unittest

# Thêm thư mục gốc dự án vào PYTHONPATH để import được các module trong implementation
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from implementation.mcp_server import search, insert, aggregate, database_schema, table_schema

class TestMCPServer(unittest.TestCase):
    
    def test_01_search_cohort(self):
        print("Running: test_01_search_cohort")
        res = search(table="students", filters={"cohort": "A1"})
        data = json.loads(res)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)
        names = {row["name"] for row in data}
        self.assertIn("Alice Nguyen", names)
        self.assertIn("Bob Tran", names)

    def test_02_search_invalid_table(self):
        print("Running: test_02_search_invalid_table")
        res = search(table="ghost_table")
        self.assertTrue(res.startswith("Validation Error:"))

    def test_03_insert_success(self):
        print("Running: test_03_insert_success")
        res = insert(table="courses", values={"title": "Chemistry"})
        data = json.loads(res)
        self.assertIn("id", data)
        self.assertEqual(data["title"], "Chemistry")

    def test_04_insert_empty_payload(self):
        print("Running: test_04_insert_empty_payload")
        res = insert(table="students", values={})
        self.assertTrue(res.startswith("Validation Error:"))

    def test_05_aggregate_average_score(self):
        print("Running: test_05_aggregate_average_score")
        res = aggregate(table="enrollments", metric="avg", column="score", filters={"course_id": 2})
        data = json.loads(res)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertAlmostEqual(data[0]["value"], 85.25)

    def test_06_aggregate_invalid_metric(self):
        print("Running: test_06_aggregate_invalid_metric")
        res = aggregate(table="students", metric="invalid_metric")
        self.assertTrue(res.startswith("Validation Error:"))

    def test_07_database_schema_resource(self):
        print("Running: test_07_database_schema_resource")
        res = database_schema()
        data = json.loads(res)
        self.assertIn("students", data)
        self.assertIn("courses", data)
        self.assertIn("enrollments", data)

    def test_08_table_schema_resource(self):
        print("Running: test_08_table_schema_resource")
        res = table_schema(table_name="students")
        data = json.loads(res)
        self.assertIsInstance(data, list)
        col_names = {col["name"] for col in data}
        self.assertEqual(col_names, {"id", "name", "cohort"})

if __name__ == "__main__":
    unittest.main()
