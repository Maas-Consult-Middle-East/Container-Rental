frappe.ui.form.on("Container Trip", {
	setup(frm) {
		frm.set_query("supervisor", () => ({
			filters: { designation: "Supervisor" },
		}));
	},

	refresh(frm) {
		if (frm.doc.docstatus !== 1) return;

		if (frm.doc.driver && flt(frm.doc.driver_commission) > 0) {
			frm.add_custom_button(__("Driver Commission"), () => {
				frappe.model.open_mapped_doc({
					method: "container.workflows.make_driver_commission",
					frm,
				});
			}, __("Create"));
		}
		if (frm.doc.supervisor && flt(frm.doc.supervisor_commission) > 0) {
			frm.add_custom_button(__("Supervisor Commission"), () => {
				frappe.model.open_mapped_doc({
					method: "container.workflows.make_supervisor_commission",
					frm,
				});
			}, __("Create"));
		}
	},
});
