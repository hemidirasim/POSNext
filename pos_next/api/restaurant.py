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
