# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies Pvt. Ltd.

{
    'name': 'CI Demo',
    'version': '18.0.1.0.0',
    'author': 'Softhealer Technologies',
    'license': 'LGPL-3',
    'category': 'Tools',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/sh_ci_demo_task_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'description': 'Small Odoo module used to verify local webhook CI.',
}
