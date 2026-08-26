from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def role_required(*allowed_roles):
    """Décorateur restreignant l'accès aux utilisateurs possédant au moins l'un des rôles spécifiés."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, "Veuillez vous connecter pour accéder à cette page.")
                return redirect('login')
            if request.user.is_superuser or request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, "Vous n'avez pas les permissions nécessaires pour accéder à cette fonctionnalité.")
            return redirect('dashboard')
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
            messages.warning(request, "Veuillez vous connecter pour effectuer cette action.")
            return redirect('login')
        if request.user.is_superuser or request.user.is_fabmanager_user or getattr(request.user, 'is_approved', False):
            return view_func(request, *args, **kwargs)
        messages.error(request, "Votre compte est actuellement en attente de validation par le responsable de votre FabLab.")
        return redirect('landing')
    return _wrapped_view


def instructor_required(view_func):
    """Décorateur restreignant l'accès aux Formateurs, FabManagers et Administrateurs."""
    return role_required('ADMIN', 'FABMANAGER', 'INSTRUCTOR')(view_func)


def admin_required(view_func):
    """Décorateur restreignant l'accès aux seuls Administrateurs Système."""
    return role_required('ADMIN')(view_func)
