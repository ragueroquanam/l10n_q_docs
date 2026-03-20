# -*- coding: utf-8 -*-
{
    'name': 'Quanam l10n POS Link provider',
    "version": "18.0.1.2.0",
    'license': 'LGPL-3',
    'summary': 'Proveedor POS Link para pagos por POS',
    'category': 'Purchase Management',
    'author': 'Quanam',
    'website': 'https://www.quanam.com',
    'depends': ['pos_q'],
    'data': [
        'security/ir.model.access.csv',
        'data/res_currency_data.xml',
        'data/pos_payment_provider_data.xml',
        'views/account_journal_inherit_views.xml',
        'views/account_payment_views.xml',
        'wizard/pos_void_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
