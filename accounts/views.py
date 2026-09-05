from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.utils import timezone
from django.utils.text import slugify

from django.db.models import Sum, Q

from accounts.models import User, Subscription
from accounts.decorators import fabmanager_required, role_required, admin_required
from fablabs.models import FabLab
from reservations.models import Certification, UserCertification
from core.emails import send_member_signup_notification, send_member_approved_email, send_member_info_request_email, send_member_rejected_email

def login_view(request):
    """Vue de connexion membre (par Username ou par Email)."""
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.role == 'ADMIN':
            return redirect('superadmin_dashboard')
        if request.user.role == 'FABMANAGER' or request.user.is_approved:
            return redirect('dashboard')
        return redirect('landing')

    if request.method == 'POST':
        login_input = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        # Support de la connexion par Email ou Nom d'utilisateur
        username = login_input
        if '@' in login_input:
            user_by_email = User.objects.filter(email__iexact=login_input).first()
            if user_by_email:
                username = user_by_email.username

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.fablab:
                request.session['tenant_slug'] = user.fablab.slug

            if user.is_superuser or user.role == 'FABMANAGER' or user.is_approved:
                messages.success(request, f"Bienvenue, {user.get_full_name() or user.username} !")
                if user.is_superuser or user.role == 'ADMIN':
                    default_next = 'superadmin_dashboard'
                else:
                    default_next = 'dashboard'
                next_url = request.GET.get('next') or default_next
                return redirect(next_url)
            else:
                messages.info(request, f"Bienvenue {user.get_full_name() or user.username} ! Votre compte a été créé mais est en attente de validation par le FabManager. L'accès au Tableau de bord sera débloqué après validation.")
                return redirect('landing')
        else:
            messages.error(request, "Identifiant/Email ou mot de passe incorrect.")

    return render(request, 'accounts/login.html')


def logout_view(request):
    """Déconnexion de l'utilisateur."""
    logout(request)
    messages.info(request, "Vous avez été déconnecté avec succès.")
    return redirect('landing')


def signup_view(request):
    """Inscription d'un nouveau membre rattaché au FabLab actif (ou choisi dans la liste)."""
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.role == 'FABMANAGER' or request.user.is_approved:
            return redirect('dashboard')
        return redirect('landing')

    tenant = getattr(request, 'tenant', None)
    all_tenants = FabLab.objects.all()

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        role = request.POST.get('role', 'MAKER')
        fablab_id = request.POST.get('fablab_id')

        target_tenant = tenant
        if fablab_id:
            target_tenant = FabLab.objects.filter(id=fablab_id).first() or tenant

        if User.objects.filter(username=username).exists():
            messages.error(request, f"Le nom d'utilisateur '{username}' est déjà pris.")
            return render(request, 'accounts/signup.html', {'tenant': tenant, 'all_tenants': all_tenants})

        dossier_doc = request.FILES.get('dossier_document')

        # Aucun mot de passe à l'inscription : le membre en définit un lui-même
        # via un lien à usage unique, une fois son compte validé par le FabManager.
        user = User.objects.create_user(
            username=username,
            email=email,
            password=None,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role=role,
            fablab=target_tenant,
            dossier_document=dossier_doc,
            is_approved=False
        )

        # Création automatique d'un abonnement d'essai de 1 mois
        Subscription.objects.create(
            user=user,
            plan_type='STUDENT' if role == 'STUDENT' else 'MAKER_MONTHLY',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
            price=15.00 if role == 'STUDENT' else 30.00,
            is_active=True
        )

        # Notification email d'inscription
        send_member_signup_notification(user, target_tenant)

        login(request, user)
        if target_tenant:
            request.session['tenant_slug'] = target_tenant.slug
        
        return redirect('signup_pending')

    return render(request, 'accounts/signup.html', {'tenant': tenant, 'all_tenants': all_tenants})


def signup_pending_view(request):
    """Page d'information et de confirmation post-inscription (compte en attente de validation)."""
    return render(request, 'accounts/signup_pending.html')


def profile_view(request):
    """Vue et modification du profil membre avec gestion des abonnements."""
    if not request.user.is_authenticated:
        messages.warning(request, "Veuillez vous connecter pour voir votre profil.")
        return redirect('login')

    user = request.user
    user_subscriptions = Subscription.objects.filter(user=user)
    active_sub = user_subscriptions.filter(is_active=True).first()
    from django.db.models import Q
    user_certifications = UserCertification.objects.filter(Q(user=user) | Q(user_username=user.username))

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_profile':
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.phone = request.POST.get('phone', user.phone)
            user.bio = request.POST.get('bio', user.bio)
            if 'avatar' in request.FILES:
                user.avatar = request.FILES['avatar']
            user.save()
            messages.success(request, "Votre profil a été mis à jour avec succès !")
            return redirect('profile')

        elif action == 'renew_subscription':
            plan_type = request.POST.get('plan_type', 'MAKER_MONTHLY')
            days = 365 if plan_type == 'MAKER_ANNUAL' else 30
            price = 300.00 if plan_type == 'MAKER_ANNUAL' else (15.00 if plan_type == 'STUDENT' else 30.00)

            # Désactiver anciens abonnements
            Subscription.objects.filter(user=user, is_active=True).update(is_active=False)
            Subscription.objects.create(
                user=user,
                plan_type=plan_type,
                start_date=timezone.now().date(),
                end_date=timezone.now().date() + timedelta(days=days),
                price=price,
                is_active=True
            )
            messages.success(request, f"Abonnement renouvelé avec succès !")
            return redirect('profile')

    context = {
        'user_obj': user,
        'active_sub': active_sub,
        'user_subscriptions': user_subscriptions,
        'user_certifications': user_certifications,
    }
    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        return render(request, 'accounts/partials/profile_content.html', context)
    return render(request, 'accounts/profile.html', context)


@fabmanager_required
def member_list_view(request):
    """Annuaire des membres inscrit sur le tenant courant avec gestion des rôles et validation d'inscription."""
    tenant = getattr(request, 'tenant', None)
    if tenant:
        members = User.objects.filter(fablab=tenant).order_by('-date_joined')
    else:
        members = User.objects.all().order_by('-date_joined')

    is_superadmin = request.user.is_superuser or request.user.role == 'ADMIN'

    if request.method == 'POST':
        action = request.POST.get('action')
        member_id = request.POST.get('member_id')
        member = get_object_or_404(User, id=member_id)

        # Protection : Seul un SuperAdmin peut valider ou rejeter un FabManager ou Administrateur
        if member.role in ['FABMANAGER', 'ADMIN'] and not is_superadmin:
            messages.error(request, "Seul le Super Administrateur Système peut valider ou modifier un compte FabManager / Administrateur.")
            return redirect('member_list')

        if action == 'approve_user':
            member.is_approved = True
            member.save()
            send_member_approved_email(member)
            messages.success(request, f"Le compte membre de {member.get_full_name() or member.username} a été approuvé avec succès !")
            return redirect('member_list')
        elif action == 'reject_user':
            send_member_rejected_email(member)
            member.delete()
            messages.info(request, "La demande d'inscription a été refusée.")
            return redirect('member_list')
        elif action == 'request_info':
            custom_msg = request.POST.get('custom_message', '').strip()
            if not custom_msg:
                custom_msg = "Merci de bien vouloir nous fournir un document justificatif valide (carte étudiant ou pièce d'identité)."
            member.bio = f"[Demande de précision : {custom_msg}]"
            member.save()
            send_member_info_request_email(member, custom_msg)
            messages.success(request, f"E-mail de demande d'informations complémentaires envoyé avec succès à {member.get_full_name() or member.username} ({member.email}).")
            return redirect('member_list')

        new_role = request.POST.get('role')
        toggle_certified = request.POST.get('toggle_certified')
        toggle_approved = request.POST.get('toggle_approved')

        if new_role and new_role != member.role:
            if (new_role in ['ADMIN', 'FABMANAGER'] or member.role in ['ADMIN', 'FABMANAGER']) and not is_superadmin:
                messages.error(request, "Seul le Super Administrateur Système peut attribuer ou modifier le rôle FabManager / Administrateur.")
            else:
                member.role = new_role
                member.save()
                messages.success(request, f"Rôle de {member.get_full_name() or member.username} mis à jour en {member.get_role_display()}.")

        if toggle_certified:
            member.is_certified = not member.is_certified
            member.save()
            status_str = "Habilité" if member.is_certified else "Non habilité"
            messages.info(request, f"Statut de {member.get_full_name()} : {status_str}.")

        if toggle_approved:
            if member.role in ['FABMANAGER', 'ADMIN'] and not is_superadmin:
                messages.error(request, "Seul le Super Administrateur Système peut modifier la validation d'un compte FabManager.")
            else:
                member.is_approved = not member.is_approved
                member.save()
                status_str = "Approuvé" if member.is_approved else "En attente"
                messages.info(request, f"Statut de validation de {member.get_full_name()} : {status_str}.")

        return redirect('member_list')

    # Filtrage des demandes selon le rang de l'utilisateur connecté :
    # Un SuperAdmin voit toutes les demandes (dont FabManagers). Un FabManager standard ne voit QUE les membres réguliers de son labo.
    if is_superadmin:
        pending_members = members.filter(is_approved=False)
        pending_fabmanagers = pending_members.filter(role__in=['FABMANAGER', 'ADMIN'])
        pending_regular_members = pending_members.exclude(role__in=['FABMANAGER', 'ADMIN'])
    else:
        pending_members = members.filter(is_approved=False).exclude(role__in=['FABMANAGER', 'ADMIN'])
        pending_fabmanagers = User.objects.none()
        pending_regular_members = pending_members

    approved_members = members.filter(is_approved=True)

    context = {
        'members': members,
        'pending_members': pending_members,
        'pending_fabmanagers': pending_fabmanagers,
        'pending_regular_members': pending_regular_members,
        'approved_members': approved_members,
        'total_members': members.count(),
        'pending_count': pending_members.count(),
        'certified_members': members.filter(is_certified=True).count(),
        'is_superadmin': is_superadmin,
    }
    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        return render(request, 'accounts/partials/member_table.html', context)
    return render(request, 'accounts/member_list.html', context)


@admin_required
def superadmin_dashboard_view(request):
    """Tableau de bord Master dédié au Super Administrateur Système."""
    all_fablabs = FabLab.objects.all().order_by('-created_at')
    all_users = User.objects.all().order_by('-date_joined')
    pending_fabmanagers = User.objects.filter(is_approved=False, role__in=['FABMANAGER', 'ADMIN'])
    pending_members_count = User.objects.filter(is_approved=False).count()
    
    total_fablabs = all_fablabs.count()
    active_fablabs = all_fablabs.filter(is_active=True).count()
    total_users = all_users.count()
    total_subscriptions = Subscription.objects.filter(is_active=True).count()
    total_revenue = Subscription.objects.filter(is_active=True).aggregate(total=Sum('price'))['total'] or 0

    if request.method == 'POST':
        action = request.POST.get('action')
        target_id = request.POST.get('target_id')

        if action == 'approve_fabmanager' and target_id:
            user_obj = get_object_or_404(User, id=target_id)
            user_obj.is_approved = True
            user_obj.save()
            send_member_approved_email(user_obj)
            messages.success(request, f"Le compte FabManager de {user_obj.get_full_name() or user_obj.username} a été approuvé avec succès !")
            return redirect('superadmin_dashboard')

        elif action == 'reject_fabmanager' and target_id:
            user_obj = get_object_or_404(User, id=target_id)
            send_member_rejected_email(user_obj)
            user_obj.delete()
            messages.info(request, "La demande de création de compte FabManager a été refusée.")
            return redirect('superadmin_dashboard')

        elif action == 'toggle_lab_status' and target_id:
            lab = get_object_or_404(FabLab, id=target_id)
            lab.is_active = not lab.is_active
            lab.save()
            status_str = "activé" if lab.is_active else "désactivé"
            messages.info(request, f"L'espace FabLab '{lab.name}' a été {status_str}.")
            return redirect('superadmin_dashboard')

    # Vue globale, non rattachée à un FabLab en particulier : on efface tout
    # contexte de tenant "collé" en session (ex: suite à un switch-tenant
    # précédent) pour que la barre du haut n'affiche pas une école au hasard.
    request.session.pop('tenant_slug', None)

    context = {
        'all_fablabs': all_fablabs,
        'all_users': all_users,
        'pending_fabmanagers': pending_fabmanagers,
        'pending_members_count': pending_members_count,
        'total_fablabs': total_fablabs,
        'active_fablabs': active_fablabs,
        'total_users': total_users,
        'total_subscriptions': total_subscriptions,
        'total_revenue': total_revenue,
        'tenant': None,
    }

    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        return render(request, 'accounts/partials/superadmin_content.html', context)
    return render(request, 'accounts/superadmin_dashboard.html', context)


from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator


def password_reset_view(request):
    """Vue de demande de réinitialisation de mot de passe par Nom d'utilisateur ou Email."""
    if request.method == 'POST':
        login_input = request.POST.get('email_or_username', '').strip()
        user_obj = None
        if '@' in login_input:
            user_obj = User.objects.filter(email__iexact=login_input).first()
        else:
            user_obj = User.objects.filter(username__iexact=login_input).first()

        if user_obj:
            uid = urlsafe_base64_encode(force_bytes(user_obj.pk))
            token = default_token_generator.make_token(user_obj)
            
            from core.emails import get_base_url
            base_url = get_base_url(user_obj.fablab)
            reset_link = f"{base_url}/password-reset/confirm/{uid}/{token}/"

            subject = "[LabOS] Réinitialisation de votre mot de passe"
            message = (
                f"Bonjour {user_obj.get_full_name() or user_obj.username},\n\n"
                f"Vous avez demandé la réinitialisation de votre mot de passe sur la plateforme LabOS.\n\n"
                f"📌 Vos Identifiants :\n"
                f"• Nom d'utilisateur : {user_obj.username}\n"
                f"• Adresse Email : {user_obj.email}\n\n"
                f"🔗 Cliquez sur le lien ci-dessous pour choisir votre nouveau mot de passe :\n"
                f"{reset_link}\n\n"
                f"Si vous n'êtes pas à l'origine de cette demande, vous pouvez ignorer cet e-mail.\n\n"
                f"L'équipe LabOS."
            )
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                send_mail(subject, message, getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@labos.com'), [user_obj.email], fail_silently=True)
            except Exception as e:
                pass

            messages.success(request, f"Un e-mail contenant le lien de réinitialisation et vos identifiants a été envoyé à l'adresse associée à votre compte.")
        else:
            messages.info(request, "Si un compte correspond à cette adresse ou identifiant, un e-mail avec les instructions de réinitialisation a été transmis.")
        return redirect('login')

    return render(request, 'accounts/password_reset.html')


def password_reset_confirm_view(request, uidb64, token):
    """Vue de réinitialisation finale permettant de définir un nouveau mot de passe."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user_obj = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user_obj = None

    if user_obj is not None and default_token_generator.check_token(user_obj, token):
        if request.method == 'POST':
            new_password = request.POST.get('password', '').strip()
            confirm_password = request.POST.get('confirm_password', '').strip()

            if not new_password:
                messages.error(request, "Veuillez renseigner un mot de passe valide.")
            elif new_password != confirm_password:
                messages.error(request, "Les deux mots de passe ne correspondent pas.")
            else:
                user_obj.set_password(new_password)
                user_obj.save()
                messages.success(request, "Votre mot de passe a été réinitialisé avec succès ! Vous pouvez maintenant vous connecter.")
                return redirect('login')

        return render(request, 'accounts/password_reset_confirm.html', {'validlink': True, 'user_obj': user_obj})
    else:
        messages.error(request, "Le lien de réinitialisation de mot de passe est invalide ou a expiré.")
        return redirect('password_reset')
