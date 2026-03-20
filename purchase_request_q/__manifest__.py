# -*- coding: utf-8 -*-
{
    'name': 'Quanam l10n Purchase Request',
    "version": "18.0.1.0.1",
    'summary': 'Localización Quanam para el flujo de Solicitudes de Compra',
    'category': 'Purchase Management',
    'author': 'Quanam',
    'website': 'www.quanam.com',
    'license': 'LGPL-3',
    'depends': [
        'purchase_request'
    ],
    "data": [
        "views/purchase_request_view.xml",
        "reports/purchase_request_report.xml",
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
