# -*- coding: utf-8 -*-
{
    "name": "Quanam Batch Payment - CABAL",
    "version": "18.0.1.0.0",
    "author": "Quanam",
    "website": "www.quanam.com",
    "description": """
                       Módulo para generar archivos de pagos masivos en formato CABAL
                       Soporta configuraciones para PMSA y CMSA
                       """,
    "depends": ["account_batch_payment_q"],
    "data": [
        "data/account_bank_payment_file_config_data.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
