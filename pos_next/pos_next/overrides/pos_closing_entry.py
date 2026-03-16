import frappe
from frappe import _
from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import POSClosingEntry

def custom_validate_pos_invoices(self):
    """
    Sales Invoice-ləri yoxla (POS Invoice yox).
    Çünki bizim POS sistemimiz Sales Invoice yaradır.
    pos_invoice field-i boş ola bilər, sales_invoice istifadə edirik.
    """
    invalid_rows = []
    
    for d in self.pos_transactions:
        # Əsasən sales_invoice istifadə edirik
        invoice_no = d.sales_invoice or d.pos_invoice
        
        if not invoice_no:
            # Hər iki field boşdursa - xəta
            invalid_rows.append({
                "idx": d.idx,
                "msg": ["Həm Sales Invoice, həm də POS Invoice boşdur"]
            })
            continue
        
        # Sales Invoice yoxla
        try:
            sales_inv = frappe.db.get_values(
                "Sales Invoice",
                invoice_no,
                ["consolidated_invoice", "pos_profile", "docstatus", "owner", "name"],
                as_dict=1,
            )
            
            if not sales_inv:
                # Faktura tapılmadı - xəta
                invalid_rows.append({
                    "idx": d.idx,
                    "msg": [f"Faktura tapılmadı: {invoice_no}"]
                })
                continue
                
            sales_inv = sales_inv[0]
            invalid_row = {"idx": d.idx}
            
            # Yoxlamalar
            if sales_inv.consolidated_invoice:
                invalid_row.setdefault("msg", []).append("Faktura artıq konsolidasiya edilib")
            
            if sales_inv.pos_profile and sales_inv.pos_profile != self.pos_profile:
                invalid_row.setdefault("msg", []).append("POS Profili uyğun gəlmir")
            
            if sales_inv.docstatus != 1:
                invalid_row.setdefault("msg", []).append("Faktura təsdiqlənməyib")
            
            if invalid_row.get("msg"):
                invalid_rows.append(invalid_row)
                
        except Exception as e:
            # Gözlənilməz xəta
            invalid_rows.append({
                "idx": d.idx,
                "msg": [f"Xəta: {str(e)}"]
            })
    
    # Xətalar varsa göstər
    if invalid_rows:
        error_list = []
        for row in invalid_rows:
            for msg in row.get("msg", []):
                error_list.append(f"Sətir #{row.get('idx')}: {msg}")
        
        if error_list:
            frappe.throw(error_list, title=_("Yanlış fakturalar"), as_list=True)

# Override et
POSClosingEntry.validate_pos_invoices = custom_validate_pos_invoices