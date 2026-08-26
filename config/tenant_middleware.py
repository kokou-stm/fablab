"""
Middleware de détection et d'activation du Tenant courant (FabLab).
"""

from django.utils.deprecation import MiddlewareMixin
from config.tenant_router import set_current_tenant, ensure_tenant_db_registered, get_current_tenant
from fablabs.models import FabLab

RESERVED_SUBDOMAINS = {"app", "www", "api", "admin", "static", "media", "localhost", "127"}


class TenantMiddleware(MiddlewareMixin):
    def process_request(self, request):
        tenant_slug = None
        user = getattr(request, "user", None)

        # 1. Priorité Utilisateur connecté : son FabLab attribué
        if user and user.is_authenticated:
            fablab = getattr(user, "fablab", None)
            if fablab and getattr(fablab, "slug", None):
                tenant_slug = fablab.slug

        # 2. En-tête HTTP explicite X-Tenant-Slug ou paramètre GET ?tenant=
        if not tenant_slug:
            tenant_slug = request.headers.get("X-Tenant-Slug") or request.GET.get("tenant")

        # 3. Variable de Session
        if not tenant_slug:
            tenant_slug = request.session.get("tenant_slug")

        # 4. Fallback au premier FabLab existant en base si aucun spécifié
        if not tenant_slug:
            first_lab = FabLab.objects.first()
            if first_lab:
                tenant_slug = first_lab.slug

        if tenant_slug:
            ensure_tenant_db_registered(tenant_slug)
            set_current_tenant(tenant_slug)
            request.tenant = FabLab.objects.filter(slug=tenant_slug).first()
            request.session["tenant_slug"] = tenant_slug
        else:
            set_current_tenant(None)
            request.tenant = None

    def process_response(self, request, response):
        set_current_tenant(None)
        return response
