def send_to_kitchen(order_data=None):
    """
    Send order items to kitchen (KDS).
    Creates or updates a POS Invoice for the table.
    
    Args:
        order_data: dict with table_name, table_id, items, timestamp, status
    
    Returns:
        dict: { success: bool, invoice_name: str, message: str }
    """
    try:
        # Debug: Log entry

        
        # Parse order_data if it's a string (JSON)
        if isinstance(order_data, str):
            import json
            order_data = json.loads(order_data)
        
        # If order_data is still None, try to get from form_dict
        if order_data is None and 'order_data' in frappe.form_dict:
            order_data = frappe.form_dict.get('order_data')
            if isinstance(order_data, str):
                import json
                order_data = json.loads(order_data)
        
        if not order_data:
            frappe.throw(_("Order data is required"))
        
        table_name = order_data.get("table_id")
        table_display_name = order_data.get("table_name")
        items = order_data.get("items", [])
        
        
        if not table_name:
            frappe.throw(_("Table is required"))
        
        if not items:
            frappe.throw(_("No items to send to kitchen"))
        
        # Check for existing draft invoice for this table
        existing_invoice = frappe.get_all(
            "POS Invoice",
            fields=["name", "kds_status", "restaurant_table"],
            filters={
                "restaurant_table": table_name,
                "docstatus": 0,
                "status": ["!=", "Paid"]
            },
            limit=1
        )
        
        
        if existing_invoice:
            # Update existing invoice
            invoice = frappe.get_doc("POS Invoice", existing_invoice[0].name)
        else:
            # Create new invoice with required fields
            invoice = frappe.new_doc("POS Invoice")
            
            # Get default values - find any active customer
            default_customer = frappe.defaults.get_user_default("Customer") or frappe.db.get_value("Customer", {"disabled": 0}, "name")
            if not default_customer:
                return {
                    "success": False,
                    "message": _("No active Customer found. Please create a Customer first.")
                }
            
            default_company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
            
            # Try to find any active POS Profile
            default_pos_profile = frappe.db.get_value("POS Profile", {"disabled": 0}, "name")
            if not default_pos_profile:
                # List all profiles for debugging
                all_profiles = frappe.get_all("POS Profile", fields=["name", "disabled", "company"])
            
            today = frappe.utils.today()
            
            # Validate customer exists
            if not default_customer:
                return {
                    "success": False,
                    "message": _("No active Customer found. Please create a Customer in ERPNext.")
                }
            
            # Set required fields - pos_profile is optional
            invoice.customer = default_customer
            invoice.company = default_company
            if default_pos_profile:
                invoice.pos_profile = default_pos_profile
            invoice.posting_date = today
            invoice.due_date = today
            invoice.restaurant_table = table_name
            invoice.kds_status = "Pending"
            
            # No payment needed at this stage - payment will be collected at checkout
            # Set is_pos to False to avoid payment validation for KDS orders
            invoice.is_pos = 0
            
        
        # Add items to invoice
        item_count = len(items)
        
        
        # Ensure invoice.items is a list (not None)
        if invoice.items is None:
            invoice.items = []
        
        
        for idx, item_data in enumerate(items):
            try:
                item_code = item_data.get("item_code")
                qty = item_data.get("quantity", 1)
                
                # Check if item already exists in invoice
                existing_item = None
                for item in invoice.items:
                    if item.item_code == item_code:
                        existing_item = item
                        break
                
                if existing_item:
                    existing_item.qty += qty
                else:
                    # Add new item
                    item_doc = frappe.get_doc("Item", item_code)
                    
                    invoice.append("items", {
                        "item_code": item_code,
                        "item_name": item_data.get("item_name") or item_doc.item_name,
                        "qty": qty,
                        "uom": item_data.get("uom") or item_doc.stock_uom,
                        "rate": item_doc.standard_rate or 0,
                        "posa_special_instructions": item_data.get("special_instructions", "")
                    })
            except Exception as item_error:
                raise
        
        # Save invoice - check POS Opening Entry first
        try:
            invoice.save(ignore_permissions=True)
        except Exception as save_error:
            error_str = str(save_error)
            if "POS Opening Entry" in error_str or "No open POS" in error_str:
                return {
                    "success": False,
                    "message": _("Please open a POS Opening Entry first. Go to POS > POS Opening Entry > New")
                }
            raise
        
        # Build KDS notification with item details
        kds_items = []
        for item_data in items:
            kds_items.append({
                "item_code": item_data.get("item_code"),
                "item_name": item_data.get("item_name"),
                "qty": item_data.get("quantity"),
                "total_qty": item_data.get("total_quantity"),  # Total in cart
                "is_additional": item_data.get("total_quantity", 0) > item_data.get("quantity", 0)
            })
        
        
        # Notify KDS about the order
        frappe.publish_realtime(
            event="kds_new_order",
            message={
                "order_id": invoice.name,
                "table": table_display_name or table_name,
                "items": kds_items,
                "items_count": len(items),
                "timestamp": frappe.utils.now(),
                "is_update": len(invoice.items) > len(items)  # True if adding to existing
            },
            room="kds_room"
        )
        
        
        return {
            "success": True,
            "invoice_name": invoice.name,
            "message": _("Order sent to kitchen successfully")
        }
        
    except Exception as e:
        import traceback
        error_msg = str(e)[:100]  # Sadece ilk 100 karakter
        frappe.log_error(f"KDS: {error_msg}")
        return {
            "success": False,
            "message": f"Error: {error_msg}"
        }


@frappe.whitelist()
def notify_kds_new_order(invoice_name):
    """
    Notify KDS displays about a new order.
    Called when a new order is created with restaurant_table.
    
