# -*- coding: utf-8 -*-
{
    'name': 'Quanam l10n Purchase approval levels',
    "version": "18.0.1.0.0",
    'author': 'Quanam',
    'website': 'www.quanam.com',
    'category': 'Purchase',
    'sequence': 45,
    'summary': 'Localización Quanam para el flujo de Ordenes de Compra. Adiciona niveles de aprobación',
    'depends': [
        'purchase',
        'purchase_q'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_approval_level_views.xml',
        'views/purchase_order_views.xml',
        'data/mail_template_data.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
