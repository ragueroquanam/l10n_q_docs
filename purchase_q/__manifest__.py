# -*- coding: utf-8 -*-
{
    'name': 'Quanam l10n Purchase Order',
    "version": "18.0.1.1.0",
    'summary': 'Localización Quanam para el flujo de Ordenes de Compra',
    'category': 'Purchase',
    'author': 'Quanam',
    'website': 'www.quanam.com',
    'license': 'LGPL-3',
    'depends': [
        'purchase'
    ],
    'data': [
        'views/purchase_order_view.xml',
        'views/supplierinfo_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
