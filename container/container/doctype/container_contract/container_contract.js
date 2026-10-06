frappe.ui.form.on('Container Contract', {
    refresh(frm) {
        if (frm.doc.docstatus === 1 && frm.doc.status === 'Active') {
            if (frappe.model.can_create('Sales Invoice')) {
                frm.add_custom_button(__('Create Sales Invoice'), () => {
                    frappe.call({method: 'container.billing.make_invoice', args: {contract: frm.doc.name}, freeze: true,
                        callback(r) { if (r.message) frappe.set_route('Form', 'Sales Invoice', r.message); }});
                });
            }
            if (frappe.user.has_role('Container Manager')) {
                frm.add_custom_button(__('Complete Contract'), () => frm.call('complete').then(() => frm.reload_doc()));
            }
        }
    }
});
