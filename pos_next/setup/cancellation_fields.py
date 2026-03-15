"""
Add custom fields to POS Invoice for cancellation tracking
"""
import frappe


def add_cancellation_fields():
    """Add cancellation tracking fields to POS Invoice"""
    
    fields = [
        {
            "fieldname": "cancellation_section",
            "label": "Cancellation Details",
            "fieldtype": "Section Break",
            "insert_after": "status",
            "depends_on": "eval:doc.status=='Cancelled'",
            "collapsible": 1
        },
        {
            "fieldname": "cancel_reason",
            "label": "Cancellation Reason Code",
            "fieldtype": "Select",
            "options": "\ncustomer_changed_mind\nwrong_item_ordered\nitem_out_of_stock\nlong_preparation_time\nkitchen_mistake\nquality_issue\nother",
            "insert_after": "cancellation_section",
            "depends_on": "eval:doc.status=='Cancelled'",
            "read_only": 1
        },
        {
            "fieldname": "cancel_reason_text",
            "label": "Cancellation Reason",
            "fieldtype": "Data",
            "insert_after": "cancel_reason",
            "depends_on": "eval:doc.status=='Cancelled'",
            "read_only": 1
        },
        {
            "fieldname": "cancel_note",
            "label": "Cancellation Note",
            "fieldtype": "Text",
            "insert_after": "cancel_reason_text",
            "depends_on": "eval:doc.status=='Cancelled'",
            "read_only": 1
        },
        {
            "fieldname": "cancelled_by",
            "label": "Cancelled By",
            "fieldtype": "Link",
            "options": "User",
            "insert_after": "cancel_note",
            "depends_on": "eval:doc.status=='Cancelled'",
            "read_only": 1
        },
        {
            "fieldname": "cancelled_at",
            "label": "Cancelled At",
            "fieldtype": "Datetime",
            "insert_after": "cancelled_by",
            "depends_on": "eval:doc.status=='Cancelled'",
            "read_only": 1
        }
    ]
    
    for field in fields:
        try:
            if not frappe.db.exists("Custom Field", f"POS Invoice-{field['fieldname']}"):
                frappe.get_doc({
                    "doctype": "Custom Field",
                    "dt": "POS Invoice",
                    **field
                }).insert()
                print(f"✅ Field {field['fieldname']} added")
        except Exception as e:
            print(f"⚠️ Field {field['fieldname']}: {e}")
    
    frappe.db.commit()
    print("✅ Cancellation fields added to POS Invoice")
