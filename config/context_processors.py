from fablabs.models import FabLab

def tenant_context(request):
    """Fournit le FabLab actif et la liste des FabLabs accessibles selon le rang de l'utilisateur."""
    active_tenant = getattr(request, 'tenant', None)
    user = getattr(request, 'user', None)

    is_superadmin = False
    if user and user.is_authenticated:
        is_superadmin = user.is_superuser or getattr(user, 'role', '') == 'ADMIN'
        if not is_superadmin and getattr(user, 'fablab', None):
            all_tenants = FabLab.objects.filter(id=user.fablab.id)
            if active_tenant != user.fablab:
                active_tenant = user.fablab
        else:
            all_tenants = FabLab.objects.filter(is_active=True)
    else:
        all_tenants = FabLab.objects.filter(is_active=True)

    return {
        'tenant': active_tenant,
        'all_tenants': all_tenants,
        'is_superadmin': is_superadmin,
    }
