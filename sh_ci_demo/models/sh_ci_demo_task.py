# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies Pvt. Ltd.

from odoo import fields, models


class ShCiDemoTask(models.Model):
    """Minimal task model used by the CI demonstration module."""

    _name = 'sh.ci.demo.task'
    _description = 'CI Demo Task'

    name = fields.Char(required=True)
    description = fields.Text()
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('done', 'Done'),
        ],
        default='draft',
        required=True,
        copy=False,
    )

    def action_mark_done(self):
        """Mark the selected tasks as completed."""
        self.write({'state': 'done'})
        return True
