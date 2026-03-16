# -*- coding: utf-8 -*-
# Copyright (c) 2020, Youssef Restom and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint, flt
from frappe.model.document import Document


class POSOpeningShift(Document):
    def validate(self):
        self.validate_pos_profile_and_cashier()
        self.set_status()

    def validate_pos_profile_and_cashier(self):
        if self.company != frappe.db.get_value("POS Profile", self.pos_profile, "company"):
            frappe.throw(
                _("POS Profile {} does not belongs to company {}".format(self.pos_profile, self.company))
            )

        if not cint(frappe.db.get_value("User", self.user, "enabled")):
            frappe.throw(_("User {} has been disabled. Please select valid user/cashier".format(self.user)))

    def on_submit(self):
        self.set_status(update=True)
        self.create_pos_opening_entry()

    def create_pos_opening_entry(self):
        """Create ERPNext standard POS Opening Entry for validation compatibility"""
        frappe.logger().info(f"create_pos_opening_entry called for {self.name}")
        
        try:
            # Check if field exists and already has value
            if hasattr(self, 'pos_opening_entry') and self.pos_opening_entry:
                frappe.logger().info(f"POS Opening Shift {self.name} already has pos_opening_entry: {self.pos_opening_entry}")
                return
            
            frappe.logger().info(f"Creating POS Opening Entry for shift {self.name}...")
            
            # Create POS Opening Entry (ERPNext standard)
            entry = frappe.new_doc("POS Opening Entry")
            entry.pos_profile = self.pos_profile
            entry.user = self.user
            entry.company = self.company
            entry.period_start_date = self.period_start_date
            
            # Add opening balances from balance_details
            for detail in self.balance_details:
                entry.append("balance_details", {
                    "mode_of_payment": detail.mode_of_payment,
                    "opening_amount": flt(detail.amount)
                })
            
            frappe.logger().info(f"Saving POS Opening Entry...")
            entry.save(ignore_permissions=True)
            frappe.logger().info(f"Submitting POS Opening Entry {entry.name}...")
            entry.submit()
            
            # Link to this shift
            frappe.logger().info(f"Linking pos_opening_entry {entry.name} to shift {self.name}...")
            self.db_set("pos_opening_entry", entry.name)
            
            frappe.logger().info(f"✅ Created POS Opening Entry {entry.name} for Shift {self.name}")
            
        except Exception as e:
            error_msg = f"Failed to create POS Opening Entry for Shift {self.name}: {str(e)}"
            frappe.log_error(error_msg, "POS Opening Shift")
            frappe.logger().error(error_msg)
            # Don't throw error - allow shift to work without entry

    def set_status(self, update=False):
        """Set the status of the opening shift"""
        if self.docstatus == 0:
            status = "Draft"
        elif self.docstatus == 1:
            if self.pos_closing_shift:
                status = "Closed"
            else:
                status = "Open"
        else:
            status = "Cancelled"

        if update:
            frappe.db.set_value("POS Opening Shift", self.name, "status", status)
        else:
            self.status = status
