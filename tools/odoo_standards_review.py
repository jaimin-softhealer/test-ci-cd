# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies Pvt. Ltd.
#!/usr/bin/env python3
"""Suggestion-only checks for changed Odoo Python and XML files."""

import argparse
import ast
import json
from collections import Counter
from pathlib import Path


HEADER = [
    '# -*- coding: utf-8 -*-',
    '# Copyright (C) Softhealer Technologies Pvt. Ltd.',
]
ORM_METHODS = {'create', 'write', 'unlink'}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo-root', required=True)
    parser.add_argument('--changed-files-json', required=True)
    parser.add_argument('--json-output', required=True)
    parser.add_argument('--markdown-output', required=True)
    return parser.parse_args()


def finding(file_path, line, rule, message, suggestion):
    return {
        'file': str(file_path),
        'line': line,
        'rule': rule,
        'message': message,
        'suggestion': suggestion,
    }


def review_python(path):
    source = path.read_text(encoding='utf-8')
    lines = source.splitlines()
    findings = []
    if lines[:2] != HEADER:
        findings.append(finding(path, 1, 'file_header', 'Required Python header is missing.',
                                 'Use the exact two-line company header.'))
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        findings.append(finding(path, error.lineno or 1, 'syntax_error', str(error),
                                 'Fix the Python syntax error.'))
        return findings

    overrides = []
    for class_node in [node for node in tree.body if isinstance(node, ast.ClassDef)]:
        for method in [node for node in class_node.body if isinstance(node, ast.FunctionDef)]:
            if method.name in ORM_METHODS:
                overrides.append((method.name, method.lineno))
                calls_super = any(
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == method.name
                    and isinstance(node.func.value, ast.Call)
                    and isinstance(node.func.value.func, ast.Name)
                    and node.func.value.func.id == 'super'
                    for node in ast.walk(method)
                )
                if not calls_super:
                    findings.append(finding(
                        path, method.lineno, 'missing_super',
                        f'{method.name}() override does not call super().{method.name}().',
                        f'Call super().{method.name}() unless replacement is intentional.',
                    ))
            for node in ast.walk(method):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr == 'sudo' and not any('SUDO:' in line for line in lines[max(0, node.lineno - 3):node.lineno]):
                        findings.append(finding(path, node.lineno, 'sudo_comment',
                                                 'sudo() has no nearby SUDO justification.',
                                                 'Add a short SUDO: comment explaining the business need.'))
                    if node.func.attr == 'execute' and node.args and isinstance(node.args[0], (ast.JoinedStr, ast.BinOp)):
                        findings.append(finding(path, node.lineno, 'unsafe_sql',
                                                 'SQL appears to be built dynamically.',
                                                 'Use parameterized SQL values.'))

    for method_name, count in Counter(name for name, _ in overrides).items():
        if count > 1:
            line = next(line for name, line in overrides if name == method_name)
            findings.append(finding(path, line, 'multiple_overrides',
                                     f'{method_name}() is overridden {count} times in this file.',
                                     f'Consolidate {method_name}() into one override or helper flow.'))
    return findings


def review_file(path):
    if path.suffix == '.py':
        return review_python(path)
    if path.suffix == '.xml':
        return [finding(path, number, 'controller_auth_none', 'auth="none" is not allowed.',
                        'Use auth="user" or a justified auth="public" route.')
                for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1)
                if 'auth="none"' in line or "auth='none'" in line]
    return []


def main():
    args = parse_args()
    root = Path(args.repo_root).resolve()
    findings = []
    for relative in json.loads(args.changed_files_json):
        path = (root / relative).resolve()
        if path.is_file():
            findings.extend(review_file(path))
    Path(args.json_output).write_text(json.dumps(findings, indent=2), encoding='utf-8')
    markdown = ['## Odoo Standards Review', '', f'Found {len(findings)} suggestion(s).', '']
    for item in findings:
        markdown.append(f"- `{item['file']}:{item['line']}` **{item['rule']}**: {item['message']} {item['suggestion']}")
    Path(args.markdown_output).write_text('\n'.join(markdown) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
