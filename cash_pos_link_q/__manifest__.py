{
    'name': 'Cash POS Link - Quanam',
    "version": "18.0.1.0.0",
    'license': 'LGPL-3',
    'summary': 'Localización Quanam para las configuraciones del POS',
    'category': 'Purchase Management',
    'author': 'Quanam',
    'website': 'https://www.quanam.com',
    'depends': ['pos_link_q', 'cash_management_q'],
    'data': [
        'views/cash_management_config_view.xml',
    ],
    'installable': True,
    'application': False,
}
