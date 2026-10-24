"""
Service des fichiers médias avec contrôle d'accès minimal pour les dossiers sensibles.

`django.views.static.serve` ne fait aucune vérification d'authentification par
lui-même : n'importe qui peut télécharger n'importe quel fichier sous MEDIA_ROOT
en connaissant son URL. Certains dossiers contiennent des données sensibles
(pièces d'identité, justificatifs officiels, pièces jointes de messagerie
privée, supports de cours réservés aux inscrits) et ne doivent donc pas être
accessibles sans être connecté et approuvé.

Ce n'est pas un contrôle d'accès complet par propriétaire/tenant (un membre
approuvé d'un FabLab pourrait techniquement accéder à un fichier sensible
d'un autre FabLab s'il en devine l'URL exacte) — juste un filtre "authentifié
et approuvé" sur les dossiers qui n'ont clairement rien à faire de public.
"""

from django.conf import settings
from django.http import HttpResponseForbidden
from django.views.static import serve as static_serve

PROTECTED_MEDIA_PREFIXES = (
    'user_dossiers/',
    'justificatifs/',
    'chat_attachments/',
    'workshop_resources/',
    'library_resources/',
)


def protected_media_view(request, path):
    if path.startswith(PROTECTED_MEDIA_PREFIXES):
        user = request.user
        if not user.is_authenticated:
            return HttpResponseForbidden("Connexion requise pour accéder à ce fichier.")
        if not (user.is_superuser or user.is_staff or getattr(user, 'is_approved', False)):
            return HttpResponseForbidden("Votre compte doit être approuvé pour accéder à ce fichier.")
    return static_serve(request, path, document_root=settings.MEDIA_ROOT)
