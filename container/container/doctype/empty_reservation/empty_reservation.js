frappe.ui.form.on("Empty Reservation", {
	setup(frm) {
		frm.set_query("supervisor", () => ({
			filters: { designation: "Supervisor" },
		}));
	},
});
