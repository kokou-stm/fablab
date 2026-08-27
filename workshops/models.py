import os
from django.db import models

class Workshop(models.Model):
    CATEGORY_CHOICES = [
        ('PRINT3D', 'Impression 3D'),
        ('LASER', 'Découpe Laser'),
        ('CNC', 'Usinage CNC'),
        ('ELECTRONICS', 'Électronique & IoT'),
        ('CAD', 'Modélisation & CAO'),
        ('GENERAL', 'Initiation & Sécurité'),
    ]

    title = models.CharField("Titre de l'atelier / formation", max_length=200)
    slug = models.SlugField("Slug", max_length=200, unique=True)
    category = models.CharField("Catégorie", max_length=30, choices=CATEGORY_CHOICES, default='GENERAL')
    instructor = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name="workshops_instructed")
    instructor_name = models.CharField("Formateur / Animateur (Nom)", max_length=150, blank=True)
    description = models.TextField("Description complète et objectifs de la formation")
    start_date = models.DateTimeField("Date & Heure de Début")
    end_date = models.DateTimeField("Date & Heure de Fin")
    price = models.DecimalField("Prix d'entrée (€)", max_digits=8, decimal_places=2, default=0.00)
    max_seats = models.IntegerField("Places maximales", default=10)
    image = models.ImageField("Image d'illustration", upload_to="workshops/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Atelier & Formation"
        verbose_name_plural = "Ateliers & Formations"
        ordering = ["start_date"]

    def __str__(self):
        return f"{self.title} ({self.start_date.strftime('%d/%m/%Y')})"

    @property
    def registered_count(self):
        return self.registrations.count()

    @property
    def available_seats(self):
        return max(0, self.max_seats - self.registered_count)


class WorkshopRegistration(models.Model):
    workshop = models.ForeignKey(Workshop, on_delete=models.CASCADE, related_name="registrations")
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, null=True, blank=True, related_name="workshop_registrations")
    user_full_name = models.CharField("Nom Complet du Participant", max_length=200)
    user_email = models.EmailField("Email", max_length=254)
    payment_status = models.CharField("Statut du Paiement", max_length=20, choices=[
        ('FREE', 'Gratuit'),
        ('PENDING', 'En Attente'),
        ('PAID', 'Payé'),
    ], default='PAID')
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Inscription Atelier"
        verbose_name_plural = "Inscriptions Ateliers"

    def __str__(self):
        return f"{self.user_full_name} -> {self.workshop.title}"


class CourseLesson(models.Model):
    workshop = models.ForeignKey(Workshop, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField("Titre du cours / chapitre", max_length=200)
    description = models.TextField("Contenu / Notes de cours", blank=True)
    video_url = models.URLField("Lien vidéo tutoriel (Tutoriel YouTube/Vimeo)", max_length=500, blank=True, null=True)
    order = models.PositiveIntegerField("Ordre d'affichage", default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cours / Chapitre"
        verbose_name_plural = "Cours / Chapitres"
        ordering = ["order", "created_at"]

    def __str__(self):
        return f"{self.workshop.title} - {self.title}"


class LessonResource(models.Model):
    RESOURCE_TYPES = [
        ('PDF', 'Document PDF'),
        ('DOC', 'Fichier Texte / Doc'),
        ('ARCHIVE', 'Fichier CAD / ZIP / STL / DXF'),
        ('LINK', 'Lien Web Utile'),
    ]

    lesson = models.ForeignKey(CourseLesson, on_delete=models.CASCADE, related_name="resources", null=True, blank=True)
    workshop = models.ForeignKey(Workshop, on_delete=models.CASCADE, related_name="direct_resources", null=True, blank=True)
    title = models.CharField("Titre du document / ressource", max_length=200)
    file = models.FileField("Fichier (PDF, ZIP, STL, etc.)", upload_to="workshop_resources/", blank=True, null=True)
    external_url = models.URLField("Lien Externe (optionnel)", max_length=500, blank=True, null=True)
    resource_type = models.CharField("Type de ressource", max_length=20, choices=RESOURCE_TYPES, default='PDF')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ressource de cours"
        verbose_name_plural = "Ressources de cours"

    def __str__(self):
        return f"{self.title} ({self.get_resource_type_display()})"

    @property
    def filename(self):
        if self.file:
            return os.path.basename(self.file.name)
        return self.title
