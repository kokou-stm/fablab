from datetime import timedelta
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from config.test_utils import BaseTenantTestCase
from accounts.models import User
from workshops.models import Workshop, WorkshopRegistration

class WorkshopsModelAndViewsTests(BaseTenantTestCase):
    def setUp(self):
        self.client = Client()
        now = timezone.now()
        self.workshop = Workshop.objects.create(
            title="Initiation Laser",
            slug="initiation-laser",
            instructor_name="Alex",
            description="Formation",
            start_date=now + timedelta(days=1),
            end_date=now + timedelta(days=1, hours=2),
            price=10.00,
            max_seats=5
        )

        self.user = User.objects.create_user(
            username="workshop_user",
            email="workshop@test.org",
            password="password123",
            role="MAKER",
            is_approved=True
        )
        self.client.login(username="workshop_user", password="password123")

    def test_workshop_seats(self):
        self.assertEqual(self.workshop.available_seats, 5)

        WorkshopRegistration.objects.create(
            workshop=self.workshop,
            user=self.user,
            user_full_name="Jean Dupont",
            user_email="jean@test.org",
            payment_status="PAID"
        )
        self.assertEqual(self.workshop.registered_count, 1)
        self.assertEqual(self.workshop.available_seats, 4)

    def test_workshop_list_and_register_post(self):
        response = self.client.get(reverse('workshop_list'))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('workshop_list'), {
            'workshop_id': self.workshop.id
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.workshop.registered_count, 1)

    def test_workshop_max_seats_enforcement(self):
        # Atelier avec 1 seule place disponible
        full_ws = Workshop.objects.create(
            title="Atelier Limité",
            slug="atelier-limite",
            instructor_name="Alex",
            description="Complet",
            start_date=timezone.now() + timedelta(days=2),
            end_date=timezone.now() + timedelta(days=2, hours=2),
            max_seats=1
        )
        # Première inscription
        self.client.post(reverse('workshop_list'), {'workshop_id': full_ws.id})
        self.assertEqual(full_ws.available_seats, 0)

        # Inscription d'un 2e membre sur l'atelier complet -> Doit être refusée
        user2 = User.objects.create_user(username="user2", email="user2@test.org", password="password123", is_approved=True)
        self.client.login(username="user2", password="password123")
        response = self.client.post(reverse('workshop_list'), {'workshop_id': full_ws.id})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(full_ws.registered_count, 1)
