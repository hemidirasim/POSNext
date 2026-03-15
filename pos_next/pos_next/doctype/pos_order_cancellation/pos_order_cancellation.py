"""
POS Order Cancellation Controller
"""
import frappe
from frappe.model.document import Document


class POSOrderCancellation(Document):
    def before_insert(self):
        # Calculate totals
        total_qty = 0
        total_amt = 0
        
        for item in self.items:
            total_qty += item.quantity or 0
            if not item.amount and item.rate and item.quantity:
                item.amount = item.rate * item.quantity
            total_amt += item.amount or 0
        
        self.total_quantity = total_qty
        self.total_amount = total_amt
    
    def validate(self):
        # Ensure reason_text is set
        if not self.reason_text and self.reason:
            reason_map = {
                "customer_changed_mind": "Customer changed mind",
                "wrong_item_ordered": "Wrong item ordered",
                "item_out_of_stock": "Item out of stock",
                "long_preparation_time": "Long preparation time",
                "kitchen_mistake": "Kitchen mistake",
                "quality_issue": "Quality issue",
                "other": "Other Reason"
            }
            self.reason_text = reason_map.get(self.reason, self.reason)
