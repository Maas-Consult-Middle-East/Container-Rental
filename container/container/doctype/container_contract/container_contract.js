frappe.ui.form.on("Container Contract", {
    setup(frm) {
        frm.set_query("supervisor", () => ({ filters: { designation: "Supervisor" } }));
    },
    refresh(frm) {
        bind_rental_current_location(frm);
        if (frm.doc.docstatus === 1 && frappe.model.can_create("Sales Invoice")) {
            frm.add_custom_button(__("Sales Invoice"), () => {
                frappe.model.open_mapped_doc({
                    method: "container.workflows.make_sales_invoice_from_container_contract",
                    frm,
                });
            }, __("Create"));
        }

    },
    contract_from(frm) {
        return frm.set_value("contract_to", frm.doc.contract_from ? frappe.datetime.add_days(frm.doc.contract_from, 10) : null);
    },
    onload(frm) { set_default_commissions(frm); },
	map_location(frm) {
		let latitude = null;
		let longitude = null;
		try {
			const location = typeof frm.doc.map_location === "string"
				? JSON.parse(frm.doc.map_location || "null") : frm.doc.map_location;
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
});

function bind_rental_current_location(frm) {
	const field = frm.fields_dict.map_location;
	if (!field || field._rental_location_bound) return;
	field._rental_location_bound = true;
	field.get_leaflet_controls = function () {
		return new L.Control.Draw({
			position: "topleft",
			draw: {
				marker: true,
				polyline: false,
				polygon: false,
				rectangle: false,
				circle: false,
				circlemarker: false,
			},
			edit: {
				featureGroup: this.editableLayers,
				edit: false,
				remove: true,
			},
		});
	};
	const bind_map = () => {
		const map = field.map;
		if (!map || map._rental_location_bound) return;
		map._rental_location_bound = true;
		if (!frm.doc.map_location) {
			map.setView([24.7136, 46.6753], 12);
		}
		if (field.draw_control) map.removeControl(field.draw_control);
		if (!field.disabled) field.bind_leaflet_draw_control();
		map.zoomControl?.remove();
		map.on("locationfound", async ({ latlng }) => {
			if (frm.doc.docstatus !== 0 || field.df.read_only || field.disabled) return;
			if (!Number.isFinite(latlng?.lat) || !Number.isFinite(latlng?.lng)) return;
			field.locate_control?.stop();
			await frm.set_value("map_location", JSON.stringify({
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
        frm.doctype === "Container Contract" &&
        !frm.doc.supervisor_commission &&
        supervisor_commission
    ) {
        frm.set_value("supervisor_commission", supervisor_commission);
    }
}
