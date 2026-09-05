from django.db import models

class FabLab(models.Model):
    name = models.CharField("Nom du FabLab", max_length=150)
    slug = models.SlugField("Slug (identifiant unique)", max_length=100, unique=True)
    domain = models.CharField("Nom de domaine personnalisé", max_length=200, blank=True, null=True)
    domain_verified = models.BooleanField(
        "Domaine vérifié par le SuperAdmin",
        default=False,
        help_text="Tant que ce n'est pas coché, le domaine personnalisé est ignoré (les emails et liens utilisent le sous-domaine standard) pour éviter d'envoyer des liens morts si le DNS n'est pas réellement configuré.",
    )
    logo = models.ImageField("Logo", upload_to="fablab_logos/", blank=True, null=True)
    contact_email = models.EmailField("Email de contact", max_length=254)
    phone = models.CharField("Téléphone", max_length=30, blank=True)
    address = models.TextField("Adresse physique", blank=True)
    city = models.CharField("Ville", max_length=100, default="Paris")
    country = models.CharField("Pays", max_length=100, default="France")
    plan = models.CharField("Plan Tarifaire", max_length=50, choices=[
        ('COMMUNITY', 'Communautaire / Associatif'),
        ('UNIVERSITY', 'Universitaire / Éducation'),
        ('ENTERPRISE', 'Entreprise / Prototypage Pro'),
    ], default='COMMUNITY')
    is_active = models.BooleanField("Actif", default=True)
    is_approved = models.BooleanField("Approuvé par le SuperAdmin", default=False)
    justification_document = models.FileField("Justificatif officiel (KBIS, attestation)", upload_to="justificatifs/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "FabLab (Tenant)"
        verbose_name_plural = "FabLabs (Tenants)"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.slug})"
