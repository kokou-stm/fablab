from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponse

def _auth_redirect(request, url_name, fallback_path):
    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        response = HttpResponse(status=200)
        response['HX-Redirect'] = fallback_path
        return response
    return redirect(url_name)


def role_required(*allowed_roles):
    """Décorateur restreignant l'accès aux utilisateurs possédant au moins l'un des rôles spécifiés."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, "Veuillez vous connecter pour accéder à cette page.")
                return _auth_redirect(request, 'login', '/login/')
            if request.user.is_admin_user:
                return view_func(request, *args, **kwargs)
            # Un rôle ne donne ses droits qu'une fois le compte validé.
            if not getattr(request.user, 'is_approved', False):
                messages.error(request, "Votre compte est en attente de validation.")
                return _auth_redirect(request, 'signup_pending', '/signup-pending/')
            if request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, "Vous n'avez pas les permissions nécessaires pour accéder à cette fonctionnalité.")
            return _auth_redirect(request, 'dashboard', '/dashboard/')
        return _wrapped_view
    return decorator


def fabmanager_required(view_func):
    """Décorateur restreignant l'accès aux FabManagers et Administrateurs."""
    return role_required('ADMIN', 'FABMANAGER')(view_func)


def approved_member_required(view_func):
    """Décorateur s'assurant que l'utilisateur est connecté et validé par le responsable."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Veuillez vous connecter pour accéder à cette page.")
            return _auth_redirect(request, 'login', '/login/')
        # Un FabManager non encore validé n'a pas plus de droits qu'un membre
        # en attente : seul le SuperAdmin est exempté de validation.
        if request.user.is_admin_user or getattr(request.user, 'is_approved', False):
            return view_func(request, *args, **kwargs)
        messages.error(request, "Votre compte est actuellement en attente de validation par le responsable de votre FabLab.")
        return _auth_redirect(request, 'signup_pending', '/signup-pending/')
    return _wrapped_view


def instructor_required(view_func):
    """Décorateur restreignant l'accès aux Formateurs, FabManagers et Administrateurs."""
    return role_required('ADMIN', 'FABMANAGER', 'INSTRUCTOR')(view_func)


def admin_required(view_func):
    """Décorateur restreignant l'accès aux seuls Administrateurs Système."""
    return role_required('ADMIN')(view_func)
