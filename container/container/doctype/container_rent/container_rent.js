frappe.ui.form.on("Container Rent", {
	setup(frm) {
		frm.set_query("supervisor", () => ({
			filters: { designation: "Supervisor" },
		}));
		frm.set_query("container_number",function(){
			return {
				filters:{
					status: "Empty"
				}
			}
		})
	},

	refresh(frm) {
		bind_rental_current_location(frm);
		
		if (!frm.is_new() && frm.doc.docstatus !== 2 && frappe.model.can_create("Sales Invoice")) {
			frm.add_custom_button(__("Sales Invoice"), async () => {
				if (frm.is_dirty()) {
					frappe.msgprint(__("Please save the rental before creating an invoice."));
					return;
				}
				const response = await frappe.call({
					method: "container.workflows.create_sales_invoice_from_container_rent",
					args: { source_name: frm.doc.name },
					freeze: true,
					freeze_message: __("Creating Sales Invoice…"),
				});
				if (response.message) frappe.set_route("Form", "Sales Invoice", response.message);
			}, __("Create"));
		}
		if (!frm.is_new() && frm.doc.docstatus !== 2 && frm.doc.container_number
			&& frappe.model.can_create("Pull Container")) {
			frm.add_custom_button(__("Pull Container"), () => {
				frappe.model.open_mapped_doc({
					method: "container.workflows.make_pull_from_container_rent",
					frm,
				});
			}, __("Create"));
		}
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Container Trip"), () => {
				frappe.model.open_mapped_doc({
					method: "container.workflows.make_trip_from_container_rent",
					frm,
				});
			}, __("Create"));
		}
	},

	from(frm) {
		return frm.set_value("to", frm.doc.from ? frappe.datetime.add_days(frm.doc.from, 10) : null);
	},

	container_number(frm) {
		console.log("Container field changed");
		console.log("Selected:", frm.doc.container_number);
	},

	location(frm) {
		let latitude = null;
		let longitude = null;
		try {
			const location = typeof frm.doc.location === "string"
				? JSON.parse(frm.doc.location || "null") : frm.doc.location;
			const geometry = location?.type === "FeatureCollection"
				? location.features?.find((feature) => feature.geometry?.type === "Point")?.geometry
				: location?.type === "Feature" ? location.geometry : location;
			if (geometry?.type === "Point") {
				const [lng, lat] = geometry.coordinates || [];
				if (Number.isFinite(lat) && Number.isFinite(lng)
					&& Math.abs(lat) <= 90 && Math.abs(lng) <= 180) {
					latitude = lat;
					longitude = lng;
				}
			}
		} catch (error) {
			console.error("Error reading location:", error);
		}
		return frm.set_value({ latitude, longitude });
	},
	onload(frm) {
        set_default_commissions(frm);
    }
});

function bind_rental_current_location(frm) {
	const field = frm.fields_dict.location;
	if (!field || field._rental_location_bound) return;
	field._rental_location_bound = true;
	const bind_map = () => {
		const map = field.map;
		if (!map || map._rental_location_bound) return;
		map._rental_location_bound = true;
		map.on("locationfound", async ({ latlng }) => {
			if (frm.doc.docstatus !== 0 || field.df.read_only || field.disabled) return;
			if (!Number.isFinite(latlng?.lat) || !Number.isFinite(latlng?.lng)) return;
			// Save the located point as the rental's marker, not just the map's temporary GPS overlay.
			field.locate_control?.stop();
			await frm.set_value("location", JSON.stringify({
				type: "FeatureCollection",
				features: [{
					type: "Feature",
					properties: {},
					geometry: { type: "Point", coordinates: [latlng.lng, latlng.lat] },
				}],
			}));
		});
	};
	const make_map = field.make_map;
	field.make_map = function (...args) {
		const result = make_map.apply(this, args);
		bind_map();
		return result;
	};
	bind_map();
}

async function set_default_commissions(frm) {
    if (!frm.is_new()) return;

    const settings = await Promise.all([
        frappe.db.get_single_value("Container Settings", "enable"),
        frappe.db.get_single_value("Container Settings", "default_driver_commission"),
        frappe.db.get_single_value("Container Settings", "default_supervisor_commission")
    ]);

    const [enabled, driver_commission, supervisor_commission] = settings;

    if (!enabled) return;

    if (!frm.doc.driver_commission && driver_commission) {
        frm.set_value("driver_commission", driver_commission);
    }

    if (
        frm.doctype === "Container Rent" &&
        !frm.doc.supervisor_commission &&
        supervisor_commission
    ) {
        frm.set_value("supervisor_commission", supervisor_commission);
    }
}
