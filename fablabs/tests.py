from django.test import Client
from django.urls import reverse
from config.test_utils import BaseTenantTestCase
from fablabs.models import FabLab

class FabLabModelAndViewsTests(BaseTenantTestCase):
    def setUp(self):
        self.client = Client()
        self.lab1 = FabLab.objects.create(
            name="FabLab Paris",
            slug="paris",
            contact_email="paris@fablab.org"
        )
        self.lab2 = FabLab.objects.create(
            name="FabLab Lyon",
            slug="lyon",
            contact_email="lyon@fablab.org"
        )

    def test_fablab_str(self):
        self.assertEqual(str(self.lab1), "FabLab Paris (paris)")

    def test_switch_tenant_view(self):
        response = self.client.get(reverse('switch_tenant', kwargs={'slug': 'lyon'}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get('tenant_slug'), 'lyon')
