from django.db import models

class Channel(models.Model):
    """Canaux de discussion généraux ou thématiques de l'espace FabLab."""
    CHANNEL_TYPES = [
        ('PUBLIC', 'Canal Public (Tout le FabLab)'),
        ('FABMANAGER', 'Canal Équipe FabManager'),
        ('GROUP', 'Groupe / Projet Sur Invitation'),
        ('HELP', 'Entraide & Support Makers'),
        ('DIRECT', 'Message Direct / Privé'),
    ]

    name = models.CharField("Nom du canal / Sujet", max_length=100)
    slug = models.SlugField("Slug", max_length=100)
    channel_type = models.CharField("Type", max_length=20, choices=CHANNEL_TYPES, default='PUBLIC')
    description = models.CharField("Description / Thème", max_length=255, blank=True)
    icon = models.CharField("Icône", max_length=10, default="")
    creator = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name="created_channels")
    members = models.ManyToManyField('accounts.User', blank=True, related_name="joined_channels")
    is_private = models.BooleanField("Privé sur invitation uniquement", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Canal de Discussion"
        verbose_name_plural = "Canaux de Discussion"
        ordering = ["id"]

    def __str__(self):
        return f"#{self.name}"


class MessageTag(models.Model):
    """Tags / Étiquettes de classement (ex: Projet, Urgent, Panne, Formation, Habilitation)."""
    name = models.CharField("Nom du Tag", max_length=50)
    slug = models.SlugField("Slug", max_length=50, unique=True)
    color = models.CharField("Couleur Badge CSS", max_length=30, default="#3b82f6")

    class Meta:
        verbose_name = "Tag de Message"
        verbose_name_plural = "Tags de Messages"

    def __str__(self):
        return self.name


class Message(models.Model):
    """Message émis dans un canal ou en message direct."""
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name="messages", null=True, blank=True)
    sender = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name="sent_chat_messages")
    sender_username = models.CharField("Auteur", max_length=150)
    sender_role = models.CharField("Rôle Auteur", max_length=50, default="Maker")
    recipient = models.ForeignKey('accounts.User', on_delete=models.CASCADE, null=True, blank=True, related_name="received_direct_chat_messages")
    content = models.TextField("Contenu du message")
    tags = models.ManyToManyField(MessageTag, blank=True, related_name="messages")
    attachment = models.FileField("Pièce jointe (Fichier / Photo)", upload_to="chat_attachments/", blank=True, null=True)
    is_announcement = models.BooleanField("Annonce officielle", default=False)
    is_read = models.BooleanField("Lu", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.sender_username}] {self.content[:40]}"


class ChannelReadStatus(models.Model):
    """Suivi de lecture des canaux de discussion par utilisateur (pour les badges de messages non lus style Discord/WhatsApp)."""
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name="channel_read_statuses")
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name="read_statuses")
    last_read_message = models.ForeignKey(Message, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'channel')
        verbose_name = "Statut de Lecture Canal"
        verbose_name_plural = "Statuts de Lecture Canaux"
