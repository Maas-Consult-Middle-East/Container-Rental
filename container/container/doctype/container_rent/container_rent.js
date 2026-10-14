frappe.ui.form.on("Container Rent", {
	setup(frm) {
		frm.set_query("supervisor", () => ({
			filters: { designation: "Supervisor" },
		}));
		frm.set_query("container_number",function(){
			return {
				filters:{
					status: "Empty"
				}
			}
		})
	},

	refresh(frm) {
		if (!frm.is_new() && frm.doc.docstatus !== 2 && frappe.model.can_create("Sales Invoice")) {
			frm.add_custom_button(__("Sales Invoice"), async () => {
				if (frm.is_dirty()) {
					frappe.msgprint(__("Please save the rental before creating an invoice."));
					return;
				}
				const response = await frappe.call({
					method: "container.workflows.create_sales_invoice_from_container_rent",
					args: { source_name: frm.doc.name },
					freeze: true,
					freeze_message: __("Creating Sales Invoice…"),
				});
				if (response.message) frappe.set_route("Form", "Sales Invoice", response.message);
			}, __("Create"));
		}
		if (!frm.is_new() && frm.doc.docstatus !== 2 && frm.doc.container_number
			&& frappe.model.can_create("Pull Container")) {
			frm.add_custom_button(__("Pull Container"), () => {
				frappe.model.open_mapped_doc({
					method: "container.workflows.make_pull_from_container_rent",
					frm,
				});
			}, __("Create"));
		}
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Container Trip"), () => {
				frappe.model.open_mapped_doc({
					method: "container.workflows.make_trip_from_container_rent",
					frm,
				});
			}, __("Create"));
		}
	},

	container_number(frm) {
		console.log("Container field changed");
		console.log("Selected:", frm.doc.container_number);
	},

	location(frm) {
        if (frm.doc.location) {
            try {
                let location = JSON.parse(frm.doc.location);

                if (location.features && location.features.length > 0) {
                    let coordinates = location.features[0].geometry.coordinates;

                    frm.set_value('longitude', coordinates[0]);
                    frm.set_value('latitude', coordinates[1]);
                }
            } catch (error) {
                console.error("Error reading location:", error);
            }
        }
    }
});
