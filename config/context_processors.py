from fablabs.models import FabLab

def tenant_context(request):
    """Fournit le FabLab actif et la liste de tous les FabLabs enregistrés aux templates."""
    active_tenant = getattr(request, 'tenant', None)
    all_tenants = FabLab.objects.filter(is_active=True)
    return {
        'tenant': active_tenant,
        'all_tenants': all_tenants,
    }
