{
    'name': "Approval Route Extension - Quanam",
    'version': '18.0.1.1.1',
    'depends': ['xf_approval_route_base', 'xf_approval_route_payment'],
    'author': "Quanam",
    'category': 'Accounting/Accounting',
    'summary': "Extiende rutas de aprobación para extender comportamiento de 'Ruta por defecto' y aprobación masiva de pagos.",
    'license': 'LGPL-3',
    'data': [
        'views/approval_route_views.xml',
        'views/account_payments_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
