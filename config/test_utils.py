from django.test import TestCase
from django.conf import settings
from config.tenant_router import set_current_tenant

class BaseTenantTestCase(TestCase):
    """Classe de base pour les tests unitaires supportant la création dynamique de bases tenants."""

    @classmethod
    def _databases_names(cls, include_mirrors=True):
        return list(settings.DATABASES.keys())

    def setUp(self):
        super().setUp()
        set_current_tenant(None)
