import os
import logging
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator

logger = logging.getLogger(__name__)

def get_base_url(tenant=None):
    """Génère l'URL de base propre avec sous-domaine (https://polytech-lome.aidubber.fr en prod)."""
    base_domain = os.environ.get('DJANGO_BASE_DOMAIN', 'aidubber.fr')
    if not getattr(settings, 'DEBUG', True):
        if tenant and getattr(tenant, 'domain', None) and getattr(tenant, 'domain_verified', False):
            return f"https://{tenant.domain}"
        if tenant and getattr(tenant, 'slug', None):
            return f"https://{tenant.slug}.{base_domain}"
        return f"https://{base_domain}"
    else:
        if tenant and getattr(tenant, 'slug', None):
            return f"http://{tenant.slug}.localhost:8000"
        return "http://127.0.0.1:8000"

def get_tenant_login_url(tenant):
    return f"{get_base_url(tenant)}/login/"


def send_tenant_registered_email(fablab, user):
    """Envoie une notification par email lors de la création d'un nouvel espace FabLab."""
    login_url = get_tenant_login_url(fablab)
    subject = f"[LabOS] Demande de création d'espace FabLab : {fablab.name}"
    message = (
        f"Bonjour {user.get_full_name() or user.username},\n\n"
        f"Votre demande de création de l'espace FabLab '{fablab.name}' a été enregistrée .\n"
        f"Votre document justificatif a été transmis à l'équipe SuperAdmin pour vérification.\n\n"
        f"Identifiant de l'espace (slug) : {fablab.slug}\n"
        f"Plan tarifaire : {fablab.get_plan_display()}\n"
        f"Nom d'utilisateur administrateur : {user.username}\n\n"
        f"🔗 Lien de connexion à votre espace :\n"
        f"{login_url}\n\n"
        f"Vous recevrez une notification dès que votre espace sera validé.\n\n"
        f"L'équipe LabOS Platform."
    )
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@labos.com'),
            recipient_list=[user.email, fablab.contact_email],
            fail_silently=True
        )
    except Exception as e:
        logger.error(f"Erreur d'envoi d'email tenant: {e}")


def send_member_signup_notification(user, tenant):
    """Notification initiale d'inscription envoyée au membre et au FabManager."""
    lab_name = tenant.name if tenant else "LabOS"
    members_url = f"{get_base_url(tenant)}/members/"
    
    # 1. Email d'attente pour le nouveau membre (dossier en cours d'examen)
    member_subject = f"[LabOS] Inscription enregistrée - En cours d'examen"
    member_message = (
        f"Bonjour {user.get_full_name() or user.username},\n\n"
        f"Votre demande d'inscription sur l'espace FabLab '{lab_name}' a bien été reçue.\n\n"
        f" Statut de votre demande : Votre dossier est actuellement en cours d'examen par le responsable (FabManager) de votre établissement.\n"
        f"Vous recevrez un e-mail de confirmation dès que vos accès auront été validés.\n\n"
        f"L'équipe {lab_name}."
    )
    
    # 2. Email de notification pour le FabManager
    manager_subject = f"[LabOS] Inscription en attente de validation"
    manager_message = (
        f"Bonjour,\n\n"
        f"Un nouveau membre ({user.get_full_name() or user.username} - {user.email}) s'est inscrit sur l'espace {lab_name}.\n"
        f"Profil demandé : {user.get_role_display()}\n\n"
        f"Veuillez vous rendre dans l'annuaire des membres pour examiner son dossier et valider sa demande :\n"
        f"{members_url}\n\n"
        f"Plateforme LabOS."
    )
    
    try:
        send_mail(member_subject, member_message, getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@labos.com'), [user.email], fail_silently=True)
        if tenant and tenant.contact_email:
            send_mail(manager_subject, manager_message, getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@labos.com'), [tenant.contact_email], fail_silently=True)
    except Exception as e:
        logger.error(f"Erreur d'envoi d'email membre: {e}")



def send_member_approved_email(user):
    """Notification d'approbation finale envoyée lors de la validation : invite à créer son mot de passe.

    Le compte est créé sans mot de passe lors de l'inscription ; ce n'est qu'après
    validation par le FabManager (ou le SuperAdmin pour un FabManager) que le
    membre peut en définir un, via un lien de création à usage unique.
    """
    lab_name = user.fablab.name if user.fablab else "LabOS"
    base_url = get_base_url(user.fablab)

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    set_password_url = f"{base_url}/password-reset/confirm/{uid}/{token}/"

    subject = f"[LabOS] Compte validé — Créez votre mot de passe - {lab_name}"
    message = (
        f"Félicitations {user.get_full_name() or user.username} !\n\n"
        f"Votre compte membre a été validé  par le responsable du FabLab '{lab_name}'.\n\n"
        f" Votre identifiant de connexion : {user.username}\n\n"
        f" Dernière étape : créez votre mot de passe pour activer votre compte :\n"
        f"{set_password_url}\n\n"
        f"Vous pourrez ensuite vous connecter et réserver les machines et équipements disponibles.\n\n"
        f"Bienvenue et bonne création !\n\n"
        f"L'équipe {lab_name}."
    )
    try:
        send_mail(subject, message, getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@labos.com'), [user.email], fail_silently=True)
    except Exception as e:
        logger.error(f"Erreur d'envoi d'email de confirmation d'inscription: {e}")


def send_member_rejected_email(user):
    """Notification envoyée au candidat lorsque sa demande d'inscription est refusée."""
    lab_name = user.fablab.name if user.fablab else "LabOS"

    subject = f"[LabOS] Votre demande d'inscription - {lab_name}"
    message = (
        f"Bonjour {user.get_full_name() or user.username},\n\n"
        f"Nous vous informons que votre demande d'inscription sur l'espace FabLab '{lab_name}' n'a pas été retenue par le responsable.\n\n"
        f"Si vous pensez qu'il s'agit d'une erreur ou souhaitez plus d'informations, "
        f"nous vous invitons à contacter directement le FabLab.\n\n"
        f"L'équipe {lab_name}."
    )
    try:
        send_mail(subject, message, getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@labos.com'), [user.email], fail_silently=True)
    except Exception as e:
        logger.error(f"Erreur d'envoi d'email de refus d'inscription: {e}")


def send_member_info_request_email(user, custom_message):
    """Envoie un email au candidat pour lui demander des informations ou pièces complémentaires."""
    lab_name = user.fablab.name if user.fablab else "LabOS"
    login_url = get_tenant_login_url(user.fablab)
    
    subject = f"[LabOS] Demande d'informations complémentaires - {lab_name}"
    message = (
        f"Bonjour {user.get_full_name() or user.username},\n\n"
        f"Le FabManager / Responsable de votre espace FabLab '{lab_name}' a examiné votre dossier d'inscription et sollicite des précisions complémentaires :\n\n"
        f"💬 Message du FabManager :\n"
        f"« {custom_message} »\n\n"
        f" Statut de votre demande : En attente de complément d'informations.\n\n"
        f" Veuillez vous connecter pour mettre à jour votre dossier ou transmettre la pièce demandée :\n"
        f"{login_url}\n\n"
        f"L'équipe {lab_name}."
    )
    try:
        send_mail(subject, message, getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@labos.com'), [user.email], fail_silently=True)
    except Exception as e:
        logger.error(f"Erreur d'envoi d'email de demande d'informations: {e}")


def send_reservation_request_email(reservation, tenant):
    """Prévient les responsables du FabLab qu'une réservation attend leur validation."""
    lab_name = tenant.name if tenant else "LabOS"
    reservations_url = f"{get_base_url(tenant)}/reservations/"

    # Responsables du FabLab + adresse de contact de l'espace, sans doublon.
    recipients = []
    if tenant:
        from accounts.models import User
        recipients = list(
            User.objects.filter(
                fablab=tenant, role__in=['FABMANAGER', 'ADMIN'], is_approved=True
            ).exclude(email='').values_list('email', flat=True)
        )
        if tenant.contact_email:
            recipients.append(tenant.contact_email)
    recipients = sorted(set(r for r in recipients if r))
    if not recipients:
        return

    subject = f"[LabOS] Nouvelle demande de réservation - {reservation.equipment.name}"
    message = (
        f"Bonjour,\n\n"
        f"Une nouvelle demande de réservation attend votre validation sur l'espace '{lab_name}'.\n\n"
        f"• Machine : {reservation.equipment.name}\n"
        f"• Demandeur : {reservation.user_full_name}\n"
        f"• Créneau : du {reservation.start_time.strftime('%d/%m/%Y à %H:%M')} "
        f"au {reservation.end_time.strftime('%d/%m/%Y à %H:%M')}\n"
        f"• Coût estimé : {reservation.total_cost} €\n"
        + (f"• Description du travail : {reservation.project_description}\n" if reservation.project_description else "")
        + f"\n🔗 Valider ou refuser la demande :\n{reservations_url}\n\n"
        f"L'équipe {lab_name}."
    )
    try:
        send_mail(subject, message, getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@labos.com'), recipients, fail_silently=True)
    except Exception as e:
        logger.error(f"Erreur d'envoi d'email de demande de réservation: {e}")


def send_reservation_decision_email(reservation, approved):
    """Informe le membre que sa réservation a été confirmée ou refusée."""
    user = reservation.user
    if not user or not user.email:
        return
    tenant = getattr(user, 'fablab', None)
    lab_name = tenant.name if tenant else "LabOS"
    reservations_url = f"{get_base_url(tenant)}/reservations/"

    creneau = (
        f"du {reservation.start_time.strftime('%d/%m/%Y à %H:%M')} "
        f"au {reservation.end_time.strftime('%d/%m/%Y à %H:%M')}"
    )
    if approved:
        subject = f"[LabOS] Réservation confirmée - {reservation.equipment.name}"
        message = (
            f"Bonjour {user.get_full_name() or user.username},\n\n"
            f"Votre réservation a été confirmée par le responsable du FabLab '{lab_name}'.\n\n"
            f"• Machine : {reservation.equipment.name}\n"
            f"• Créneau : {creneau}\n\n"
            f"🔗 Voir vos réservations :\n{reservations_url}\n\n"
            f"L'équipe {lab_name}."
        )
    else:
        subject = f"[LabOS] Réservation refusée - {reservation.equipment.name}"
        message = (
            f"Bonjour {user.get_full_name() or user.username},\n\n"
            f"Votre demande de réservation n'a pas été retenue par le responsable du FabLab '{lab_name}'.\n\n"
            f"• Machine : {reservation.equipment.name}\n"
            f"• Créneau demandé : {creneau}\n\n"
            f"Vous pouvez proposer un autre créneau depuis votre espace :\n{reservations_url}\n\n"
            f"L'équipe {lab_name}."
        )
    try:
        send_mail(subject, message, getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@labos.com'), [user.email], fail_silently=True)
    except Exception as e:
        logger.error(f"Erreur d'envoi d'email de décision de réservation: {e}")
