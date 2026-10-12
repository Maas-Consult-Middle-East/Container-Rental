import unittest
from unittest.mock import patch

import frappe

from container.container.report.container_report import container_report as report


class TestContainerReport(unittest.TestCase):
	def test_map_coordinates_and_invalid_locations(self):
		self.assertEqual(report.map_url({'latitude': '0', 'longitude': '0'}),
			'https://www.google.com/maps?q=0.0,0.0')
		self.assertEqual(report.map_url({'location': '{"type":"FeatureCollection","features":[{"geometry":{"type":"Point","coordinates":[46.7,24.7]}}]}'}),
			'https://www.google.com/maps?q=24.7,46.7')
		for row in ({'latitude': 'NaN', 'longitude': 1}, {'latitude': 91, 'longitude': 1},
			{'location': 'bad json'}, {'location': '{"type":"Point","coordinates":[]}'}):
			self.assertIsNone(report.map_url(row))

	def test_dates_status_contract_total_and_customer_details(self):
		queries = []
		def get_list(doctype, **kwargs):
			queries.append((doctype, kwargs))
			if doctype == 'Cotainer Rent':
				return [frappe._dict(name='OLD', container_number='C1', client='CLIENT', driver='D1',
					contact_number='0500000000', address='Rental address', classification='20 Yard',
					**{'from': '2026-10-12 23:59:59', 'to': '2026-10-22 23:59:59'})]
			if doctype == 'Container Contract':
				return [frappe._dict(name='CON-1', customer='CLIENT', classification='20 Yard',
					contract_from='2026-10-01', contract_to='2026-10-31', total=725)]
			return [frappe._dict({
				'Customer': dict(name='CLIENT', customer_name='Client name', primary_address='Client address'),
				'Driver': dict(name='D1', full_name='Driver name'),
				'Container': dict(name='C1', status='Rented'),
			}[doctype])]
		with patch.object(report, '_', side_effect=lambda text: text), \
			patch.object(frappe, 'has_permission', return_value=True), \
			patch.object(frappe, 'get_list', side_effect=get_list):
			columns, rows = report.execute({'to_date': '2026-10-12'})
			self.assertEqual(len(columns), 12)
			self.assertEqual(rows[0]['container_status'], 'Rented')
			self.assertEqual(rows[0]['amount'], 725)
			self.assertEqual(rows[0]['driver_name'], 'Driver name')
			self.assertEqual(rows[0]['client_address'], 'Client address')
			self.assertEqual(rows[0]['address'], 'Rental address')
			self.assertIn(['from', '<', frappe.utils.getdate('2026-10-13')], queries[0][1]['filters'])
			self.assertIn(['docstatus', '!=', 2], queries[0][1]['filters'])
			self.assertEqual(report.execute({'container_status': 'Empty'})[1], [])

	def test_contract_must_cover_date_and_classification(self):
		rental = frappe._dict(client='CLIENT', classification='20 Yard', **{'from': '2026-10-12'})
		contracts = [
			frappe._dict(name='WRONG-TYPE', classification='30 Yard', contract_from='2026-10-01',
				contract_to='2026-10-31', total=1),
			frappe._dict(name='EXPIRED', classification='20 Yard', contract_from='2026-09-01',
				contract_to='2026-09-30', total=2),
			frappe._dict(name='MATCH', classification='20 Yard', contract_from='2026-10-01',
				contract_to='2026-10-31', total=3),
		]
		self.assertEqual(report.contract_for_rental(rental, contracts).name, 'MATCH')

	def test_reversed_dates_rejected_before_query(self):
		with patch.object(report, '_', side_effect=lambda text: text), \
			patch.object(frappe, 'throw', side_effect=ValueError), \
			patch.object(frappe, 'get_list') as query:
			with self.assertRaises(ValueError):
				report.execute({'from_date': '2026-10-12', 'to_date': '2026-10-01'})
			query.assert_not_called()

	def test_inaccessible_linked_records_not_read(self):
		with patch.object(frappe, 'has_permission', return_value=False), \
			patch.object(frappe, 'get_list') as query:
			self.assertEqual(report.linked_records('Customer', ['C1'], ['customer_name']), {})
			query.assert_not_called()
