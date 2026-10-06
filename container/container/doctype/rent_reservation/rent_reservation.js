frappe.ui.form.on('Rent Reservation', {
    refresh(frm) {
        if (frm.doc.docstatus !== 1 || !['Reserved', 'Confirmed'].includes(frm.doc.status)) return;
        for (const status of ['Confirmed', 'Completed']) {
            if (frm.doc.status !== status) {
                frm.add_custom_button(__(status), () => {
                    frm.call('set_reservation_status', {status}).then(() => frm.reload_doc());
                });
            }
        }
    }
});
