from datetime import timedelta
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from config.test_utils import BaseTenantTestCase
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

    def test_workshop_seats(self):
        self.assertEqual(self.workshop.available_seats, 5)

        WorkshopRegistration.objects.create(
            workshop=self.workshop,
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
            'workshop_id': self.workshop.id,
            'participant_name': 'Marie Curie',
            'participant_email': 'marie@test.org'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.workshop.registered_count, 1)
