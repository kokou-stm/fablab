import os

from django.db import models


class LibraryResource(models.Model):
    """Ressource documentaire mise à disposition des membres d'un FabLab.

    Chaque établissement a sa propre bibliothèque (donnée de tenant) ;
    seuls les responsables de l'espace l'alimentent, tous les membres la consultent.
    """

    RESOURCE_TYPES = [
        ('BOOK', 'Livre / Ouvrage'),
        ('VIDEO', 'Vidéo (YouTube, Vimeo…)'),
        ('LINK', 'Lien / Site web'),
        ('DOCUMENT', 'Document à télécharger'),
        ('OTHER', 'Autre ressource'),
    ]

    CATEGORY_CHOICES = [
        ('PRINT3D', 'Impression 3D'),
        ('LASER', 'Découpe Laser'),
        ('CNC', 'Usinage CNC'),
        ('ELECTRONICS', 'Électronique & IoT'),
        ('CAD', 'Modélisation & CAO'),
        ('SAFETY', 'Sécurité & Bonnes pratiques'),
        ('GENERAL', 'Généraliste'),
    ]

    title = models.CharField("Titre", max_length=200)
    resource_type = models.CharField("Type de ressource", max_length=20, choices=RESOURCE_TYPES, default='LINK')
    category = models.CharField("Catégorie", max_length=30, choices=CATEGORY_CHOICES, default='GENERAL')
    description = models.TextField("Description / Résumé", blank=True)
    author = models.CharField("Auteur / Éditeur / Chaîne", max_length=200, blank=True)
    external_url = models.URLField("Lien externe (vidéo, site, fiche du livre)", max_length=500, blank=True, null=True)
    file = models.FileField("Fichier (PDF, ZIP…)", upload_to="library_resources/", blank=True, null=True)
    cover_image = models.ImageField("Couverture / Vignette", upload_to="library_covers/", blank=True, null=True)
    added_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name="library_resources"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ressource de bibliothèque"
        verbose_name_plural = "Bibliothèque"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.get_resource_type_display()})"

    @property
    def filename(self):
        return os.path.basename(self.file.name) if self.file else ''

    @property
    def youtube_id(self):
        """Identifiant de la vidéo YouTube, pour afficher la vignette officielle."""
        url = self.external_url or ''
        for marker in ('watch?v=', 'youtu.be/', 'embed/', 'shorts/'):
            if marker in url:
                candidate = url.split(marker, 1)[1]
                for sep in ('&', '?', '/', '#'):
                    candidate = candidate.split(sep, 1)[0]
                return candidate if candidate else None
        return None
