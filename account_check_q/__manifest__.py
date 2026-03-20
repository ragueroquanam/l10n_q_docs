# -*- coding: utf-8 -*-
{
    'name': 'Quanam l10n Account Check',
    "version": "18.0.1.0.0",
    'author': 'Quanam',
    'website': 'www.quanam.com',
    'category': 'Accounting/Accounting',
    'sequence': 45,
    'summary': 'Localización Quanam para el flujo de Cheques',
    'depends': [
        'account'
    ],
    'data': [
        'views/account_journal_views.xml',
        'views/account_payment_views.xml',
        'views/account_payment_register_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
