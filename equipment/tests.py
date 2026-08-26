from django.test import Client
from django.urls import reverse
from config.test_utils import BaseTenantTestCase
from accounts.models import User
from equipment.models import EquipmentCategory, Equipment, MaintenanceTicket

class EquipmentModelTests(BaseTenantTestCase):
    def setUp(self):
        self.category = EquipmentCategory.objects.create(
            name="Impression 3D",
            slug="impression-3d",
            icon="printer"
        )
        self.equipment = Equipment.objects.create(
            name="Prusa MK4",
            slug="prusa-mk4",
            category=self.category,
            status="AVAILABLE",
            hourly_rate=5.00,
            location_zone="Atelier 3D"
        )

    def test_equipment_creation(self):
        self.assertEqual(self.equipment.category, self.category)
        self.assertEqual(self.equipment.status, "AVAILABLE")

    def test_maintenance_ticket_creation(self):
        ticket = MaintenanceTicket.objects.create(
            equipment=self.equipment,
            reported_by_username="Maker",
            issue_title="Buse bouchée",
            description="Buse 0.4mm obstruée",
            priority="MEDIUM",
            status="OPEN"
        )
        self.assertEqual(ticket.equipment, self.equipment)
        self.assertEqual(ticket.status, "OPEN")


class EquipmentViewsTests(BaseTenantTestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="eq_user",
            email="eq@test.org",
            password="password123",
            role="MAKER",
            is_approved=True
        )
        self.client.login(username="eq_user", password="password123")
        self.category = EquipmentCategory.objects.create(
            name="Découpe Laser",
            slug="decoupe-laser",
            icon="zap"
        )
        self.equipment = Equipment.objects.create(
            name="Laser 60W",
            slug="laser-60w",
            category=self.category,
            status="AVAILABLE",
            hourly_rate=15.00
        )

    def test_equipment_list_view(self):
        response = self.client.get(reverse('equipment_list'))
        self.assertEqual(response.status_code, 200)

    def test_equipment_detail_view(self):
        response = self.client.get(reverse('equipment_detail', kwargs={'slug': self.equipment.slug}))
        self.assertEqual(response.status_code, 200)

    def test_maintenance_list_view_post(self):
        response = self.client.post(reverse('maintenance_list'), {
            'equipment_id': self.equipment.id,
            'issue_title': 'Moteur pas à pas bloqué',
            'description': 'Axe X bloqué',
            'priority': 'HIGH'
        })
        self.assertEqual(response.status_code, 302)
        ticket = MaintenanceTicket.objects.get(equipment=self.equipment)
        self.assertEqual(ticket.reported_by, self.user)
        self.assertEqual(ticket.reported_by_username, "eq_user")
