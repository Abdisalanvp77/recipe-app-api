"""Tests for the health check endpoint."""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient


class HealthCheckTest(TestCase):
    def test_health_check(self):
        """Test the health check endpoint."""
        client = APIClient()
        url = reverse('health_check')
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'status': 'ok'})
