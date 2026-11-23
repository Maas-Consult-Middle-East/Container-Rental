frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		if (frm.doc.docstatus !== 0 || frm.doc.is_return || !frm.perm?.[0]?.write) return;
		for (const [doctype, customer_field] of [["Rent A Container", "client"], ["Container Contract", "customer"]]) {
			if (!frappe.model.can_read(doctype)) continue;
			frm.add_custom_button(__(doctype), () => {
				frappe.prompt({
					fieldname: "source", label: __(doctype), fieldtype: "Link", options: doctype, reqd: 1,
					get_query: () => ({ filters: {
						docstatus: 1,
						...(frm.doc.customer ? { [customer_field]: frm.doc.customer } : {}),
					} }),
				}, async ({ source }) => {
					const response = await frappe.call({
						method: "container.workflows.fetch_container_invoice_items",
						args: { source_doctype: doctype, source_name: source, target_doc: frm.doc },
						freeze: true, freeze_message: __("Fetching items…"),
					});
					if (response.message) {
						frappe.model.sync(response.message);
						frm.dirty();
						frm.refresh();
					}
				}, __("Get Items From"), __("Get Items"));
			}, __("Get Items From"));
		}
	},
});
