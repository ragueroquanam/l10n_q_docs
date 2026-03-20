{
    'name': 'Quanam - Purchase Request Extra Specifications',
    'version': '18.0.1.1.0',
    'summary': 'Traslada especificaciones desde la solicitud de compra a la RFQ',
    'description': '''
Este módulo extiende el flujo estándar de solicitudes de compra para:
- Copiar el campo Especificaciones desde la solicitud a la RFQ.
- Mostrarlo y permitir editarlo en la interfaz de RFQ.
- Incluirlo en el documento PDF impreso de la solicitud de cotización.
''',
    'author': 'Quanam',
    'category': 'Purchases',
    'depends': ['purchase', 'purchase_request'],
    'data': [
        'views/purchase_order_line_views.xml',
        'views/report_purchase_quotation_inherit.xml',
        'views/report_purchase_order_inherit.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
