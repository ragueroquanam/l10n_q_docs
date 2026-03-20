# -*- coding: utf-8 -*-
{
    "name": "Quanam Reports",
    "version": "18.0.2.0.0",
    "author": "Quanam",
    "website": "www.quanam.com",
    "category": "Accounting/Accounting",
    "sequence": 45,
    "summary": "Reportes contables",
    "depends": ["base", "account", "report_xlsx"],
    "data": [
        'security/ir.model.access.csv',
        'views/statement_change_equity_conf_views.xml',
        'report/statement_change_equity_reports.xml',
        'report/statement_change_equity_templates.xml',
        'wizard/statement_changes_equity_wizard_views.xml',
        'views/menu_items.xml',
    ],
    "demo": [],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
