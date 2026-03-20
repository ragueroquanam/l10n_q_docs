# -*- coding: utf-8 -*-
{
    'name': 'Batch Reconciliation Queue',
    'version': '18.0.3.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'High-performance batch reconciliation with queue_job for 5000+ records',
    'description': """
Batch Reconciliation Queue
==========================

Solución de alto rendimiento para conciliación bancaria de lotes con más de 5000 pagos.

Arquitectura (v3.0):
-------------------
* Division del trabajo en chunks independientes de 500 pagos
* Cada chunk se procesa como un job separado en queue_job
* Procesamiento paralelo con límite configurable
* **NUEVO**: Separación de creación de líneas y conciliación
* **NUEVO**: Conciliación manual por lotes o encolada en background
* Cada job dura < 10 minutos (compatible con Odoo.sh 15 min timeout)

Flujo de Estados:
----------------
1. draft → preparing → processing (chunks en paralelo)
2. processing → lines_created (asiento creado, pendiente conciliar)
3. lines_created → reconciling (conciliación en progreso)
4. reconciling → reconciled (completado)

Conciliación Flexible:
---------------------
* Botón "Reconcile Batch": concilia N pares manualmente con feedback
* Botón "Queue Reconciliation": encola toda la conciliación en background
* Progreso visual en tiempo real
* Reanudación desde el último punto en caso de fallo

Optimizaciones SQL:
------------------
* Índices optimizados para consultas de reconciliación
* Bulk prefetch de datos relacionados
* SQL directo para operaciones masivas
* Minimización de triggers ORM

Características:
---------------
* Progreso en tiempo real por chunk y por reconciliación
* Reintentos automáticos por chunk individual
* Notificaciones de completado/error
* Panel de monitoreo de jobs
* Compatibilidad total con integridad contable Odoo

Rendimiento Esperado:
--------------------
* 5,000 pagos: ~10-15 minutos (10 chunks de 500)
* 9,000 pagos: ~18-25 minutos (18 chunks de 500)
* Sin timeouts en Odoo.sh
    """,
    'author': 'Quanam',
    'website': 'https://www.quanam.com',
    'depends': [
        'account_accountant',
        'account_accountant_batch_payment',
        'account_batch_payment',
        'queue_job',
        'queue_job_cron_jobrunner',
        'queue_q'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/queue_job_channel_data.xml',
        'data/ir_config_parameter_data.xml',
        'data/ir_cron.xml',
        'views/batch_reconciliation_master_views.xml',
        'views/batch_reconciliation_chunk_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}
