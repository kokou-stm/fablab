from decimal import Decimal
from django.test import Client
from django.urls import reverse
from config.test_utils import BaseTenantTestCase
from inventory.models import InventoryItem

class InventoryModelAndViewsTests(BaseTenantTestCase):
    def setUp(self):
        self.client = Client()
        self.item = InventoryItem.objects.create(
            name="Filament PLA Noir",
            sku="PLA-BLK",
            quantity=Decimal('2.00'),
            min_threshold=Decimal('5.00'),
            unit_price=Decimal('20.00')
        )

    def test_low_stock_property(self):
        self.assertTrue(self.item.is_low_stock)

        self.item.quantity = Decimal('10.00')
        self.item.save()
        self.assertFalse(self.item.is_low_stock)

    def test_inventory_list_view(self):
        response = self.client.get(reverse('inventory_list'))
        self.assertEqual(response.status_code, 200)

    def test_inventory_add_quantity_post(self):
        response = self.client.post(reverse('inventory_list'), {
            'item_id': self.item.id,
            'add_quantity': '5.00'
        })
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, Decimal('7.00'))
