from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

User = get_user_model()

class AccountDeletionTests(APITestCase):
    def setUp(self):
        # Create a general user
        self.user = User.objects.create_user(
            email='delete_test@example.com',
            password='testpassword123',
            full_name='Delete Test User',
            user_type='general'
        )
        self.delete_url =Reverse = '/users/delete-account/' # Hardcoding url based on previous view knowledge if reverse fails or /users/delete-account/

    def test_delete_account_success(self):
        """
        Ensure a general user can delete their own account.
        """
        self.client.force_authenticate(user=self.user)
        # Using the direct URL path as observed in views.py context
        response = self.client.delete('/users/delete-account/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(User.objects.filter(email='delete_test@example.com').exists())

    def test_delete_account_unauthenticated(self):
        """
        Ensure unauthenticated users cannot delete accounts.
        """
        response = self.client.delete('/users/delete-account/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_account_wrong_role(self):
        """
        Ensure non-job-seekers (e.g. employers) cannot use this endpoint if restricted.
        The view logic restricts to ['general', 'agency_referred'].
        """
        employer = User.objects.create_user(
            email='employer_del@example.com',
            password='testpassword123',
            full_name='Test Employer',
            user_type='employer'
        )
        self.client.force_authenticate(user=employer)
        response = self.client.delete('/users/delete-account/')
        
        # Should be 403 Forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
