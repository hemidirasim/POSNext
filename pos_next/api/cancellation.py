"""
Order Cancellation API - Integrated with POS Invoice
"""
import frappe
from frappe import _
from datetime import datetime


@frappe.whitelist()
def cancel_pos_invoice(invoice_name, reason, reason_text=None, custom_note=None, table=None):
    """
    Cancel POS Invoice with reason tracking
    Updates invoice status to 'Cancelled' and logs reason
    """
    try:
        if not frappe.db.exists("POS Invoice", invoice_name):
            return {"success": False, "error": "Invoice not found"}
        
        invoice = frappe.get_doc("POS Invoice", invoice_name)
        
        # Check if already cancelled
        if invoice.status == "Cancelled":
            return {"success": False, "error": "Invoice already cancelled"}
        
        # Update invoice
        invoice.status = "Cancelled"
        invoice.cancel_reason = reason
        invoice.cancel_reason_text = reason_text or get_reason_label(reason)
        invoice.cancel_note = custom_note
        invoice.cancelled_by = frappe.session.user
        invoice.cancelled_at = datetime.now()
        
        # If restaurant table, update table status
        if table:
            invoice.restaurant_table = table
            update_table_status(table, "Available")
        
        # Add to comments for history
        comment_text = f"""
        <b>Order Cancelled</b><br>
        Reason: {invoice.cancel_reason_text}<br>
        Cancelled By: {frappe.session.user}<br>
        Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}<br>
        """
        if custom_note:
            comment_text += f"Note: {custom_note}<br>"
        
        invoice.add_comment("Comment", comment_text)
        
        # Save changes
        invoice.save(ignore_permissions=True)
        
        # Create activity log for tracking
        create_cancellation_log(invoice, reason, reason_text, custom_note)
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": "Order cancelled successfully",
            "invoice": invoice_name
        }
        
    except Exception as e:
        frappe.log_error(f"Cancel invoice failed: {str(e)}", "POS Cancellation")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def cancel_cart_items(items, reason, reason_text=None, custom_note=None, 
                       pos_profile=None, customer=None, table=None):
    """
    Cancel items from cart (before creating invoice)
    Logs cancellation without creating invoice (no POS Opening Entry required)
    """
    try:
        if not items:
            return {"success": False, "error": "No items to cancel"}
        
        # Calculate totals
        total_qty = sum(item.get("quantity", 1) for item in items)
        total_amount = sum(item.get("amount", 0) for item in items)
        
        # Create activity log for tracking (no invoice needed)
        log_doc = frappe.get_doc({
            "doctype": "Activity Log",
            "subject": f"Cart Cancelled - {len(items)} items",
            "operation": "Cancel",
            "status": "Success",
            "reference_type": "POS Profile",
            "reference_name": pos_profile or "General",
            "communication_date": datetime.now(),
            "user": frappe.session.user,
            "notes": f"""
                <b>Cart Cancelled (Before Checkout)</b><br>
                Reason: {reason_text or get_reason_label(reason)}<br>
                Reason Code: {reason}<br>
                Items Count: {len(items)}<br>
                Total Quantity: {total_qty}<br>
                Total Amount: {total_amount}<br>
                Customer: {customer or 'Walking Customer'}<br>
                Table: {table or 'N/A'}<br>
                Cancelled By: {frappe.session.user}<br>
                Note: {custom_note or 'N/A'}
            """
        })
        log_doc.insert(ignore_permissions=True)
        
        # Also create a comment on POS Profile for quick reference
        if pos_profile and frappe.db.exists("POS Profile", pos_profile):
            pos_doc = frappe.get_doc("POS Profile", pos_profile)
            comment = f"""
            <b>Cart Cancelled</b><br>
            Reason: {reason_text or get_reason_label(reason)}<br>
            Items: {len(items)} | Qty: {total_qty} | Amount: {total_amount}<br>
            By: {frappe.session.user} at {datetime.now().strftime('%Y-%m-%d %H:%M')}
            """
            if custom_note:
                comment += f"<br>Note: {custom_note}"
            pos_doc.add_comment("Comment", comment)
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": "Cart cancelled successfully",
            "log_id": log_doc.name
        }
        
    except Exception as e:
        frappe.log_error(f"Cancel cart failed: {str(e)}", "POS Cancellation")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_reason_label(reason_code):
    """Get human readable label for reason code"""
    reason_map = {
        "customer_changed_mind": _("Customer changed mind"),
        "wrong_item_ordered": _("Wrong item ordered"),
        "item_out_of_stock": _("Item out of stock"),
        "long_preparation_time": _("Long preparation time"),
        "kitchen_mistake": _("Kitchen mistake"),
        "quality_issue": _("Quality issue"),
        "other": _("Other Reason")
    }
    return reason_map.get(reason_code, reason_code)


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
def get_cancelled_invoices(start_date=None, end_date=None, pos_profile=None, 
                           reason=None, limit=50):
    """
    Get list of cancelled invoices for reporting
    """
    try:
        filters = {
            "status": "Cancelled",
            "is_pos": 1
        }
        
        if start_date:
            filters["posting_date"] = [">=", start_date]
        if end_date:
            filters["posting_date"] = ["<=", end_date]
        if pos_profile:
            filters["pos_profile"] = pos_profile
        if reason:
            filters["cancel_reason"] = reason
        
        invoices = frappe.get_all(
            "POS Invoice",
            filters=filters,
            fields=[
                "name", "posting_date", "posting_time", 
                "customer", "grand_total", "status",
                "cancel_reason", "cancel_reason_text", 
                "cancelled_by", "cancelled_at",
                "restaurant_table", "pos_profile"
            ],
            order_by="posting_date desc, posting_time desc",
            limit=limit
        )
        
        return {
            "success": True,
            "invoices": invoices,
            "count": len(invoices)
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_cancellation_log(invoice, reason, reason_text, custom_note):
    """Create activity log for cancellation"""
    try:
        frappe.get_doc({
            "doctype": "Activity Log",
            "subject": f"POS Invoice {invoice.name} Cancelled",
            "reference_type": "POS Invoice",
            "reference_name": invoice.name,
            "operation": "Cancel",
            "status": "Success",
            "communication_date": datetime.now(),
            "notes": f"""
                Reason: {reason_text or reason}
                Note: {custom_note or 'N/A'}
                Cancelled By: {frappe.session.user}
            """
        }).insert(ignore_permissions=True)
    except:
        pass


def update_table_status(table, status):
    """Update restaurant table status"""
    try:
        if table and frappe.db.exists("Restaurant Table", table):
            frappe.db.set_value("Restaurant Table", table, "status", status)
    except:
        pass
