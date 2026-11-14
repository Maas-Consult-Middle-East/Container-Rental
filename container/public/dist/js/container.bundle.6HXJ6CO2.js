(() => {
  // ../container/container/public/js/container.bundle.js
  frappe.provide("container.utils");
  container.utils.open_mapped_doc_for_container = function(frm, method) {
    const containers = (frm.doc.containers || []).map((row) => row.container).filter(Boolean);
    const open = (container2) => frappe.model.open_mapped_doc({ method, frm, args: { container: container2 } });
    if (containers.length === 1)
      return open(containers[0]);
    frappe.prompt(
      { fieldname: "container", fieldtype: "Select", label: __("Container"), options: containers, reqd: 1 },
      (values) => open(values.container),
      __("Select Container")
    );
  };
})();
//# sourceMappingURL=container.bundle.6HXJ6CO2.js.map
