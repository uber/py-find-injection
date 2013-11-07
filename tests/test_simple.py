import os.path
from unittest import TestCase

import py_find_injection


SAMPLE_PATH = os.path.realpath(os.path.join(os.path.dirname(__file__), 'samples'))


class TestSimple(TestCase):
    def test_good_file(self):
        errors = py_find_injection.check(os.path.join(SAMPLE_PATH, 'good_script.py'))
        self.assertEqual(errors, [])

    def test_bad_file(self):
        errors = py_find_injection.check(os.path.join(SAMPLE_PATH, 'bad_script.py'))
        self.assertEqual(1, len(errors))
        self.assertEqual(errors[0].lineno, 6)
        self.assertEqual(errors[0].reason, 'string interpolation of SQL query')

    def test_interpolation_not_inline(self):
        errors = py_find_injection.check(os.path.join(SAMPLE_PATH, 'bad_script_2.py'))
        self.assertEqual(1, len(errors))
        self.assertEqual(errors[0].lineno, 7)
        self.assertEqual(errors[0].reason, 'string concatenation of SQL query')
