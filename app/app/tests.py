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

    def test_subtract(self):
        """_summary_ Test the subtract function.
        """
        res = calc.subtract(5, 2)
        self.assertEqual(res, 3)

    def test_multiply(self):
        """_summary_ Test the multiply function.
        """
        res = calc.multiply(2, 3)
        self.assertEqual(res, 6)

    def test_divide(self):
        """_summary_ Test the divide function.
        """
        res = calc.divide(6, 2)
        self.assertEqual(res, 3)
