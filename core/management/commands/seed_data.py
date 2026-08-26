from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from fablabs.models import FabLab
from config.tenant_router import set_current_tenant, migrate_tenant
from equipment.models import EquipmentCategory, Equipment, MaintenanceTicket
from reservations.models import Certification, UserCertification, Reservation
from workshops.models import Workshop, WorkshopRegistration
from inventory.models import InventoryItem
from projects.models import Project


class Command(BaseCommand):
    help = "Initialise les tenants FabLab démo et peuple leurs bases respectives."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🚀 Initialisation de la base Master FabLabs..."))

        # 1. Création des Tenants Master
        labs_data = [
            {
                'name': 'FabLab Sorbonne Université',
                'slug': 'sorbonne',
                'contact_email': 'fablab@sorbonne-universite.fr',
                'city': 'Paris',
                'plan': 'UNIVERSITY',
            },
            {
                'name': 'Artilect FabLab Toulouse',
                'slug': 'artilect',
                'contact_email': 'contact@artilect.fr',
                'city': 'Toulouse',
                'plan': 'COMMUNITY',
            },
            {
                'name': 'OpenLab Tech Prototyping',
                'slug': 'openlab',
                'contact_email': 'info@openlab-tech.com',
                'city': 'Lyon',
                'plan': 'ENTERPRISE',
            },
        ]

        created_labs = []
        for d in labs_data:
            lab, created = FabLab.objects.get_or_create(
                slug=d['slug'],
                defaults=d
            )
            created_labs.append(lab)
            status = "créé" if created else "existant"
            self.stdout.write(f"   • FabLab Tenant : {lab.name} ({status})")

        # 2. Pour chaque tenant, exécution des migrations de schéma et population des données
        for lab in created_labs:
            self.stdout.write(self.style.WARNING(f"\n📦 Seeding du tenant : {lab.name} ({lab.slug})..."))
            
            # Migration du schéma tenant
            migrate_tenant(lab.slug)
            set_current_tenant(lab.slug)

            # Catégories d'Équipement
            cat_3d, _ = EquipmentCategory.objects.get_or_create(slug="impression-3d", defaults={"name": "Impression 3D", "icon": "printer"})
            cat_laser, _ = EquipmentCategory.objects.get_or_create(slug="decoupe-laser", defaults={"name": "Découpe Laser", "icon": "zap"})
            cat_cnc, _ = EquipmentCategory.objects.get_or_create(slug="usinage-cnc", defaults={"name": "Usinage CNC", "icon": "settings"})
            cat_elec, _ = EquipmentCategory.objects.get_or_create(slug="electronique", defaults={"name": "Électronique & IoT", "icon": "cpu"})

            # Machines
            m1, _ = Equipment.objects.get_or_create(
                slug="prusa-mk4-01",
                defaults={
                    "name": f"Prusa i3 MK4 #{lab.slug.upper()}",
                    "category": cat_3d,
                    "model_number": "Original Prusa MK4",
                    "status": "AVAILABLE",
                    "hourly_rate": 3.50,
                    "location_zone": "Atelier Impression FDM",
                    "power_watts": 350,
                    "safety_instructions": "Ne pas toucher la buse à 250°C. Nettoyer le plateau après utilisation.",
                }
            )

            m2, _ = Equipment.objects.get_or_create(
                slug="epilog-laser-60w",
                defaults={
                    "name": f"Découpe Laser Epilog 60W #{lab.slug.upper()}",
                    "category": cat_laser,
                    "model_number": "Epilog Fusion Pro 36",
                    "status": "AVAILABLE" if lab.slug != 'artilect' else "RESERVED",
                    "hourly_rate": 15.00,
                    "location_zone": "Salle Laser & Extraction",
                    "power_watts": 1200,
                    "requires_certification": True,
                    "safety_instructions": "Lunettes de protection laser obligatoires. Allumer l'extraction de fumées avant découpe.",
                }
            )

            m3, _ = Equipment.objects.get_or_create(
                slug="roland-cnc-srm20",
                defaults={
                    "name": f"Fraiseuse CNC Precision Roland #{lab.slug.upper()}",
                    "category": cat_cnc,
                    "model_number": "Roland MonoFab SRM-20",
                    "status": "AVAILABLE" if lab.slug != 'openlab' else "MAINTENANCE",
                    "hourly_rate": 12.00,
                    "location_zone": "Zone Usinage Propre",
                    "power_watts": 600,
                    "requires_certification": True,
                }
            )

            # Ticket de maintenance si en maintenance
            if m3.status == "MAINTENANCE":
                MaintenanceTicket.objects.get_or_create(
                    equipment=m3,
                    issue_title="Changement de fraise & recalibrage plateau",
                    defaults={
                        "reported_by_username": "FabManager",
                        "description": "Fraise 0.8mm cassée pendant usinage PCB. Remplacement en cours.",
                        "priority": "HIGH",
                        "status": "IN_PROGRESS",
                    }
                )

            # Certifications
            cert_laser, _ = Certification.objects.get_or_create(
                name="Habilitation Découpe Laser Niveau 2",
                category=cat_laser,
                defaults={
                    "level": "AUTONOMOUS",
                    "description": "Capacité à régler le focus, choisir les vitesses/puissances selon les matériaux et lancer des jobs découpe/gravure.",
                }
            )

            UserCertification.objects.get_or_create(
                user_username="maker_resident",
                certification=cert_laser,
                defaults={
                    "user_full_name": "Thomas Pesquet",
                    "is_active": True,
                }
            )

            # Réservations
            now = timezone.now()
            Reservation.objects.get_or_create(
                equipment=m1,
                user_username="sophie_m",
                defaults={
                    "user_full_name": "Sophie Martin",
                    "start_time": now - timedelta(hours=1),
                    "end_time": now + timedelta(hours=2),
                    "status": "APPROVED",
                    "total_cost": 7.00,
                    "project_description": "Impression boîtier capteur qualité de l'air.",
                }
            )

            # Ateliers
            w1, _ = Workshop.objects.get_or_create(
                slug=f"initiation-laser-{lab.slug}",
                defaults={
                    "title": "Initiation Prise en Main Découpe Laser",
                    "instructor_name": "Alexandre FabManager",
                    "description": "Formation pratique de 2h30 pour apprendre à préparer vos fichiers vectoriels (.SVG, .DXF) et manipuler la découpeuse laser en toute sécurité.",
                    "start_date": now + timedelta(days=3),
                    "end_date": now + timedelta(days=3, hours=2, minutes=30),
                    "price": 15.00 if lab.slug != 'sorbonne' else 0.00,
                    "max_seats": 8,
                }
            )

            # Inscriptions ateliers
            WorkshopRegistration.objects.get_or_create(
                workshop=w1,
                user_email="etudiant1@sorbonne.fr",
                defaults={
                    "user_full_name": "Julie Dupont",
                    "payment_status": "PAID",
                }
            )

            # Inventaire & Consommables
            InventoryItem.objects.get_or_create(
                name="Filament PLA 1.75mm Noir (1kg)",
                defaults={
                    "sku": "PLA-BLK-175",
                    "category": "Impression 3D",
                    "quantity": 12.00,
                    "unit": "SPOOL",
                    "min_threshold": 3.00,
                    "unit_price": 22.00,
                    "location": "Étagère A1",
                }
            )

            InventoryItem.objects.get_or_create(
                name="Plaque PMMA Plexiglas Translucide 3mm (60x40cm)",
                defaults={
                    "sku": "PMMA-3MM-CLR",
                    "category": "Découpe Laser",
                    "quantity": 2.00,  # Stock bas!
                    "unit": "SHEET",
                    "min_threshold": 5.00,
                    "unit_price": 14.50,
                    "location": "Râtelier Bois & Plastique",
                }
            )

            # Projets
            Project.objects.get_or_create(
                slug=f"lampe-design-laser-{lab.slug}",
                defaults={
                    "title": "Lampe d'Ambiance Géométrique en Contreplaqué",
                    "author_name": "Camille Maker",
                    "category": "Découpe Laser",
                    "description": "Lampe de chevet assemblée par emboîtement sans colle. Fichiers SVG pour contreplaqué bouleau 3mm avec douille E27.",
                    "license": "CC-BY-SA",
                    "is_public": True,
                }
            )

            self.stdout.write(self.style.SUCCESS(f"   ✓ Données peuplées pour le schéma : {lab.slug}"))

        self.stdout.write(self.style.SUCCESS("\n✨ Initialisation Multi-Tenant de FabOS terminée avec succès !"))
