import unittest
from unittest.mock import patch

import frappe

from container.patches.convert_classification_to_select import execute, normalize_size


class TestClassificationMigration(unittest.TestCase):
	def test_supported_sizes_and_units(self):
		for value, expected in [("12", "12"), ("20 Yard", "20"), ("20 ياردة", "20"),
			("١٢ ياردة", "12"), (None, ""), ("", "")]:
			self.assertEqual(normalize_size(value), expected)

	def test_unknown_or_ambiguous_values_are_not_guessed(self):
		for value in ["Trash", "Rubble", "30 Yard", "12/20", "120", "Container 20"]:
			self.assertIsNone(normalize_size(value))

	def test_unknown_value_prevents_all_updates(self):
		def records(doctype, **kwargs):
			if doctype == "Container":
				return [frappe._dict(name="known", classification="20 Yard"),
					frappe._dict(name="unknown", classification="Rubble")]
			return []

		with patch("frappe.get_all", side_effect=records), \
			patch.object(frappe.db, "table_exists", return_value=True), \
			patch.object(frappe.db, "has_column", return_value=True), \
			patch.object(frappe.db, "set_value") as write:
			with self.assertRaises(frappe.ValidationError):
				execute()
			write.assert_not_called()
