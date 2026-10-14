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
});
