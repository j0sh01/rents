from __future__ import unicode_literals
import frappe

def execute():
    # Create Landlord role if it doesn't exist
    if not frappe.db.exists("Role", "Landlord"):
        role = frappe.new_doc("Role")
        role.role_name = "Landlord"
        role.desk_access = 1
        role.is_custom = 1
        role.insert(ignore_permissions=True)
    
    # Create Tenant role if it doesn't exist
    if not frappe.db.exists("Role", "Tenant"):
        role = frappe.new_doc("Role")
        role.role_name = "Tenant"
        role.desk_access = 1
        role.is_custom = 1
        role.insert(ignore_permissions=True)