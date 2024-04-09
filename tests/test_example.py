import unittest


def add(a, b):
    """
    Adds two numbers together.
    
    Args:
        a (int or float): The first number.
        b (int or float): The second number.
        
    Returns:
        int or float: The sum of the two numbers.
    """
    return a + b


class TestAddFunction(unittest.TestCase):
    def test_add_integers(self):
        result = add(3, 4)
        self.assertEqual(result, 7)
        self.assertIsInstance(result, int)

    def test_add_floats(self):
        result = add(3.5, 2.5)
        self.assertAlmostEqual(result, 6.0)
        self.assertIsInstance(result, float)

    def test_add_negative_numbers(self):
        result = add(-3, -4)
        self.assertEqual(result, -7)
        self.assertIsInstance(result, int)

    def test_add_mixed_types(self):
        result = add(3, 4.5)
        self.assertAlmostEqual(result, 7.5)
        self.assertIsInstance(result, float)
