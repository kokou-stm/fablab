from django.db import models
from django.conf import settings

class Project(models.Model):
    LICENSE_CHOICES = [
        ('CC-BY-SA', 'Creative Commons BY-SA 4.0'),
        ('CC-BY-NC', 'Creative Commons Non-Commercial'),
        ('MIT', 'Licence MIT (Open Source)'),
        ('CERN-OHL', 'CERN Open Hardware Licence'),
    ]

    title = models.CharField("Titre du projet", max_length=200)
    slug = models.SlugField("Slug", max_length=200, unique=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="projects")
    author_name = models.CharField("Auteur / Maker", max_length=150)
    category = models.CharField("Domaine / Spécialité", max_length=100, default="Impression 3D & IoT")
    description = models.TextField("Description complète et tutoriel d'assemblage")
    license = models.CharField("Licence Open Source", max_length=30, choices=LICENSE_CHOICES, default='CC-BY-SA')
    is_public = models.BooleanField("Projet Public sur le Hub", default=True)
    cover_image = models.ImageField("Image de couverture", upload_to="projects/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Projet Maker"
        verbose_name_plural = "Galerie de Projets Makers"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} par {self.author_name}"
