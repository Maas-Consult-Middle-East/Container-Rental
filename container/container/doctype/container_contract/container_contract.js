
frappe.ui.form.on("Container Contract", {
    refresh(frm) {
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__("Rent A Container"), async () => {
                const doc = await frappe.model.with_doctype("Rent A Container");

                const new_doc = frappe.model.get_new_doc("Rent A Container");

                new_doc.container_contract = frm.doc.name;
                new_doc.client = frm.doc.customer;
                new_doc.from = frm.doc.contract_from;
                new_doc.supervisor = frm.doc.supervisor;
                new_doc.classification = frm.doc.classification;

                frappe.set_route("Form", "Rent A Container", new_doc.name);
            }, __("Create"));
        }
    }
});
