from django.core.management.base import BaseCommand
from fablabs.models import FabLab
from config.tenant_router import migrate_tenant

class Command(BaseCommand):
    help = "Exécute les migrations de base de données pour l'ensemble des tenants (FabLabs) enregistrés."

    def handle(self, *args, **options):
        tenants = FabLab.objects.all()
        self.stdout.write(f"Migrating {tenants.count()} tenant(s)...")
        for fablab in tenants:
            self.stdout.write(f"-> Migrating tenant '{fablab.slug}' ({fablab.name})...")
            migrate_tenant(fablab.slug, verbosity=0)
        self.stdout.write(self.style.SUCCESS("Toutes les bases de données tenant ont été migrées avec succès !"))
