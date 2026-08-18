# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies Pvt. Ltd.

from odoo.tests.common import TransactionCase


class TestShCiDemoTask(TransactionCase):
    """Verify the demo task lifecycle."""

    def test_create_task_starts_in_draft(self):
        """A new task must start in draft state."""
        task = self.env['sh.ci.demo.task'].create({'name': 'CI task'})
        self.assertEqual(task.state, 'draft')

    def test_mark_done_changes_state(self):
        """The action must mark the task as done."""
        task = self.env['sh.ci.demo.task'].create({'name': 'CI task'})
        task.action_mark_done()
        self.assertEqual(task.state, 'done')
