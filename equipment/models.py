from django.db import models
from django.conf import settings

class EquipmentCategory(models.Model):
    name = models.CharField("Catégorie", max_length=100)
    slug = models.SlugField("Slug", max_length=100, unique=True)
    icon = models.CharField("Icône SVG / CSS", max_length=50, default="cpu")
    description = models.TextField("Description", blank=True)

    class Meta:
        verbose_name = "Catégorie d'Équipement"
        verbose_name_plural = "Catégories d'Équipements"

    def __str__(self):
        return self.name


class Equipment(models.Model):
    STATUS_CHOICES = [
        ('AVAILABLE', 'Opérationnel / Disponible'),
        ('RESERVED', 'En Utilisation / Réservé'),
        ('MAINTENANCE', 'En Maintenance'),
        ('OFFLINE', 'Hors Service'),
    ]

    name = models.CharField("Nom de la machine", max_length=150)
    slug = models.SlugField("Slug", max_length=150, unique=True)
    category = models.ForeignKey(EquipmentCategory, on_delete=models.CASCADE, related_name="equipments")
    model_number = models.CharField("Marque / Modèle", max_length=100, blank=True)
    serial_number = models.CharField("Numéro de Série", max_length=100, blank=True)
    status = models.CharField("Statut", max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')
    hourly_rate = models.DecimalField("Tarif Horaire (€)", max_digits=8, decimal_places=2, default=0.00)
    location_zone = models.CharField("Zone dans le FabLab", max_length=100, default="Atelier Principal")
    power_watts = models.IntegerField("Puissance (Watts)", default=500)
    description = models.TextField("Description / Caractéristiques", blank=True)
    safety_instructions = models.TextField("Consignes de Sécurité / EPI requis", blank=True)
    requires_certification = models.BooleanField("Nécessite une Habilitation/Formation", default=False)
    image = models.ImageField("Photo de la machine", upload_to="equipment/", blank=True, null=True)
    doc_file = models.FileField("Fichier Notice / Documentation (PDF)", upload_to="equipment_docs/", blank=True, null=True)
    doc_url = models.URLField("Lien Web Manuel / Tutoriel (URL)", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Équipement / Machine"
        verbose_name_plural = "Équipements & Machines"

    def __str__(self):
        return f"{self.name} [{self.get_status_display()}]"

    @property
    def current_active_reservation(self):
        from django.utils import timezone
        now = timezone.now()
        return self.reservations.filter(
            status__in=['APPROVED', 'ACTIVE'],
            start_time__lte=now,
            end_time__gte=now
        ).first()

    @property
    def is_currently_reserved(self):
        return self.status == 'RESERVED' or self.current_active_reservation is not None


class MaintenanceTicket(models.Model):
    PRIORITY_CHOICES = [
        ('LOW', 'Faible'),
        ('MEDIUM', 'Moyenne'),
        ('HIGH', 'Haute'),
        ('URGENT', 'Urgent / Machine Bloquée'),
    ]
    STATUS_CHOICES = [
        ('OPEN', 'Signalé'),
        ('IN_PROGRESS', 'En cours d\'intervention'),
        ('RESOLVED', 'Résolu / Réparé'),
    ]

    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name="maintenance_tickets")
    reported_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name="reported_tickets")
    reported_by_username = models.CharField("Rapporté par", max_length=150, default="Membre")
    issue_title = models.CharField("Titre du Problème", max_length=200)
    description = models.TextField("Description détaillée de la panne")
    priority = models.CharField("Priorité", max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.CharField("Statut", max_length=20, choices=STATUS_CHOICES, default='OPEN')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Ticket de Maintenance"
        verbose_name_plural = "Tickets de Maintenance"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_priority_display()}] {self.equipment.name} - {self.issue_title}"
