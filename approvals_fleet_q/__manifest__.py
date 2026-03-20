{
    "name": "Quanam Approval fuel of Fleet",
    "version": "18.0.1.1.0",
    "author": "Quanam",
    "website": "www.quanam.com",
    "category": "Approvals",
    'sequence': 45,
    'summary': "Solicitud de Combustibles en aprobaciones",
    "depends": ["approvals", "fleet", "base_wizard_utils", "approvals_purchase"],
    "data": [
        "views/approval_category_views.xml",
        "views/approval_product_line_views.xml",
        "views/approval_request_views.xml",
        "views/approval_request_template.xml",
        "views/fleet_vehicle_views.xml"
    ],
    "installable": True,
    "license": "AGPL-3",
}
