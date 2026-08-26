from django.db import models

class Workshop(models.Model):
    title = models.CharField("Titre de l'atelier", max_length=200)
    slug = models.SlugField("Slug", max_length=200, unique=True)
    instructor = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name="workshops_instructed")
    instructor_name = models.CharField("Formateur / Animateur (Nom)", max_length=150, blank=True)
    description = models.TextField("Description complète et programme")
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
