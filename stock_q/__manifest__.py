# -*- coding: utf-8 -*-
{
    'name': 'Quanam l10n Stock ',
    "version": "18.0.1.1.0",
    'summary': 'Localización Quanam para el flujo de Stock',
    'category': 'Inventory',
    'author': 'Quanam',
    'website': 'https://www.quanam.com',
    'license': 'LGPL-3',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_warehouse_views.xml',
        'views/stock_location_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_quant_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
