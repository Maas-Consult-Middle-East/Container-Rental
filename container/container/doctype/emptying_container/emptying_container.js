frappe.ui.form.on("Emptying Container", {
	setup(frm) {
		frm.set_query("container", () => ({
			filters: { status: "Pull" },
		}));
		frm.set_query("supervisor", () => ({
			filters: { designation: "Supervisor" },
		}));
	},

	refresh(frm) {
		frm.set_df_property("container", "read_only", !frm.is_new());
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