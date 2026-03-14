# -*- coding: utf-8 -*-
# Copyright (c) 2025, BrainWise and contributors
# For license information, please see license.txt

"""
POS Next Restaurant API
Handles table management, areas, and restaurant operations
"""

import frappe
from frappe import _
from frappe.utils import flt


def get_mode_of_payment_account(mode_of_payment, company):
    """
    Get default account for Mode of Payment from Mode of Payment doctype.
    
    Args:
        mode_of_payment: Mode of Payment name
        company: Company name
    
    Returns:
        str: Account name or None
    """
    try:
        mop_doc = frappe.get_doc("Mode of Payment", mode_of_payment)
        for acc in mop_doc.accounts:
            if acc.company == company:
                # Try different field names for account
                # ERPNext versions may use 'default_account' or 'account'
                account = getattr(acc, 'default_account', None) or getattr(acc, 'account', None)
                if account:
                    return account
        return None
    except Exception as e:
        frappe.log_error(f"Error getting MoP account for {mode_of_payment}: {str(e)[:100]}")
        return None


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
def update_kds_status(invoice_name, status):
    """
    Update KDS status for a POS Invoice.
    
    Args:
        invoice_name: POS Invoice name
        status: New KDS status (e.g., "Pending", "Preparing", "Ready", "Served")
    
    Returns:
        dict: { success: bool, message: str }
    """
    try:
        if not invoice_name:
            return {"success": False, "message": _("Invoice name required")}
        
        if not status:
            return {"success": False, "message": _("Status required")}
        
        # Check if invoice exists
        if not frappe.db.exists("POS Invoice", invoice_name):
            return {"success": False, "message": _("Invoice not found: {0}").format(invoice_name)}
        
        invoice = frappe.get_doc("POS Invoice", invoice_name)
        
        # Update status
        invoice.kds_status = status
        
        # Save with ignore_permissions and ignore_version
        invoice.flags.ignore_permissions = True
        invoice.save(ignore_permissions=True)
        
        # Notify KDS displays about status change
        try:
            frappe.publish_realtime(
                event="kds_status_update",
                message={
                    "order_id": invoice_name,
                    "status": status,
                    "table": invoice.restaurant_table
                },
                room="kds_room"
            )
        except Exception:
            pass  # Realtime notification is not critical
        
        return {"success": True, "message": _("Status updated to {0}").format(status)}
        
    except frappe.exceptions.ValidationError as e:
        # Return validation errors clearly
        return {"success": False, "message": str(e), "error_type": "validation"}
    except Exception as e:
        frappe.log_error(f"KDS status update error: {str(e)[:200]}")
        return {"success": False, "message": str(e)}


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
def get_or_create_table_invoice(table_name, pos_profile, customer=None):
    """
    Get existing draft invoice for table or create new one.
    Implements 'Running Tab' pattern - one table = one open invoice.
    
    Args:
        table_name: Restaurant Table name
        pos_profile: POS Profile name
        customer: Customer name (optional)
    
    Returns:
        dict: { invoice_name, items: [...], is_new: bool, ... }
    """
    try:
        if not table_name:
            return {"success": False, "message": _("Table name required")}
        
        # Look for existing draft invoice for this table
        existing = frappe.get_all(
            "POS Invoice",
            filters={
                "restaurant_table": table_name,
                "docstatus": 0,
                "status": ["!=", "Paid"],
                "is_return": 0
            },
            fields=["name", "customer", "grand_total", "posting_time", "modified"],
            order_by="creation desc",
            limit=1
        )
        
        if existing:
            invoice_name = existing[0].name
            # Get full invoice details with items
            invoice = frappe.get_doc("POS Invoice", invoice_name)
            
            # Format items for frontend
            items = []
            for item in invoice.items:
                items.append({
                    "item_code": item.item_code,
                    "item_name": item.item_name,
                    "quantity": item.qty,
                    "uom": item.uom,
                    "rate": item.rate,
                    "amount": item.amount,
                    "stock_uom": item.stock_uom,
                    "warehouse": item.warehouse,
                    "posa_special_instructions": item.get("posa_special_instructions", ""),
                    "posa_sent_qty": item.qty,  # Mark all as sent (already in kitchen)
                    "price_list_rate": item.price_list_rate,
                    "discount_percentage": item.discount_percentage or 0,
                    "discount_amount": item.discount_amount or 0,
                })
            
            return {
                "success": True,
                "invoice_name": invoice_name,
                "items": items,
                "customer": invoice.customer,
                "grand_total": invoice.grand_total,
                "is_new": False,
                "message": _("Loaded existing tab")
            }
        
        # No existing invoice - return empty to create new
        return {
            "success": True,
            "invoice_name": None,
            "items": [],
            "customer": customer,
            "is_new": True,
            "message": _("Start new tab")
        }
        
    except Exception as e:
        frappe.log_error(f"Failed to get table invoice: {str(e)}")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def merge_items_to_invoice(invoice_name, new_items, table_name=None, pos_profile=None, customer=None):
    """
    Merge new items into existing invoice (Running Tab pattern).
    Only sends new/updated items to kitchen.
    
    Args:
        invoice_name: Existing POS Invoice name
        new_items: List of new items to add
        table_name: Restaurant Table name (for new invoice)
        pos_profile: POS Profile name (required for new invoice)
        customer: Customer name (optional)
    
    Returns:
        dict: { success, invoice_name, new_items_count, sent_items: [...] }
    """
    import time
    
    if isinstance(new_items, str):
        import json
        new_items = json.loads(new_items)
    
    if not invoice_name and not table_name:
        return {"success": False, "message": _("Invoice or table required")}
    
    # Retry logic for race condition handling
    max_retries = 3
    retry_delay = 0.5
    
    for attempt in range(max_retries):
        try:
            return _merge_items_to_invoice_impl(
                invoice_name, new_items, table_name, pos_profile, customer
            )
        except frappe.exceptions.TimestampMismatchError:
            # Document was modified by another request, retry
            if attempt < max_retries - 1:
                frappe.db.commit()
                time.sleep(retry_delay)
                continue
            else:
                return {"success": False, "message": _("Table is busy, please try again")}
        except Exception as e:
            if attempt < max_retries - 1 and "Document has been modified" in str(e):
                frappe.db.commit()
                time.sleep(retry_delay)
                continue
            raise
    
    return {"success": False, "message": _("Failed to update table after retries")}


def _merge_items_to_invoice_impl(invoice_name, new_items, table_name=None, pos_profile=None, customer=None):
    """Internal implementation with retry support."""
    
    # Get or create invoice with lock
    if invoice_name and frappe.db.exists("POS Invoice", invoice_name):
        # Reload to get latest version
        invoice = frappe.get_doc("POS Invoice", invoice_name)
        invoice.reload()
    else:
        # Create new invoice for table - get defaults from POS Profile
        if not pos_profile:
            return {"success": False, "message": _("POS Profile required for new invoice")}
        
        # Get POS Profile defaults
        profile = frappe.get_doc("POS Profile", pos_profile)
        
        # Create new invoice with required fields
        invoice = frappe.new_doc("POS Invoice")
        invoice.restaurant_table = table_name
        invoice.pos_profile = pos_profile
        invoice.is_pos = 1
        invoice.update_stock = 1
        
        # Set required fields from POS Profile
        invoice.company = profile.company
        invoice.customer = customer or profile.customer
        invoice.currency = profile.currency
        invoice.conversion_rate = 1.0
        invoice.selling_price_list = profile.selling_price_list
        invoice.price_list_currency = profile.currency
        invoice.plc_conversion_rate = 1.0
        
        # Set posting date
        invoice.posting_date = frappe.utils.nowdate()
        invoice.posting_time = frappe.utils.nowtime()
        
        # Set taxes from Sales Taxes and Charges Template
        if profile.taxes_and_charges:
            tax_template = frappe.get_doc("Sales Taxes and Charges Template", profile.taxes_and_charges)
            for tax in tax_template.taxes:
                invoice.append("taxes", {
                    "charge_type": tax.charge_type,
                    "account_head": tax.account_head,
                    "rate": tax.rate,
                    "description": tax.description
                })
        
        # Add payment methods from POS Profile (required for set_missing_values)
        if profile.payments:
            for payment_method in profile.payments:
                # Get account from Mode of Payment (not from POS Payment Method)
                mop_account = get_mode_of_payment_account(
                    payment_method.mode_of_payment, 
                    profile.company
                )
                if mop_account:
                    invoice.append("payments", {
                        "mode_of_payment": payment_method.mode_of_payment,
                        "account": mop_account,
                        "amount": 0  # Will be set later during checkout
                    })
        else:
            return {"success": False, "message": _("POS Profile has no payment methods configured. Please add payment methods.")}
    
    # Ensure customer is set
    if not invoice.customer:
        return {"success": False, "message": _("Customer is required")}
    
    # Track which items are new (for kitchen notification)
    sent_items = []
    existing_items = {f"{i.item_code}-{i.uom}": i for i in invoice.items}
    
    # Note: kds_status will be reset to Pending AFTER set_missing_values() 
    # to ensure it's not overwritten by any default value calculations
    
    # Get income account from Mode of Payment or Company
    income_account = None
    if invoice.pos_profile:
        profile_doc = frappe.get_doc("POS Profile", invoice.pos_profile)
        if profile_doc.payments:
            # Get account from first payment method's Mode of Payment
            first_mop = profile_doc.payments[0].mode_of_payment
            income_account = get_mode_of_payment_account(first_mop, invoice.company)
    
    if not income_account:
        income_account = frappe.db.get_value("Company", invoice.company, "default_income_account")
    
    for new_item in new_items:
        item_key = f"{new_item.get('item_code')}-{new_item.get('uom')}"
        qty = flt(new_item.get('quantity', 1))
        
        if qty <= 0:
            continue
        
        if item_key in existing_items:
            # Update existing item quantity
            existing = existing_items[item_key]
            old_qty = flt(existing.qty)
            new_qty = old_qty + qty
            existing.qty = new_qty
            existing.amount = flt(new_qty * existing.rate)
            
            # Only send the additional quantity to kitchen
            sent_items.append({
                "item_code": new_item.get('item_code'),
                "item_name": new_item.get('item_name'),
                "qty": qty,
                "instructions": new_item.get('posa_special_instructions', ''),
                "is_additional": True
            })
        else:
            # Get item defaults (income_account is in Item Default child table, not Item)
            item_defaults = frappe.db.get_value(
                "Item",
                new_item.get('item_code'),
                ["item_name", "stock_uom"],
                as_dict=True
            ) or {}
            
            # Get income account from Item Default child table if not already set
            item_income_account = None
            if not income_account:
                item_income_account = frappe.db.get_value(
                    "Item Default",
                    {"parent": new_item.get('item_code'), "parenttype": "Item", "company": invoice.company},
                    "income_account"
                )
            
            # Get warehouse from POS Profile or item
            warehouse = new_item.get('warehouse')
            if not warehouse and invoice.pos_profile:
                warehouse = frappe.db.get_value("POS Profile", invoice.pos_profile, "warehouse")
            
            # Add new item with all required fields
            item_dict = {
                "item_code": new_item.get('item_code'),
                "item_name": new_item.get('item_name') or item_defaults.get('item_name'),
                "qty": qty,
                "uom": new_item.get('uom') or item_defaults.get('stock_uom') or "Nos",
                "stock_uom": new_item.get('stock_uom') or item_defaults.get('stock_uom') or "Nos",
                "rate": flt(new_item.get('rate', 0)),
                "amount": flt(qty * flt(new_item.get('rate', 0))),
                "warehouse": warehouse,
                "posa_special_instructions": new_item.get('posa_special_instructions', ''),
                "price_list_rate": flt(new_item.get('price_list_rate', new_item.get('rate', 0))),
                "discount_percentage": flt(new_item.get('discount_percentage', 0)),
                "discount_amount": flt(new_item.get('discount_amount', 0)),
                "income_account": income_account or item_income_account,
                "allow_zero_valuation_rate": 1  # Allow items without valuation rate
            }
            
            invoice.append("items", item_dict)
            
            sent_items.append({
                "item_code": new_item.get('item_code'),
                "item_name": new_item.get('item_name') or item_defaults.get('item_name'),
                "qty": qty,
                "instructions": new_item.get('posa_special_instructions', ''),
                "is_additional": False
            })
    
    if not invoice.items:
        return {"success": False, "message": _("No items to add")}
    
    # Save critical fields BEFORE set_missing_values() - they may get cleared
    saved_restaurant_table = invoice.restaurant_table
    saved_kds_status = invoice.get('kds_status') or 'Pending'
    was_modified = saved_kds_status != 'Pending'
    
    # Set missing values and calculate totals with error handling
    try:
        invoice.set_missing_values()
        invoice.calculate_taxes_and_totals()
    except AttributeError as e:
        error_msg = str(e)
        if "default_account" in error_msg or "account" in error_msg:
            return {"success": False, "message": _("POS Profile payment methods missing default account. Please configure POS Profile with valid payment methods and accounts.")}
        elif "income_account" in error_msg:
            return {"success": False, "message": _("Items missing income account. Please check item configurations or company default income account.")}
        else:
            frappe.log_error(f"set_missing_values error: {error_msg[:100]}")
            return {"success": False, "message": _("Configuration error: {0}").format(error_msg[:100])}
    except Exception as e:
        frappe.log_error(f"Invoice calculation error: {str(e)[:100]}")
        return {"success": False, "message": _("Error calculating invoice totals. Please check POS Profile and item configurations.")}
    
    # Restore critical fields that set_missing_values may have cleared
    if saved_restaurant_table and not invoice.restaurant_table:
        invoice.restaurant_table = saved_restaurant_table
    
    # Reset kds_status to Pending for modified orders (or ensure it's set)
    if saved_kds_status != 'Pending':
        invoice.kds_status = 'Pending'
    else:
        invoice.kds_status = 'Pending'  # Ensure new orders also have Pending status
    
    # Ensure kds_status is never null/empty
    if not invoice.kds_status:
        invoice.kds_status = 'Pending'
    
    # Save invoice (draft)
    invoice.save(ignore_permissions=True)
    
    # Notify KDS about new items
    if sent_items:
        notify_kds_partial_order(invoice.name, sent_items, table_name or invoice.restaurant_table, was_modified)
    
    return {
        "success": True,
        "invoice_name": invoice.name,
        "new_items_count": len(sent_items),
        "sent_items": sent_items,
        "status_reset": was_modified  # Tell frontend if status was reset
    }


def notify_kds_partial_order(invoice_name, sent_items, table_name, is_modified=False):
    """Notify KDS about new/additional items (not entire order)."""
    try:
        table_display = table_name
        if table_name:
            tname = frappe.db.get_value("Restaurant Table", table_name, "table_name")
            if tname:
                table_display = tname
        
        frappe.publish_realtime(
            event="kds_partial_order",
            message={
                "order_id": invoice_name,
                "table": table_display,
                "items": sent_items,
                "timestamp": str(frappe.utils.now()),
                "is_modified": is_modified  # True if order was modified (status changed to Pending)
            },
            room="kds_room"
        )
    except Exception as e:
        frappe.log_error(f"KDS partial notify error: {str(e)[:100]}")  # Truncate long errors


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
                "restaurant_table": ["is", "set"],
                "kds_status": ["not in", ["Completed", "Cancelled"]]
            },
            order_by="creation desc"
        )
        
        # Enrich with table name and items
        enriched_orders = []
        
        for order in orders:
            # Get table display name
            if order.restaurant_table:
                table_name = frappe.db.get_value(
                    "Restaurant Table", 
                    order.restaurant_table, 
                    "table_name"
                )
                order.table_display = table_name or order.restaurant_table
            
            # is_recently_modified: true if order was modified after creation (new items added)
            # and status is still Pending (not yet started preparing)
            creation_dt = frappe.utils.get_datetime(order.creation)
            modified_dt = frappe.utils.get_datetime(order.modified)
            # If modified more than 10 seconds after creation, consider it as "recently modified"
            order.is_recently_modified = (modified_dt - creation_dt).total_seconds() > 10
            
            # Get order items
            invoice = frappe.get_doc("POS Invoice", order.name)
            order.items = [
                {
                    "item_code": item.item_code,
                    "item_name": item.item_name,
                    "qty": item.qty,
                    "description": item.description,
                    "posa_special_instructions": item.get("posa_special_instructions")
                }
                for item in invoice.items
            ]
            
            enriched_orders.append(order)
        
        return enriched_orders or []
        
    except Exception as e:
        frappe.log_error(f"Failed to get KDS orders: {str(e)[:100]}")  # Truncate long errors
        return []


@frappe.whitelist()
def send_to_kitchen(order_data=None):
    """
    DEPRECATED: Use merge_items_to_invoice instead.
    Kept for backward compatibility.
    """
    return {"success": True, "message": _("Use merge_items_to_invoice API")}


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
        
        # Get table name
        table_display = order.restaurant_table
        if order.restaurant_table:
            table_name = frappe.db.get_value("Restaurant Table", order.restaurant_table, "table_name")
            if table_name:
                table_display = table_name
        
        # Emit realtime event
        frappe.publish_realtime(
            event="kds_new_order",
            message={
                "order_id": invoice_name,
                "table": table_display,
                "items": [
                    {
                        "item_code": item.item_code,
                        "item_name": item.item_name,
                        "qty": item.qty,
                        "description": item.description,
                        "posa_special_instructions": item.get("posa_special_instructions")
                    } for item in order.items
                ],
                "status": order.kds_status or "Pending",
                "timestamp": str(order.creation)
            },
            room="kds_room"
        )
        
    except Exception as e:
        frappe.log_error(f"Failed to notify KDS: {str(e)[:100]}")  # Truncate long errors


@frappe.whitelist(allow_guest=True)
def get_cfd_order(order_id):
    """
    Get order status for Customer Facing Display (CFD).
    
    Args:
        order_id: POS Invoice name
    
    Returns:
        dict: Order details with items and status
    """
    try:
        if not order_id:
            return {"success": False, "message": _("Order ID required")}
        
        # Get order
        order = frappe.get_doc("POS Invoice", order_id)
        
        return {
            "success": True,
            "order_id": order.name,
            "table": order.restaurant_table,
            "status": order.kds_status or "Pending",
            "items": [
                {
                    "item_code": item.item_code,
                    "item_name": item.item_name,
                    "qty": item.qty,
                    "status": item.get("kds_status") or "Pending"
                }
                for item in order.items
            ],
            "grand_total": order.grand_total
        }
        
    except Exception as e:
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def close_table_invoice(invoice_name, payments=None, write_off_amount=0):
    """
    Close (submit) table invoice and process payment.
    
    Args:
        invoice_name: POS Invoice name
        payments: Payment details
        write_off_amount: Amount to write off
    
    Returns:
        dict: { success, message, invoice_name }
    """
    try:
        if not invoice_name:
            return {"success": False, "message": _("Invoice name required")}
        
        invoice = frappe.get_doc("POS Invoice", invoice_name)
        
        if invoice.docstatus != 0:
            return {"success": False, "message": _("Invoice already processed")}
        
        # Add payments if provided
        if payments:
            if isinstance(payments, str):
                import json
                payments = json.loads(payments)
            invoice.payments = []
            for payment in payments:
                invoice.append("payments", payment)
        
        # Set write off
        if write_off_amount:
            invoice.write_off_amount = write_off_amount
        
        # Submit invoice
        invoice.submit()
        
        # Update table status to Empty
        if invoice.restaurant_table:
            frappe.db.set_value(
                "Restaurant Table", 
                invoice.restaurant_table, 
                "status", 
                "Empty"
            )
        
        return {
            "success": True,
            "message": _("Invoice closed successfully"),
            "invoice_name": invoice.name
        }
        
    except Exception as e:
        frappe.log_error(f"Failed to close invoice: {str(e)[:100]}")  # Truncate long errors
        return {"success": False, "message": str(e)}
