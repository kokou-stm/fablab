from django.db import models

class InventoryItem(models.Model):
    UNIT_CHOICES = [
        ('KG', 'Kilogrammes'),
        ('SPOOL', 'Bobines 1kg'),
        ('SHEET', 'Plaques / Feuilles'),
        ('PIECE', 'Pièces unitaire'),
        ('METER', 'Mètres'),
    ]

    name = models.CharField("Nom de l'article", max_length=150)
    sku = models.CharField("Code SKU / Référence", max_length=50, blank=True)
    category = models.CharField("Catégorie", max_length=100, default="Impression 3D")
    quantity = models.DecimalField("Quantité en stock", max_digits=10, decimal_places=2, default=0.00)
    unit = models.CharField("Unité de mesure", max_length=20, choices=UNIT_CHOICES, default='PIECE')
    min_threshold = models.DecimalField("Seuil d'alerte stock bas", max_digits=10, decimal_places=2, default=5.00)
    unit_price = models.DecimalField("Prix Unitaire Vente (€)", max_digits=8, decimal_places=2, default=0.00)
    location = models.CharField("Emplacement dans la réserve", max_length=100, default="Étagère A1")

    class Meta:
        verbose_name = "Article de Stock / Consommable"
        verbose_name_plural = "Inventaire & Consommables"

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.get_unit_display()})"

    @property
    def is_low_stock(self):
        return self.quantity <= self.min_threshold
