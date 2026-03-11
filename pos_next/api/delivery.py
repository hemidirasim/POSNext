# -*- coding: utf-8 -*-
# Copyright (c) 2025, BrainWise and contributors
# For license information, please see license.txt

"""
POS Next Delivery API
Handles delivery charges, address management, and shipping calculations
"""

import frappe
from frappe import _
from frappe.utils import flt, cint


@frappe.whitelist()
def get_customer_addresses(customer):
    """
    Get all addresses for a customer.
    
    Args:
        customer: Customer ID
        
    Returns:
        list: List of address dictionaries
    """
    if not customer:
        return []
    
    try:
        # Get all linked addresses for the customer
        address_links = frappe.get_all(
            "Dynamic Link",
            filters={
                "link_doctype": "Customer",
                "link_name": customer,
                "parenttype": "Address"
            },
            fields=["parent"]
        )
        
        if not address_links:
            return []
        
        address_names = [link.parent for link in address_links]
        
        addresses = frappe.get_all(
            "Address",
            filters={"name": ["in", address_names], "disabled": 0},
            fields=[
                "name", "address_title", "address_type",
                "address_line1", "address_line2", "city", "county",
                "state", "country", "pincode", "phone", "email_id",
                "is_primary_address", "is_shipping_address"
            ],
            order_by="is_primary_address desc, modified desc"
        )
        
        return addresses
        
    except Exception as e:
        frappe.logger().error(f"Error fetching addresses: {str(e)}")
        return []


@frappe.whitelist()
def create_address(address_data):
    """
    Create a new address for a customer.
    
    Args:
        address_data: dict with address fields and customer
        
    Returns:
        dict: Created address document
    """
    try:
        data = frappe.parse_json(address_data) if isinstance(address_data, str) else address_data
        
        customer = data.get("customer")
        if not customer:
            frappe.throw(_("Customer is required"))
        
        # Create address document
        address = frappe.get_doc({
            "doctype": "Address",
            "address_title": data.get("address_title") or f"{customer} - {data.get('address_type', 'Shipping')}",
            "address_type": data.get("address_type") or "Shipping",
            "address_line1": data.get("address_line1"),
            "address_line2": data.get("address_line2"),
            "city": data.get("city"),
            "county": data.get("county"),
            "state": data.get("state"),
            "country": data.get("country") or frappe.defaults.get_defaults().get("country"),
            "pincode": data.get("pincode"),
            "phone": data.get("phone"),
            "email_id": data.get("email_id"),
            "is_primary_address": cint(data.get("is_primary_address", 0)),
            "is_shipping_address": cint(data.get("is_shipping_address", 1)),
            "links": [{
                "link_doctype": "Customer",
                "link_name": customer
            }]
        })
        
        address.insert(ignore_permissions=True)
        
        return {
            "success": True,
            "address": address.as_dict(),
            "message": _("Address created successfully")
        }
        
    except Exception as e:
        frappe.logger().error(f"Error creating address: {str(e)}")
        frappe.throw(_("Error creating address: {0}").format(str(e)))


@frappe.whitelist()
def calculate_delivery_charge(customer=None, address_name=None, subtotal=0, pos_profile=None):
    """
    Calculate delivery charge based on settings and address.
    
    Args:
        customer: Customer ID (optional)
        address_name: Selected address name (optional)
        subtotal: Cart subtotal amount
        pos_profile: POS Profile name
        
    Returns:
        dict: Delivery charge details
    """
    try:
        subtotal = flt(subtotal)
        
        # Get POS Settings for delivery configuration
        pos_settings = None
        if pos_profile:
            pos_settings = frappe.db.get_value(
                "POS Settings",
                {"pos_profile": pos_profile, "enabled": 1},
                ["use_delivery_charges", "delivery_item", "free_delivery_above", 
                 "default_delivery_charge", "delivery_charge_account"],
                as_dict=True
            )
        
        # If delivery not enabled
        if not pos_settings or not cint(pos_settings.get("use_delivery_charges")):
            return {
                "has_delivery": False,
                "charge": 0,
                "message": _("Delivery not enabled")
            }
        
        # Check for free delivery threshold
        free_delivery_above = flt(pos_settings.get("free_delivery_above", 0))
        if free_delivery_above > 0 and subtotal >= free_delivery_above:
            return {
                "has_delivery": True,
                "charge": 0,
                "is_free": True,
                "message": _("Free delivery (order above {0})").format(free_delivery_above),
                "delivery_item": pos_settings.get("delivery_item"),
                "delivery_charge_account": pos_settings.get("delivery_charge_account")
            }
        
        # Get default delivery charge
        charge = flt(pos_settings.get("default_delivery_charge", 0))
        
        # TODO: Future enhancement - calculate based on address/zone
        # if address_name:
        #     address = frappe.get_doc("Address", address_name)
        #     charge = calculate_by_zone(address)
        
        return {
            "has_delivery": True,
            "charge": charge,
            "is_free": False,
            "message": _("Delivery charge: {0}").format(charge) if charge > 0 else _("Free delivery"),
            "delivery_item": pos_settings.get("delivery_item"),
            "delivery_charge_account": pos_settings.get("delivery_charge_account")
        }
        
    except Exception as e:
        frappe.logger().error(f"Error calculating delivery charge: {str(e)}")
        return {
            "has_delivery": False,
            "charge": 0,
            "error": str(e)
        }


@frappe.whitelist()
def validate_delivery_settings(pos_profile):
    """
    Check if delivery is properly configured for the POS Profile.
    
    Args:
        pos_profile: POS Profile name
        
    Returns:
        dict: Validation result with configuration status
    """
    try:
        pos_settings = frappe.db.get_value(
            "POS Settings",
            {"pos_profile": pos_profile, "enabled": 1},
            ["use_delivery_charges", "delivery_item", "default_delivery_charge"],
            as_dict=True
        )
        
        if not pos_settings:
            return {
                "enabled": False,
                "configured": False,
                "message": _("POS Settings not found")
            }
        
        if not cint(pos_settings.get("use_delivery_charges")):
            return {
                "enabled": False,
                "configured": False,
                "message": _("Delivery charges not enabled")
            }
        
        # Check if delivery item is configured
        delivery_item = pos_settings.get("delivery_item")
        if not delivery_item:
            return {
                "enabled": True,
                "configured": False,
                "message": _("Delivery item not configured in POS Settings")
            }
        
        # Verify delivery item exists
        if not frappe.db.exists("Item", delivery_item):
            return {
                "enabled": True,
                "configured": False,
                "message": _("Delivery item '{0}' not found").format(delivery_item)
            }
        
        return {
            "enabled": True,
            "configured": True,
            "delivery_item": delivery_item,
            "default_charge": flt(pos_settings.get("default_delivery_charge", 0)),
            "message": _("Delivery configured correctly")
        }
        
    except Exception as e:
        frappe.logger().error(f"Error validating delivery settings: {str(e)}")
        return {
            "enabled": False,
            "configured": False,
            "error": str(e)
        }
