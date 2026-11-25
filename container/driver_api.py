"""Driver-scoped job lists for the container driver mobile app.

The driver is always resolved from the session user on the server, so a driver
can only ever receive documents where their own Driver record is selected.
"""

import json

import frappe
from frappe import _

from container.availability import active_container_operations


def session_drivers():
	"""Active Driver records whose Employee is linked to the logged-in user."""
	employees = frappe.get_all("Employee", filters={"user_id": frappe.session.user}, pluck="name")
	drivers = (
		frappe.get_all("Driver", filters={"employee": ["in", employees], "status": "Active"}, pluck="name")
		if employees
		else []
	)
	if not drivers:
		frappe.throw(_("This account is not set up as a driver. Ask your administrator to link your user to an active Driver."), frappe.PermissionError)
	return drivers


@frappe.whitelist()
def get_me():
	drivers = session_drivers()
	return {"driver": drivers[0], "full_name": frappe.db.get_value("Driver", drivers[0], "full_name")}


@frappe.whitelist()
def get_deliveries():
	"""Submitted rentals for this driver that still have containers not yet pulled."""
	return _jobs("Rent A Container", "rental", ["client_name", "from", "to"])


@frappe.whitelist()
def get_pulls():
	"""Pulls for this driver that still have containers not yet emptied."""
	jobs = _jobs("Pull Container", "pull", ["client", "date"])
	customers = {job["client"] for job in jobs if job.get("client")}
	names = dict(
		frappe.get_all(
			"Customer", filters={"name": ["in", list(customers)]}, fields=["name", "customer_name"], as_list=True
		)
	) if customers else {}
	for job in jobs:
		job["client_name"] = names.get(job.pop("client"), job.get("client"))
	return jobs


def _jobs(doctype, operation, extra_fields):
	drivers = session_drivers()
	# Same definition as the dashboard cards: pulled/emptied containers are not active.
	active = {}
	for row in active_container_operations():
		if row.operation == operation:
			active.setdefault(row.source_name, []).append(row.container)
	if not active:
		return []

	docs = frappe.get_all(
		doctype,
		filters={"name": ["in", list(active)], "driver": ["in", drivers]},
		fields=["name", "contact_number", "address", "location", "latitude", "longitude", "truck", *extra_fields],
		order_by="creation desc",
		limit_page_length=0,
	)
	containers = sorted({c for doc in docs for c in active[doc.name]})
	sizes = dict(
		frappe.get_all("Container", filters={"name": ["in", containers]}, fields=["name", "container_size"], as_list=True)
	) if containers else {}

	jobs = []
	for doc in docs:
		lat, lng = _coordinates(doc)
		job = {k: v for k, v in doc.items() if k not in ("location", "latitude", "longitude")}
		job.update(
			latitude=lat,
			longitude=lng,
			containers=[{"container": c, "container_size": sizes.get(c)} for c in sorted(active[doc.name])],
		)
		jobs.append(job)
	return jobs


def _coordinates(doc):
	"""Prefer explicit latitude/longitude, fall back to the first point on the map field."""
	try:
		if doc.latitude and doc.longitude:
			return float(doc.latitude), float(doc.longitude)
	except (TypeError, ValueError):
		pass
	try:
		for feature in json.loads(doc.location or "{}").get("features", []):
			geometry = feature.get("geometry") or {}
			if geometry.get("type") == "Point":
				lng, lat = geometry["coordinates"][:2]
				return float(lat), float(lng)
	except (TypeError, ValueError, KeyError, AttributeError):
		pass
	return None, None
