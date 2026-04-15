"""_summary_
Test for models.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model


class ModelTests(TestCase):
    """_summary_ Test models.
    """

    def test_create_user_with_email_successful(self):
        """_summary_ Test creating a new user with an email is successful.
        """
        email = 'test@example.com'
        password = 'testpass123'
        user = get_user_model().objects.create_user(email=email, password=password)

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normalized(self):
        """_summary_ Test the email for a new user is normalized.
        """
        sample_emails = [
            ['test@EXAMPLE.com', 'test@example.com'],
            ['TEST1@EXAMPLE.COM', 'TEST1@example.com'],
            ['Test2@Example.com', 'Test2@example.com'],
            ['TEST3@EXAMPLE.COM', 'TEST3@example.com'],
            ['TEST4@example.COM', 'TEST4@example.com'],
            ['Test5@example.COM', 'Test5@example.com']
        ]

        for email, expected in sample_emails:
            user = get_user_model().objects.create_user(email=email, password='testpass123')
            self.assertEqual(user.email, expected)
