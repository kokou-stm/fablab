from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [
        ('ADMIN', 'Administrateur Système'),
        ('FABMANAGER', 'FabManager / Gestionnaire'),
        ('INSTRUCTOR', 'Formateur / Inscruteur'),
        ('MAKER', 'Maker Résident'),
        ('STUDENT', 'Étudiant / Stagiaire'),
    ]

    role = models.CharField("Rôle utilisateur", max_length=20, choices=ROLE_CHOICES, default='MAKER')
    fablab = models.ForeignKey('fablabs.FabLab', on_delete=models.SET_NULL, null=True, blank=True, related_name="users")
    phone = models.CharField("Téléphone", max_length=30, blank=True)
    rfid_card_id = models.CharField("Identifiant Carte RFID / Badge", max_length=100, blank=True, null=True, unique=True)
    bio = models.TextField("Bio / Compétences", blank=True)
    avatar = models.ImageField("Photo de profil", upload_to="avatars/", blank=True, null=True)
    dossier_document = models.FileField("Justificatif / Carte Étudiant / Document Dossier", upload_to="user_dossiers/", blank=True, null=True)
    is_certified = models.BooleanField("Est habilité / Certifié", default=False)
    is_approved = models.BooleanField("Compte Approuvé / Validé par le Responsable", default=False)

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_admin_user(self):
        return self.is_superuser or self.role == 'ADMIN'

    @property
    def is_fabmanager_user(self):
        return self.is_admin_user or self.role == 'FABMANAGER'

    @property
    def is_instructor_user(self):
        return self.is_fabmanager_user or self.role == 'INSTRUCTOR'

    @property
    def is_maker_user(self):
        return self.role in ['MAKER', 'STUDENT']


class Subscription(models.Model):
    PLAN_CHOICES = [
        ('STUDENT', 'Pass Étudiant (15€/mois)'),
        ('MAKER_MONTHLY', 'Abonnement Maker (30€/mois)'),
        ('MAKER_ANNUAL', 'Abonnement Maker Annuel (300€/an)'),
        ('PRO', 'Abonnement Entreprise / Pro (100€/mois)'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscriptions")
    plan_type = models.CharField("Formule d'abonnement", max_length=30, choices=PLAN_CHOICES, default='MAKER_MONTHLY')
    start_date = models.DateField("Date de début")
    end_date = models.DateField("Date d'échéance")
    price = models.DecimalField("Montant (€)", max_digits=8, decimal_places=2, default=30.00)
    is_active = models.BooleanField("Actif", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Abonnement Membre"
        verbose_name_plural = "Abonnements Membres"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.get_plan_type_display()} ({'Actif' if self.is_active else 'Expiré'})"

