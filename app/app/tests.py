"""_summary_ Unit tests for the calc module.
"""
from django.test import SimpleTestCase

from app import calc

class CalcTests(SimpleTestCase):
    """_summary_ Test the calc module.
    """
    def test_add(self):
        """_summary_ Test the add function.
        """
        res = calc.add(2, 3)
        self.assertEqual(res, 5)