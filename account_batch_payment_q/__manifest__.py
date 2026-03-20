# -*- coding: utf-8 -*-
{
    'name': 'Quanam Batch Payment',
    "version": "18.0.2.1.0",
    'author': 'Quanam',
    'website': 'www.quanam.com',
    'description': """
Batch Payments
=======================================
Batch payments allow grouping payments.

They are used namely, but not only, to group several cheques before depositing them in a single batch to the bank.
The total amount deposited will then appear as a single transaction on your bank statement.
When you reconcile, simply select the corresponding batch payment to reconcile all the payments in the batch.
    """,
    'depends': ['account_batch_payment'],
    "data": [
        "data/account_payment_data.xml",
        "security/ir.model.access.csv",
        "views/account_bank_payment_file_config_views.xml",
        "views/res_partner_bank_views.xml",
        "views/account_journal_views.xml",
        "views/account_payment_views.xml",
        "views/account_batch_payment_views.xml",
        "views/menu_items.xml",

    ],
    'installable': True,
    'license': 'LGPL-3',
}
