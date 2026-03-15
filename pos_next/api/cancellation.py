"""
Order Cancellation API
Handles order cancellations with reason tracking
"""
import frappe
from frappe import _
from datetime import datetime


@frappe.whitelist()
def cancel_order_with_reason(invoice_name=None, items=None, reason=None, reason_text=None, custom_note=None):
    """
    Cancel order with reason tracking
    
    Args:
        invoice_name: POS Invoice name (optional if cart only)
        items: List of cancelled items with details
        reason: Cancellation reason code
        reason_text: Human readable reason
        custom_note: Custom cancellation note
    
    Returns:
        dict: Cancellation result
    """
    try:
        # Validate inputs
        if not items:
            return {"success": False, "error": "No items provided"}
        
        if not reason:
            return {"success": False, "error": "Cancellation reason required"}
        
        # Create cancellation log
        cancellation_doc = frappe.get_doc({
            "doctype": "POS Order Cancellation",
            "posting_date": datetime.now(),
            "user": frappe.session.user,
            "pos_invoice": invoice_name,
            "reason": reason,
            "reason_text": reason_text,
            "custom_note": custom_note,
            "items": []
        })
        
        # Add cancelled items
        for item in items:
            cancellation_doc.append("items", {
                "item_code": item.get("item_code"),
                "item_name": item.get("item_name"),
                "quantity": item.get("quantity"),
                "rate": item.get("rate", 0),
                "amount": item.get("amount", 0)
            })
        
        cancellation_doc.insert(ignore_permissions=True)
        
        # If invoice exists, update its status
        if invoice_name and frappe.db.exists("POS Invoice", invoice_name):
            invoice = frappe.get_doc("POS Invoice", invoice_name)
            invoice.add_comment("Comment", f"Order cancelled. Reason: {reason_text}. Note: {custom_note or 'N/A'}")
            
            # Optionally cancel the invoice
            if invoice.docstatus == 1:
                invoice.cancel()
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": "Order cancelled successfully",
            "cancellation_id": cancellation_doc.name
        }
        
    except Exception as e:
        frappe.log_error(f"Order cancellation failed: {str(e)}", "POS Cancellation")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_cancellation_reasons():
    """Get predefined cancellation reasons"""
    return [
        {"value": "customer_changed_mind", "label": _("Customer changed mind")},
        {"value": "wrong_item_ordered", "label": _("Wrong item ordered")},
        {"value": "item_out_of_stock", "label": _("Item out of stock")},
        {"value": "long_preparation_time", "label": _("Long preparation time")},
        {"value": "kitchen_mistake", "label": _("Kitchen mistake")},
        {"value": "quality_issue", "label": _("Quality issue")},
        {"value": "other", "label": _("Other Reason")}
    ]


@frappe.whitelist()
def get_cancellation_history(start_date=None, end_date=None, pos_profile=None, limit=50):
    """
    Get cancellation history for reporting
    
    Args:
        start_date: Filter from date
        end_date: Filter to date
        pos_profile: Filter by POS Profile
        limit: Maximum records to return
    """
    try:
        filters = {}
        if start_date:
            filters["posting_date"] = [">=", start_date]
        if end_date:
            filters["posting_date"] = ["<=", end_date]
        
        cancellations = frappe.get_all(
            "POS Order Cancellation",
            filters=filters,
            fields=["name", "posting_date", "user", "pos_invoice", "reason", "reason_text", "total_amount"],
            order_by="posting_date desc",
            limit=limit
        )
        
        return {
            "success": True,
            "cancellations": cancellations
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
