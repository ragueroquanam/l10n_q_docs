# -*- coding: utf-8 -*-
{
    "name": "POS & Cash Bridge Q",
    "summary": "Integra los campos de transacciones POS en la vista de Caja",
    "version": "18.0.1.0.0",
    'category': 'Purchase Management',
    'author': 'Quanam',
    'website': 'https://www.quanam.com',
    'license': 'LGPL-3',
    "depends": [
        "pos_q",
        "cash_management_q",
    ],
    "data": [
        "views/cash_management_session_views.xml",
    ],
    "installable": True,
    'application': False,
    'auto_install': False,
}
