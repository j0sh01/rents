import frappe
from frappe.utils.file_manager import save_file

@frappe.whitelist()
def get_total_rent_paid_all():
    """
    Get the total amount of rent paid by all tenants with docstatus 1.
    
    Returns:
        float: Total amount of rent paid by all tenants.
    """
    total_rent = frappe.db.sql("""
        SELECT SUM(amount_tzs) 
        FROM `tabPayment` 
        WHERE docstatus = 1
    """)
    
    return total_rent[0][0] if total_rent and total_rent[0][0] else 0.0

@frappe.whitelist()
def get_pending_rent():
    """
    Get the total amount of pending rent paid by all tenants with docstatus 0.
    
    Returns:
        float: Total amount of pending rent by all tenants.
    """
    total_rent = frappe.db.sql("""
        SELECT SUM(amount_tzs) 
        FROM `tabPayment` 
        WHERE docstatus = 0
    """)
    
    return total_rent[0][0] if total_rent and total_rent[0][0] else 0.0

@frappe.whitelist()
def get_all_payments():
    """
    Fetch all payment records from the Payment table.

    Returns:
        list: A list of dictionaries containing payment details.
    """
    payments = frappe.db.sql("""
        SELECT name, rental, amount_tzs, payment_date, payment_method, docstatus, end_date
        FROM `tabPayment`
    """, as_dict=True)
    
    return payments

@frappe.whitelist()
def get_properties():
    """
    Fetch all property records with specified fields.

    Returns:
        list: A list of dictionaries containing property details.
    """
    properties = frappe.db.sql("""
        SELECT name, title, location, price_tzs, bedrooms, bathroom, square_meters, description, status, image
        FROM `tabProperty`
    """, as_dict=True)
    
    return properties

def handle_image_upload(doc, field_name, file_data):
    """Helper function to handle image uploads

    Args:
        doc: Frappe document object
        field_name (str): Name of the image field
        file_data (dict): File data containing content and filename
    """
    if not file_data:
        return

    if isinstance(file_data, str):
        # If it's already a file URL, skip upload
        if file_data.startswith('/files/') or file_data.startswith('/private/files/'):
            return file_data
        return None

    filename = file_data.get('filename')
    content = file_data.get('content')
    
    if not (filename and content):
        return None

    # Save the file and attach it to the document
    file_doc = save_file(
        filename,
        content,
        doc.doctype,
        doc.name,
        folder="Home/Attachments",
        is_private=0
    )
    return file_doc.file_url

@frappe.whitelist()
def create_property(data):
    """Create a new Property document with image handling"""
    try:
        # Create a new Property document without images first
        property_doc = frappe.get_doc({
            "doctype": "Property",
            "title": data.get("title"),
            "location": data.get("location"),
            "price_tzs": data.get("price_tzs"),
            "bedrooms": data.get("bedrooms"),
            "bathroom": data.get("bathroom"),
            "status": data.get("status"),
            "description": data.get("description"),
            "square_meters": data.get("square_meters")
        })

        # Insert the document first to get the name
        property_doc.insert()

        # Handle image uploads
        image_fields = ["image", "image_1", "image_2", "image_3", "image_4"]
        for field in image_fields:
            if field in data and data[field]:
                file_url = handle_image_upload(property_doc, field, data[field])
                if file_url:
                    property_doc.set(field, file_url)

        # Save again with the image URLs
        property_doc.save()
        frappe.db.commit()

        return {
            "message": f"Property '{property_doc.title}' created successfully.",
            "property": property_doc.name
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Property Creation Error")
        return {
            "error": f"An error occurred while creating the property: {str(e)}"
        }

@frappe.whitelist()
def update_property(name, data):
    """Update an existing Property document with image handling"""
    try:
        # Get the existing property document
        property_doc = frappe.get_doc("Property", name)

        # Update non-image fields first
        updateable_fields = [
            "title", "location", "price_tzs", "bedrooms", 
            "bathroom", "status", "description", "square_meters"
        ]

        for field in updateable_fields:
            if field in data:
                property_doc.set(field, data.get(field))

        # Handle image uploads
        image_fields = ["image", "image_1", "image_2", "image_3", "image_4"]
        for field in image_fields:
            if field in data:
                file_url = handle_image_upload(property_doc, field, data[field])
                if file_url:
                    property_doc.set(field, file_url)

        # Save the updated document
        property_doc.save()
        frappe.db.commit()

        return {
            "message": f"Property '{property_doc.title}' updated successfully.",
            "property": property_doc.name
        }

    except frappe.DoesNotExistError:
        frappe.log_error(frappe.get_traceback(), "Property Update Error")
        return {
            "error": f"Property with name '{name}' does not exist."
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Property Update Error")
        return {
            "error": f"An error occurred while updating the property: {str(e)}"
        }


# Add this to your Frappe backend API file (e.g., rents/rental_management_system/api.py)

import frappe
from frappe import _

@frappe.whitelist()
def get_users_with_roles():
    """
    Get all users with 'Tenants' or 'System Manager' roles
    along with their property assignments and rental information
    """
    try:
        # Get users with specific roles
        users_with_roles = frappe.db.sql("""
            SELECT DISTINCT u.name, u.email, u.full_name, u.user_image, u.phone
            FROM `tabUser` u
            INNER JOIN `tabHas Role` hr ON u.name = hr.parent
            WHERE hr.role IN ('Tenants', 'System Manager')
            AND u.enabled = 1
            ORDER BY u.full_name
        """, as_dict=True)
        
        # Get user roles for each user
        for user in users_with_roles:
            user_roles = frappe.db.sql("""
                SELECT role FROM `tabHas Role` 
                WHERE parent = %s
            """, user.name, as_dict=True)
            user['roles'] = [role.role for role in user_roles]
        
        # Get property assignments and rental information for tenants
        for user in users_with_roles:
            if 'Tenants' in user.get('roles', []):
                # Check if user has an active rental
                rental = frappe.db.sql("""
                    SELECT r.name, r.property, r.start_date, r.end_date, r.monthly_rent,
                           p.title as property_name
                    FROM `tabRental` r
                    LEFT JOIN `tabProperty` p ON r.property = p.name
                    WHERE r.tenant = %s AND r.status = 'Active'
                    ORDER BY r.creation DESC
                    LIMIT 1
                """, user.name, as_dict=True)
                
                if rental:
                    rental_info = rental[0]
                    user['assigned_property'] = rental_info.property
                    user['property_name'] = rental_info.property_name
                    user['lease_start'] = rental_info.start_date
                    user['lease_end'] = rental_info.end_date
                    user['monthly_rent'] = rental_info.monthly_rent
                    user['rental_status'] = 'Active'
                else:
                    user['rental_status'] = 'Inactive'
                    user['assigned_property'] = None
                    user['property_name'] = None
            else:
                # System Manager - no property assignment
                user['rental_status'] = 'N/A'
                user['assigned_property'] = None
                user['property_name'] = None
        
        return users_with_roles
        
    except Exception as e:
        frappe.log_error(f"Error in get_users_with_roles: {str(e)}")
        return []        
    
@frappe.whitelist()
def get_rentals(filters=None):
    """
    Get all rentals with related property and tenant information.
    
    Args:
        filters (dict, optional): Dictionary of filters to apply
        
    Returns:
        dict: Contains list of rentals and any error messages
    """
    try:
        from frappe.utils.data import format_date

        # Define the fields to fetch
        fields = [
            "name", "property", "property_name", 
            "tenant", "tenant_name", "status",
            "frequency", "monthly_rent_tzs", 
            "start_date", "end_date", "total_rent_tzs",
            "docstatus"  # To check if document is submitted
        ]

        # Build filter conditions
        if not filters:
            filters = {}

        # Get rentals with specified fields
        rentals = frappe.get_all(
            "Rental",
            fields=fields,
            filters=filters,
            order_by="creation desc"
        )

        # Enhance each rental with additional information
        for rental in rentals:
            # Get property details
            if rental.property:
                property_doc = frappe.get_doc("Property", rental.property)
                rental.property_details = {
                    "title": property_doc.title,
                    "location": property_doc.location,
                    "bedrooms": property_doc.bedrooms,
                    "bathroom": property_doc.bathroom,
                    "square_meters": property_doc.square_meters,
                    "image": property_doc.image
                }

            # Get tenant details
            if rental.tenant:
                tenant = frappe.get_doc("User", rental.tenant)
                rental.tenant_details = {
                    "full_name": tenant.full_name,
                    "email": tenant.email,
                    "phone": tenant.phone,
                    "user_image": tenant.user_image
                }

            # Format dates for better readability
            if rental.start_date:
                rental.start_date = format_date(rental.start_date)
            if rental.end_date:
                rental.end_date = format_date(rental.end_date)

            # Add status context
            rental.status_context = {
                "Active": "green",
                "Expired": "red",
                "Terminated": "orange"
            }.get(rental.status, "gray")

        return {
            "message": "Rentals fetched successfully",
            "rentals": rentals,
            "total_count": len(rentals)
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Rental Fetch Error")
        return {
            "error": f"An error occurred while fetching rentals: {str(e)}",
            "rentals": []
        }

@frappe.whitelist()
def get_active_properties_count(tenant):
    """
    Get the count of distinct active properties assigned to a specific tenant.

    Args:
        tenant (str): The ID of the tenant.

    Returns:
        dict: Contains the count of distinct active properties and any error messages.
    """
    try:
        # Use frappe.get_all to fetch distinct active properties for the tenant
        rentals = frappe.get_all(
            "Rental",
            filters={
                "tenant": tenant,
                "status": "Active"
            },
            fields=["property"],
            distinct=True
        )

        # Count the number of distinct properties
        active_properties_count = len(rentals)

        return {
            "message": "Active properties count fetched successfully.",
            "tenant": tenant,
            "active_properties_count": active_properties_count
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Active Properties Count Error")
        return {
            "error": f"An error occurred while fetching active properties count: {str(e)}",
            "tenant": tenant,
            "active_properties_count": 0
        }