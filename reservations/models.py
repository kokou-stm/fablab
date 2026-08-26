from django.db import models
from equipment.models import Equipment, EquipmentCategory

class Certification(models.Model):
    LEVEL_CHOICES = [
        ('NOVICE', 'Niveau 1 : Initiation / Assisté'),
        ('AUTONOMOUS', 'Niveau 2 : Autonome'),
        ('EXPERT', 'Niveau 3 : Expert / Formateur'),
    ]

    name = models.CharField("Nom de l'habilitation", max_length=150)
    category = models.ForeignKey(EquipmentCategory, on_delete=models.CASCADE, related_name="certifications")
    level = models.CharField("Niveau d'habilitation", max_length=20, choices=LEVEL_CHOICES, default='AUTONOMOUS')
    description = models.TextField("Description des prérequis et compétences valides", blank=True)

    class Meta:
        verbose_name = "Certification / Habilitation"
        verbose_name_plural = "Certifications & Habilitations"

    def __str__(self):
        return f"{self.name} [{self.get_level_display()}]"


class UserCertification(models.Model):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, null=True, blank=True, related_name="user_certifications")
    user_username = models.CharField("Nom d'utilisateur", max_length=150)
    user_full_name = models.CharField("Nom complet du membre", max_length=200)
    certification = models.ForeignKey(Certification, on_delete=models.CASCADE, related_name="user_certifications")
    granted_at = models.DateField("Accordée le", auto_now_add=True)
    expires_at = models.DateField("Expire le", null=True, blank=True)
    is_active = models.BooleanField("Valide", default=True)

    class Meta:
        verbose_name = "Habilitation Membre"
        verbose_name_plural = "Habilitations Membres"

    def __str__(self):
        return f"{self.user_full_name} -> {self.certification.name}"


class Reservation(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'En Attente de Validation'),
        ('APPROVED', 'Confirmée'),
        ('ACTIVE', 'En cours d\'utilisation'),
        ('COMPLETED', 'Terminée'),
        ('CANCELLED', 'Annulée'),
    ]

    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name="reservations")
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, null=True, blank=True, related_name="reservations")
    user_username = models.CharField("Nom d'utilisateur", max_length=150)
    user_full_name = models.CharField("Nom complet", max_length=200)
    start_time = models.DateTimeField("Heure de Début")
    end_time = models.DateTimeField("Heure de Fin")
    status = models.CharField("Statut", max_length=20, choices=STATUS_CHOICES, default='PENDING')
    total_cost = models.DecimalField("Cout Total (€)", max_digits=8, decimal_places=2, default=0.00)
    project_description = models.TextField("Description du travail à réaliser", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Réservation"
        verbose_name_plural = "Réservations"
        ordering = ["-start_time"]

    def __str__(self):
        return f"{self.equipment.name} - {self.user_full_name} ({self.start_time.strftime('%d/%m %H:%M')})"
