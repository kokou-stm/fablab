from datetime import timedelta
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from config.test_utils import BaseTenantTestCase
from equipment.models import EquipmentCategory, Equipment
from reservations.models import Certification, UserCertification, Reservation

class ReservationsModelAndViewsTests(BaseTenantTestCase):
    def setUp(self):
        self.client = Client()
        self.category = EquipmentCategory.objects.create(
            name="Impression 3D",
            slug="impression-3d"
        )
        self.equipment = Equipment.objects.create(
            name="Prusa i3",
            slug="prusa-i3",
            category=self.category,
            hourly_rate=4.00
        )
        now = timezone.now()
        self.reservation = Reservation.objects.create(
            equipment=self.equipment,
            user_username="maker1",
            user_full_name="Maker One",
            start_time=now,
            end_time=now + timedelta(hours=2),
            status="APPROVED",
            total_cost=8.00
        )

    def test_reservation_creation(self):
        self.assertEqual(self.reservation.equipment, self.equipment)
        self.assertEqual(self.reservation.total_cost, 8.00)

    def test_reservation_list_view(self):
        response = self.client.get(reverse('reservation_list'))
        self.assertEqual(response.status_code, 200)

    def test_reservation_cancel_view(self):
        response = self.client.post(reverse('reservation_cancel', kwargs={'pk': self.reservation.pk}))
        self.assertEqual(response.status_code, 302)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, "CANCELLED")

    def test_reservation_calendar_api(self):
        response = self.client.get(reverse('reservation_calendar_api'))
        self.assertEqual(response.status_code, 200)

    def test_usage_history_view(self):
        response = self.client.get(reverse('usage_history'))
        self.assertEqual(response.status_code, 200)
