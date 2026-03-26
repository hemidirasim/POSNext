# Copyright (c) 2025, BrainWise and contributors
# For license information, please see license.txt

"""
Shift Reports API for POS Next

X Report - Mid-shift sales report (can be printed anytime while shift is open)
Z Report - End-of-shift report (printed when closing shift)

Both reports provide:
- Sales summary (gross, net, returns)
- Payment breakdown (cash, card, other)
- Invoice counts
- Tax summary
"""

import frappe
from frappe import _
from frappe.utils import flt, now, getdate, get_datetime
from typing import Dict, List, Optional


@frappe.whitelist()
def get_x_report_data(pos_profile: str, opening_shift: Optional[str] = None) -> Dict:
    """
    Get X Report data - mid-shift report while shift is still open.
    Can be printed anytime during the shift.
    
    Args:
        pos_profile: POS Profile name
        opening_shift: Optional POS Opening Shift name (if None, uses current open shift)
    
    Returns:
        dict: X Report data with sales summary, payments, and statistics
    """
    if not pos_profile:
        frappe.throw(_("POS Profile is required"))
    
    # If no opening_shift provided, find current open shift
    if not opening_shift:
        opening_shift = get_current_open_shift(pos_profile)
        if not opening_shift:
            frappe.throw(_("No open shift found for this POS Profile"))
    
    # Verify shift belongs to this POS Profile
    shift_doc = frappe.get_doc("POS Opening Shift", opening_shift)
    if shift_doc.pos_profile != pos_profile:
        frappe.throw(_("Shift does not belong to this POS Profile"))
    
    # Get all invoices created during this shift
    invoices = get_shift_invoices(opening_shift)
    
    # Calculate sales metrics
    sales_data = calculate_sales_metrics(invoices)
    
    # Get payment breakdown
    payment_data = get_payment_breakdown(invoices)
    
    # Get tax summary
    tax_summary = get_tax_summary(invoices)
    
    # Build report
    report = {
        "report_type": "X Report",
        "report_title": _("X Report - Mid Shift"),
        "generated_at": now(),
        "shift_info": {
            "opening_shift": opening_shift,
            "pos_profile": pos_profile,
            "cashier": shift_doc.user,
            "shift_start": shift_doc.period_start_date,
            "report_generated": now(),
            "shift_status": _("Open"),
        },
        "sales_summary": sales_data,
        "payments": payment_data,
        "tax_summary": tax_summary,
        "invoices": {
            "total_count": len(invoices),
            "list": [inv.name for inv in invoices[:10]],  # First 10 invoice numbers
        }
    }
    
    return report


@frappe.whitelist()
def get_z_report_data(pos_profile: str, opening_shift: Optional[str] = None) -> Dict:
    """
    Get Z Report data - end-of-shift report.
    This is the final report printed when closing shift.
    
    Args:
        pos_profile: POS Profile name
        opening_shift: Optional POS Opening Shift name
    
    Returns:
        dict: Z Report data with complete shift summary
    """
    if not pos_profile:
        frappe.throw(_("POS Profile is required"))
    
    # If no opening_shift provided, find current open shift
    if not opening_shift:
        opening_shift = get_current_open_shift(pos_profile)
        if not opening_shift:
            frappe.throw(_("No open shift found for this POS Profile"))
    
    # Get shift document
    shift_doc = frappe.get_doc("POS Opening Shift", opening_shift)
    
    # Get all invoices for this shift
    invoices = get_shift_invoices(opening_shift)
    
    # Calculate metrics
    sales_data = calculate_sales_metrics(invoices)
    payment_data = get_payment_breakdown(invoices)
    tax_summary = get_tax_summary(invoices)
    
    # Calculate duration
    duration = calculate_shift_duration(shift_doc.period_start_date, now())
    
    # Build Z Report
    report = {
        "report_type": "Z Report",
        "report_title": _("Z Report - End of Shift"),
        "generated_at": now(),
        "shift_info": {
            "opening_shift": opening_shift,
            "pos_profile": pos_profile,
            "cashier": shift_doc.user,
            "shift_start": shift_doc.period_start_date,
            "shift_end": now(),
            "duration": duration,
            "shift_status": _("Closing"),
        },
        "sales_summary": sales_data,
        "payments": payment_data,
        "tax_summary": tax_summary,
        "statistics": {
            "invoices_count": len(invoices),
            "average_ticket": sales_data["net_sales"] / len(invoices) if invoices else 0,
            "invoices_per_hour": len(invoices) / (duration["hours"] or 1) if duration else 0,
        }
    }
    
    return report


def get_current_open_shift(pos_profile: str) -> Optional[str]:
    """Get the current open shift for a POS Profile"""
    result = frappe.db.get_value(
        "POS Opening Shift",
        {
            "pos_profile": pos_profile,
            "status": "Open",
            "docstatus": 1
        },
        "name"
    )
    return result


def get_shift_invoices(opening_shift: str) -> List[Dict]:
    """Get all submitted invoices linked to an opening shift"""
    invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            "pos_opening_shift": opening_shift,
            "docstatus": 1,
            "is_pos": 1
        },
        fields=[
            "name", "grand_total", "paid_amount", "outstanding_amount",
            "discount_amount", "total_taxes_and_charges", "is_return",
            "posting_date", "posting_time", "customer", "customer_name"
        ]
    )
    return invoices


def calculate_sales_metrics(invoices: List[Dict]) -> Dict:
    """Calculate sales metrics from invoices"""
    gross_sales = 0
    returns_total = 0
    discounts_total = 0
    tax_total = 0
    
    for inv in invoices:
        if inv.is_return:
            returns_total += abs(flt(inv.grand_total))
        else:
            gross_sales += flt(inv.grand_total)
            discounts_total += flt(inv.discount_amount or 0)
            tax_total += flt(inv.total_taxes_and_charges or 0)
    
    net_sales = gross_sales - returns_total
    
    return {
        "gross_sales": flt(gross_sales, 2),
        "returns": flt(returns_total, 2),
        "net_sales": flt(net_sales, 2),
        "discounts": flt(discounts_total, 2),
        "tax_collected": flt(tax_total, 2),
    }


def get_payment_breakdown(invoices: List[Dict]) -> Dict:
    """Get payment method breakdown from invoices"""
    invoice_names = [inv.name for inv in invoices if not inv.is_return]
    
    if not invoice_names:
        return {
            "cash": 0,
            "card": 0,
            "other": 0,
            "total": 0,
            "breakdown": []
        }
    
    # Get payments from Sales Invoice Payment child table
    payments = frappe.get_all(
        "Sales Invoice Payment",
        filters={"parent": ["in", invoice_names]},
        fields=["mode_of_payment", "amount"]
    )
    
    cash_total = 0
    card_total = 0
    other_total = 0
    breakdown = {}
    
    for payment in payments:
        mode = payment.mode_of_payment or "Unknown"
        amount = flt(payment.amount)
        
        # Categorize payment
        mode_lower = mode.lower()
        if "cash" in mode_lower or "nağd" in mode_lower:
            cash_total += amount
        elif "card" in mode_lower or "kredit" in mode_lower or "debit" in mode_lower or "kart" in mode_lower:
            card_total += amount
        else:
            other_total += amount
        
        # Detailed breakdown
        if mode not in breakdown:
            breakdown[mode] = 0
        breakdown[mode] += amount
    
    # Convert breakdown to list
    breakdown_list = [
        {"mode": k, "amount": flt(v, 2)} 
        for k, v in sorted(breakdown.items(), key=lambda x: x[1], reverse=True)
    ]
    
    return {
        "cash": flt(cash_total, 2),
        "card": flt(card_total, 2),
        "other": flt(other_total, 2),
        "total": flt(cash_total + card_total + other_total, 2),
        "breakdown": breakdown_list
    }


def get_tax_summary(invoices: List[Dict]) -> List[Dict]:
    """Get tax summary from invoices"""
    invoice_names = [inv.name for inv in invoices if not inv.is_return]
    
    if not invoice_names:
        return []
    
    # Get taxes from Sales Taxes and Charges child table
    taxes = frappe.db.sql("""
        SELECT 
            charge_type,
            account_head,
            SUM(tax_amount) as total_amount,
            rate
        FROM `tabSales Taxes and Charges`
        WHERE parent IN %(invoices)s
            AND parenttype = 'Sales Invoice'
        GROUP BY account_head
        ORDER BY total_amount DESC
    """, {"invoices": tuple(invoice_names) or ("",)}, as_dict=True)
    
    return [
        {
            "account": t.account_head,
            "rate": flt(t.rate, 2),
            "amount": flt(t.total_amount, 2)
        }
        for t in taxes if t.total_amount
    ]


def calculate_shift_duration(start_date, end_date) -> Dict:
    """Calculate shift duration in hours and minutes"""
    if not start_date or not end_date:
        return {"hours": 0, "minutes": 0, "formatted": "0h 0m"}
    
    start = get_datetime(start_date)
    end = get_datetime(end_date)
    
    diff = end - start
    hours = diff.days * 24 + diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60
    
    return {
        "hours": hours,
        "minutes": minutes,
        "formatted": f"{hours}h {minutes}m"
    }


@frappe.whitelist()
def print_x_report(pos_profile: str, opening_shift: Optional[str] = None) -> Dict:
    """
    Generate and return X Report for printing
    Returns data that can be formatted for thermal printer
    """
    report_data = get_x_report_data(pos_profile, opening_shift)
    
    # Mark as printed
    report_data["printed_at"] = now()
    report_data["print_count"] = get_print_count(opening_shift, "X")
    
    return report_data


@frappe.whitelist()
def print_z_report(pos_profile: str, opening_shift: Optional[str] = None) -> Dict:
    """
    Generate and return Z Report for printing
    This is the final shift report
    """
    report_data = get_z_report_data(pos_profile, opening_shift)
    
    # Mark as printed
    report_data["printed_at"] = now()
    report_data["print_count"] = get_print_count(opening_shift, "Z")
    
    return report_data


def get_print_count(opening_shift: str, report_type: str) -> int:
    """Get how many times this report has been printed"""
    # This could be stored in a log table
    # For now, return 1
    return 1
