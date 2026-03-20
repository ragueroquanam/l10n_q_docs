{
    "name": "Account Q Payment from File",
    "version": "18.0.1.0.0",
    "author": "Quanam",
    "website": "www.quanam.com",
    "category": "Account",
    "sequence": 50,
    "summary": "Process customer payments from uploaded files (Excel/TXT)",
    "depends": ["account_q"],
    "external_dependencies": {
        "python": ["openpyxl"],
    },
    "data": [
        "data/sequence_data.xml",
        "security/ir.model.access.csv",
        "views/account_move_views.xml",
        "views/account_q_payment_from_file_views.xml",
        "views/menu_items.xml",
    ],
    "installable": True,
    "license": "AGPL-3",
}

