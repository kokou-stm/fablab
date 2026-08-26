from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.utils import timezone
from django.utils.text import slugify

from accounts.models import User, Subscription
from accounts.decorators import fabmanager_required, role_required
from fablabs.models import FabLab
from reservations.models import Certification, UserCertification

def login_view(request):
    """Vue de connexion membre avec bascule automatique sur le tenant du membre."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.fablab:
                request.session['tenant_slug'] = user.fablab.slug
            messages.success(request, f"Bienvenue, {user.get_full_name() or user.username} !")
            next_url = request.GET.get('next') or 'dashboard'
            return redirect(next_url)
        else:
            messages.error(request, "Identifiant ou mot de passe incorrect.")

    return render(request, 'accounts/login.html')


def logout_view(request):
    """Déconnexion de l'utilisateur."""
    logout(request)
    messages.info(request, "Vous avez été déconnecté avec succès.")
    return redirect('landing')


def signup_view(request):
    """Inscription d'un nouveau membre (Maker) rattaché au FabLab actif (request.tenant)."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    tenant = getattr(request, 'tenant', None)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        role = request.POST.get('role', 'MAKER')

        if User.objects.filter(username=username).exists():
            messages.error(request, f"Le nom d'utilisateur '{username}' est déjà pris.")
            return render(request, 'accounts/signup.html', {'tenant': tenant})

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role=role,
            fablab=tenant
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

        login(request, user)
        if tenant:
            request.session['tenant_slug'] = tenant.slug
        messages.success(request, f"Bienvenue dans la communauté {tenant.name if tenant else 'FabOS'} !")
        return redirect('dashboard')

    return render(request, 'accounts/signup.html', {'tenant': tenant})


def profile_view(request):
    """Vue et modification du profil membre avec gestion des abonnements."""
    if not request.user.is_authenticated:
        messages.warning(request, "Veuillez vous connecter pour voir votre profil.")
        return redirect('login')

    user = request.user
    user_subscriptions = Subscription.objects.filter(user=user)
    active_sub = user_subscriptions.filter(is_active=True).first()
    user_certifications = UserCertification.objects.filter(user_username=user.username)

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
    return render(request, 'accounts/profile.html', context)


@fabmanager_required
def member_list_view(request):
    """Annuaire des membres inscrit sur le tenant courant avec gestion des rôles et abonnements."""
    tenant = getattr(request, 'tenant', None)
    if tenant:
        members = User.objects.filter(fablab=tenant).order_by('-date_joined')
    else:
        members = User.objects.all().order_by('-date_joined')

    if request.method == 'POST':
        member_id = request.POST.get('member_id')
        new_role = request.POST.get('role')
        toggle_certified = request.POST.get('toggle_certified')

        member = get_object_or_404(User, id=member_id)
        if new_role:
            member.role = new_role
            member.save()
            messages.success(request, f"Rôle de {member.get_full_name() or member.username} mis à jour en {member.get_role_display()}.")

        if toggle_certified:
            member.is_certified = not member.is_certified
            member.save()
            status_str = "Habilité" if member.is_certified else "Non habilité"
            messages.info(request, f"Statut de {member.get_full_name()} : {status_str}.")

        return redirect('member_list')

    context = {
        'members': members,
        'total_members': members.count(),
        'certified_members': members.filter(is_certified=True).count(),
    }
    return render(request, 'accounts/member_list.html', context)
