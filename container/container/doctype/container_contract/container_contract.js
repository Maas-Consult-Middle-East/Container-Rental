frappe.ui.form.on('Container Contract', {
    refresh(frm) {
        if (frm.doc.docstatus === 1 && frm.doc.status === 'Active') {
            if (frappe.model.can_create('Sales Invoice')) {
                frm.add_custom_button(__('Create Sales Invoice'), () => {
                    frappe.call({method: 'container.billing.make_invoice', args: {contract: frm.doc.name}, freeze: true,
                        callback(r) { if (r.message) frappe.set_route('Form', 'Sales Invoice', r.message); }});
                });
            }
            const full_access_roles = [
                'System Manager',
                'Container Manager',
                'Container Operator',
                'Container Reports User',
                'Accounts User',
                'Accounts Manager',
                'Fleet Manager'
            ];
            if (full_access_roles.some(role => frappe.user.has_role(role))) {
                frm.add_custom_button(__('Complete Contract'), () => frm.call('complete').then(() => frm.reload_doc()));
            }
        }
    }
});
