frappe.ui.form.on("Pull Container", {
	setup(frm) {
		frm.set_query("container", "containers", (doc) => ({
			filters: {
				status: ["in", ["Rented", "Late"]],
				name: ["not in", (doc.containers || []).map((row) => row.container).filter(Boolean)],
			},
		}));
		frm.set_query("supervisor", () => ({
			filters: { designation: "Supervisor" },
		}));
	},

	refresh(frm) {
		frm.set_df_property("containers", "read_only", !frm.is_new());
		if (!frm.is_new() && frm.doc.docstatus !== 2
			&& frappe.model.can_create("Emptying Container")) {
			frm.add_custom_button(__("Emptying Container"), () => {
				container.utils.open_mapped_doc_for_container(frm, "container.workflows.make_emptying_from_pull_container");
			}, __("Create"));
		}
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Container Trip"), () => {
				container.utils.open_mapped_doc_for_container(frm, "container.workflows.make_trip_from_pull_container");
			}, __("Create"));
		}
	},
	onload(frm) {
        set_default_commissions(frm);
    }
});
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
        frm.doctype === "Rent A Container" &&
        !frm.doc.supervisor_commission &&
        supervisor_commission
    ) {
        frm.set_value("supervisor_commission", supervisor_commission);
    }
}
