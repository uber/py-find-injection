#!/usr/bin/env python

import argparse
import ast
import sys

version_info = (0, 1, 1)
__version__ = '.'.join(map(str, version_info))


def stringify(node):
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return '%s.%s' % (stringify(node.value), node.attr)
    elif isinstance(node, ast.Subscript):
        return '%s[%s]' % (stringify(node.value), stringify(node.slice))
    elif isinstance(node, ast.Index):
        return stringify(node.value)
    elif isinstance(node, ast.Call):
        return '%s(%s, %s)' % (stringify(node.func), stringify(node.args), stringify(node.keywords))
    elif isinstance(node, list):
        return '[%s]' % (', '.join(stringify(n) for n in node))
    elif isinstance(node, ast.Str):
        return node.s
    else:
        return ast.dump(node)


class IllegalLine(object):
    def __init__(self, reason, node, filename):
        self.reason = reason
        self.lineno = node.lineno
        self.filename = filename
        self.node = node

    def __str__(self):
        return "%s:%d\t%s" % (self.filename, self.lineno, self.reason)

    def __repr__(self):
        return "IllegalLine<%s, %s:%s>" % (self.reason, self.filename, self.lineno)


def find_assignment_in_context(variable, context):
    if isinstance(context, (ast.FunctionDef, ast.Module, ast.For, ast.While, ast.With, ast.If)):
        for node in reversed(list(ast.iter_child_nodes(context))):
            if isinstance(node, ast.Assign):
                if variable in (stringify(c) for c in node.targets):
                    return node
    if getattr(context, 'parent', None):
        return find_assignment_in_context(variable, context.parent)
    else:
        return None


class Checker(ast.NodeVisitor):
    def __init__(self, filename, *args, **kwargs):
        self.filename = filename
        self.errors = []
        super(Checker, self).__init__(*args, **kwargs)

    def check_execute(self, node):
        if isinstance(node, ast.BinOp):
            if isinstance(node.op, ast.Mod):
                return IllegalLine('string interpolation of SQL query', node, self.filename)
            elif isinstance(node.op, ast.Add):
                return IllegalLine('string concatenation of SQL query', node, self.filename)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == 'format':
                    return IllegalLine('str.format called on SQL query', node, self.filename)
        elif isinstance(node, ast.Name):
            # now we need to figure out where that query is assigned. blargh.
            assignment = find_assignment_in_context(node.id, node)
            if assignment is not None:
                return self.check_execute(assignment.value)

    def visit_Call(self, node):
        function_name = stringify(node.func)
        if function_name.lower() in ('session.execute', 'cursor.execute'):
            node.args[0].parent = node
            node_error = self.check_execute(node.args[0])
            if node_error:
                self.errors.append(node_error)
        elif function_name.lower() == 'eval':
            self.errors.append(IllegalLine('eval() is just generally evil', node, self.filename))
        self.generic_visit(node)

    def visit(self, node):
        """Visit a node."""
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        """Called if no explicit visitor function exists for a node."""
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        item.parent = node
                        self.visit(item,)
            elif isinstance(value, ast.AST):
                value.parent = node
                self.visit(value)


def check(filename):
    c = Checker(filename=filename)
    with open(filename, 'r') as fobj:
        try:
            parsed = ast.parse(fobj.read(), filename)
            c.visit(parsed)
        except Exception:
            raise
    return c.errors


def main():
    parser = argparse.ArgumentParser(
        description='Look for patterns in python source files that might indicate SQL injection vulnerabilities',
        epilog='Exit status is 0 if all files are okay, 1 if any files have an error. Errors are printed to stdout'
    )
    parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    parser.add_argument('files', nargs='+', help='Files to check')
    args = parser.parse_args()

    errors = []
    for fname in args.files:
        these_errors = check(fname)
        if these_errors:
            print '\n'.join(str(e) for e in these_errors)
            errors.extend(these_errors)
    if errors:
        print '%d total errors' % len(errors)
        return 1
    else:
        return 0


if __name__ == '__main__':
    sys.exit(main())
