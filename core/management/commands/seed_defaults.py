"""
Commande de management pour initialiser les données par défaut (catégories, canaux, tags).
Exécutée une seule fois au déploiement au lieu d'être appelée à chaque requête HTTP.
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Initialise les catégories d'équipement, canaux de messagerie et tags par défaut."

    def handle(self, *args, **options):
        self._seed_equipment_categories()
        self._seed_channels()
        self._seed_message_tags()
        self.stdout.write(self.style.SUCCESS("✓ Données par défaut initialisées avec succès."))

    def _seed_equipment_categories(self):
        from equipment.models import EquipmentCategory

        categories = [
            {"slug": "impression-3d", "defaults": {"name": "Impression 3D", "icon": "printer"}},
            {"slug": "decoupe-laser", "defaults": {"name": "Découpe Laser", "icon": "zap"}},
            {"slug": "usinage-cnc", "defaults": {"name": "Usinage CNC", "icon": "settings"}},
            {"slug": "electronique", "defaults": {"name": "Électronique & IoT", "icon": "cpu"}},
            {"slug": "autre", "defaults": {"name": "Autre", "icon": "box"}},
        ]
        created_count = 0
        for cat in categories:
            _, created = EquipmentCategory.objects.get_or_create(slug=cat["slug"], defaults=cat["defaults"])
            if created:
                created_count += 1
        self.stdout.write(f"  Catégories d'équipement : {created_count} créée(s)")

    def _seed_channels(self):
        from core.models import Channel

        channels = [
            {"slug": "general", "defaults": {"name": "Général & Discussion", "icon": "", "channel_type": "PUBLIC", "description": "Échanges libres et actualités du FabLab"}},
            {"slug": "annonces", "defaults": {"name": "Annonces Officielles", "icon": "", "channel_type": "PUBLIC", "description": "Communications officielles de l'équipe"}},
            {"slug": "entraide", "defaults": {"name": "Entraide & Projets", "icon": "", "channel_type": "HELP", "description": "Questions techniques, fichiers 3D, conseils découpe & électronique"}},
            {"slug": "maintenance", "defaults": {"name": "Pannes & Signalements", "icon": "", "channel_type": "HELP", "description": "Informations sur l'état des machines et incidents"}},
            {"slug": "fabmanagers", "defaults": {"name": "Espace FabManagers", "icon": "", "channel_type": "FABMANAGER", "description": "Canal restreint pour l'équipe d'administration"}},
        ]
        created_count = 0
        for ch in channels:
            _, created = Channel.objects.get_or_create(slug=ch["slug"], defaults=ch["defaults"])
            if created:
                created_count += 1
        self.stdout.write(f"  Canaux de messagerie : {created_count} créé(s)")

    def _seed_message_tags(self):
        from core.models import MessageTag

        tags = [
            {"slug": "projet", "defaults": {"name": "Projet", "color": "#3b82f6"}},
            {"slug": "panne", "defaults": {"name": "Panne / Maintenance", "color": "#ef4444"}},
            {"slug": "question", "defaults": {"name": "Question", "color": "#f59e0b"}},
            {"slug": "urgent", "defaults": {"name": "Urgent", "color": "#dc2626"}},
            {"slug": "habilitation", "defaults": {"name": "Habilitation", "color": "#8b5cf6"}},
            {"slug": "formation", "defaults": {"name": "Formation", "color": "#10b981"}},
        ]
        created_count = 0
        for tag in tags:
            _, created = MessageTag.objects.get_or_create(slug=tag["slug"], defaults=tag["defaults"])
            if created:
                created_count += 1
        self.stdout.write(f"  Tags de messagerie : {created_count} créé(s)")
