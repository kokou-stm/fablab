from datetime import timedelta
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from config.test_utils import BaseTenantTestCase
from accounts.models import User, Subscription
from fablabs.models import FabLab

class AccountsModelTests(BaseTenantTestCase):
    def setUp(self):
        self.fablab = FabLab.objects.create(
            name="FabLab Test",
            slug="test-lab",
            contact_email="test@fablab.org"
        )
        self.user = User.objects.create_user(
            username="test_maker",
            email="maker@test.org",
            password="password123",
            role="MAKER",
            fablab=self.fablab
        )
        self.fabmanager = User.objects.create_user(
            username="test_admin",
            email="admin@test.org",
            password="password123",
            role="FABMANAGER",
            fablab=self.fablab
        )

    def test_user_role_properties(self):
        self.assertTrue(self.user.is_maker_user)
        self.assertFalse(self.user.is_fabmanager_user)

        self.assertTrue(self.fabmanager.is_fabmanager_user)
        self.assertFalse(self.fabmanager.is_admin_user)

    def test_subscription_creation(self):
        sub = Subscription.objects.create(
            user=self.user,
            plan_type="MAKER_MONTHLY",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
            price=30.00,
            is_active=True
        )
        self.assertEqual(sub.user, self.user)
        self.assertTrue(sub.is_active)


class AccountsViewsTests(BaseTenantTestCase):
    def setUp(self):
        self.client = Client()
        self.fablab = FabLab.objects.create(
            name="FabLab Test",
            slug="test-lab",
            contact_email="test@fablab.org"
        )
        self.user = User.objects.create_user(
            username="test_maker",
            email="maker@test.org",
            password="password123",
            role="MAKER",
            fablab=self.fablab
        )
        self.fabmanager = User.objects.create_user(
            username="test_admin",
            email="admin@test.org",
            password="password123",
            role="FABMANAGER",
            fablab=self.fablab
        )

    def test_signup_view_get_and_post(self):
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('signup'), {
            'username': 'new_member',
            'email': 'new@test.org',
            'password': 'password123',
            'first_name': 'New',
            'last_name': 'Member',
            'role': 'MAKER'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='new_member').exists())

    def test_login_view_success_and_fail(self):
        response = self.client.post(reverse('login'), {
            'username': 'test_maker',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('login'), {
            'username': 'test_maker',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 302)

    def test_profile_view_requires_login(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)

        self.client.login(username='test_maker', password='password123')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)

    def test_member_list_view_permission(self):
        self.client.login(username='test_maker', password='password123')
        response = self.client.get(reverse('member_list'))
        self.assertEqual(response.status_code, 302)

        self.client.login(username='test_admin', password='password123')
        response = self.client.get(reverse('member_list'))
        self.assertEqual(response.status_code, 200)
