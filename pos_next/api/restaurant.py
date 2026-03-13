# -*- coding: utf-8 -*-
# Copyright (c) 2025, BrainWise and contributors
# For license information, please see license.txt

"""
POS Next Restaurant API
Handles table management, areas, and restaurant operations
"""

import frappe
from frappe import _


@frappe.whitelist()
def get_tables():
    """
    Get all restaurant tables and areas for the current POS Profile.
    
    Returns:
        dict: { areas: [...], tables: [...] }
    """
    try:
        # Get all restaurant areas
        areas = frappe.get_all(
            "Restaurant Area",
            fields=["name", "area_name", "description"],
            order_by="area_name"
        )
        
        # Get all restaurant tables
        tables = frappe.get_all(
            "Restaurant Table",
            fields=["name", "table_name", "area", "capacity", "status"],
            order_by="table_name"
        )
        
        return {
            "areas": areas or [],
            "tables": tables or []
        }
        
    except Exception as e:
        frappe.log_error(f"Failed to get restaurant tables: {str(e)}")
        return {
            "areas": [],
            "tables": [],
            "error": str(e)
        }


@frappe.whitelist()
def update_table_status(table_name, status):
    """
    Update the status of a restaurant table.
    
    Args:
        table_name: Restaurant Table name
        status: New status (Empty, Occupied, Reserved, Cleaning)
    
    Returns:
        dict: { success: bool, message: str }
    """
    try:
        if not table_name:
            frappe.throw(_("Table name is required"))
        
        if status not in ["Empty", "Occupied", "Reserved", "Cleaning"]:
            frappe.throw(_("Invalid status"))
        
        # Check if user has permission
        if not frappe.has_permission("Restaurant Table", "write", table_name):
            frappe.throw(_("You don't have permission to update this table"))
        
        # Update table status
        frappe.db.set_value("Restaurant Table", table_name, "status", status)
        
        return {
            "success": True,
            "message": _("Table status updated to {0}").format(status)
        }
        
    except Exception as e:
        frappe.log_error(f"Failed to update table status: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def get_table_orders(table_name):
    """
    Get active orders for a specific table.
    
    Args:
        table_name: Restaurant Table name
    
    Returns:
        list: Active orders for the table
    """
    try:
        if not table_name:
            return []
        
        # Get active POS invoices for this table
        orders = frappe.get_all(
            "POS Invoice",
            fields=["name", "customer", "grand_total", "posting_time"],
            filters={
                "restaurant_table": table_name,
                "docstatus": 0,  # Draft invoices
                "status": ["!=", "Paid"]
            },
            order_by="posting_time desc"
        )
        
        return orders or []
        
    except Exception as e:
        frappe.log_error(f"Failed to get table orders: {str(e)}")
        return []


@frappe.whitelist()
def get_kds_orders():
    """
    Get active kitchen display orders (KDS).
    Returns draft POS invoices with restaurant_table set and kds_status not completed.
    
    Returns:
        list: Active orders for kitchen display
    """
    try:
        # DEBUG: Log all POS Invoices with restaurant_table
        all_with_table = frappe.get_all(
            "POS Invoice",
            fields=["name", "restaurant_table", "kds_status", "docstatus"],
            filters={"restaurant_table": ["is", "set"]}
        )
        
        # Get active orders from POS Invoice
        orders = frappe.get_all(
            "POS Invoice",
            fields=[
                "name", "customer", "customer_name", "restaurant_table",
                "kds_status", "creation", "modified", "grand_total",
                "posting_date", "posting_time"
            ],
            filters={
                "docstatus": 0,  # Draft invoices only
                "restaurant_table": ["is", "set"],  # Must have a table
                "kds_status": ["in", ["Pending", "Preparing", "Ready"]]  # Active KDS statuses
            },
            order_by="creation asc"  # Oldest first
        )
        
        
        # Get items for each order
        for order in orders:
            order.items = frappe.get_all(
                "POS Invoice Item",
                fields=["item_code", "item_name", "qty", "description", "posa_special_instructions"],
                filters={"parent": order.name}
            )
            # Get table name
            if order.restaurant_table:
                table = frappe.db.get_value("Restaurant Table", order.restaurant_table, "table_name", as_dict=True)
                if table:
                    order.restaurant_table = table.table_name
        
        return orders or []
        
    except Exception as e:
        frappe.log_error(f"Failed to get KDS orders: {str(e)}")
        return []


@frappe.whitelist()
def update_kds_status(invoice_name, status):
    """
    Update KDS status of a POS Invoice.
    
    Args:
        invoice_name: POS Invoice name
        status: New KDS status (Pending, Preparing, Ready, Delivered)
    
    Returns:
        dict: { success: bool, message: str }
    """
    try:
        if not invoice_name:
            frappe.throw(_("Invoice name is required"))
        
        valid_statuses = ["Pending", "Preparing", "Ready", "Delivered"]
        if status not in valid_statuses:
            frappe.throw(_("Invalid KDS status. Must be one of: {0}").format(", ".join(valid_statuses)))
        
        # Check if user has permission
        if not frappe.has_permission("POS Invoice", "write", invoice_name):
            frappe.throw(_("You don't have permission to update this invoice"))
        
        # Update KDS status
        frappe.db.set_value("POS Invoice", invoice_name, "kds_status", status)
        
        # Emit realtime event to all connected KDS displays
        frappe.publish_realtime(
            event="kds_status_update",
            message={
                "order_id": invoice_name,
                "status": status,
                "timestamp": frappe.utils.now()
            },
            room="kds_room"
        )
        
        # If status is Delivered, emit completion event
        if status == "Delivered":
            frappe.publish_realtime(
                event="kds_order_completed",
                message={
                    "order_id": invoice_name,
                    "timestamp": frappe.utils.now()
                },
                room="kds_room"
            )
        
        return {
            "success": True,
            "message": _("Order status updated to {0}").format(status)
        }
        
    except Exception as e:
        frappe.log_error(f"Failed to update KDS status: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
@frappe.whitelist()
def send_to_kitchen(order_data=None):
    """
    Send order items to kitchen (KDS).
    Only sends notification to KDS, does NOT create POS Invoice.
    Invoice will be created at checkout.
    """
    try:
        if not order_data:
            return {"success": False, "message": "Order data required"}
        
        if isinstance(order_data, str):
            import json
            order_data = json.loads(order_data)
        
        table_name = order_data.get("table_id")
        items = order_data.get("items", [])
        
        if not table_name or not items:
            return {"success": False, "message": "Table and items required"}
        
        # Build KDS items
        kds_items = []
        for item in items:
            kds_items.append({
                "item_code": item.get("item_code"),
                "item_name": item.get("item_name"),
                "qty": item.get("quantity"),
                "instructions": item.get("special_instructions", "")
            })
        
        # Generate order ID
        order_id = f"KDS-{table_name}-{frappe.utils.now_datetime().strftime('%H%M%S')}"
        
        # Send to KDS
        message_data = {
            "order_id": order_id,
            "table": order_data.get("table_name", table_name),
            "items": kds_items,
            "timestamp": frappe.utils.now()
        }
        
        # Send to KDS - broadcast to all connected clients (no room)
        try:
            frappe.publish_realtime(
                event="kds_new_order",
                message=message_data
            )
        except Exception as e:
            frappe.log_error(f"KDS publish error: {str(e)[:200]}")
        
        return {"success": True, "message": "Order sent to kitchen"}
        
    except Exception as e:
        return {"success": False, "message": str(e)[:200]}
def notify_kds_new_order(invoice_name):
    """
    Notify KDS displays about a new order.
    Called when a new order is created with restaurant_table.
    
    Args:
        invoice_name: POS Invoice name
    """
    try:
        if not invoice_name:
            return
        
        # Get order details
        order = frappe.get_doc("POS Invoice", invoice_name)
        
        # Only notify if it has a restaurant table
        if not order.restaurant_table:
            return
        
        # Emit realtime event
        frappe.publish_realtime(
            event="kds_new_order",
            message={
                "order_id": invoice_name,
                "table": order.restaurant_table,
                "items_count": len(order.items),
                "timestamp": frappe.utils.now()
            },
            room="kds_room"
        )
        
    except Exception as e:
        frappe.log_error(f"Failed to notify KDS: {str(e)}")


@frappe.whitelist(allow_guest=True)
def get_cfd_order(order_id):
    """
    Get order status for Customer Facing Display (CFD).
    This endpoint allows guest access for customer displays.
    
    Args:
        order_id: POS Invoice name
    
    Returns:
        dict: Order details with status
    """
    try:
        if not order_id:
            return None
        
        # Get order details
        order = frappe.get_all(
            "POS Invoice",
            fields=[
                "name", "customer_name", "restaurant_table", "kds_status",
                "creation", "modified", "grand_total"
            ],
            filters={
                "name": order_id,
                "docstatus": 0  # Only draft invoices
            },
            limit=1
        )
        
        if not order:
            return None
        
        order = order[0]
        
        # Get order items
        order.items = frappe.get_all(
            "POS Invoice Item",
            fields=["item_code", "item_name", "qty"],
            filters={"parent": order_id}
        )
        
        # Get table name
        if order.restaurant_table:
            table = frappe.db.get_value("Restaurant Table", order.restaurant_table, "table_name", as_dict=True)
            if table:
                order.restaurant_table = table.table_name
        
        return order
        
    except Exception as e:
        frappe.log_error(f"Failed to get CFD order: {str(e)}")
        return None
