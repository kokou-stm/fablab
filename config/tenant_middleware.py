"""
Middleware de détection et d'activation du Tenant courant (FabLab).
"""

from django.utils.deprecation import MiddlewareMixin
from config.tenant_router import set_current_tenant, ensure_tenant_db_registered, get_current_tenant
from fablabs.models import FabLab

RESERVED_SUBDOMAINS = {"app", "www", "api", "admin", "static", "media", "localhost", "127", "fablab", "autodiscover"}


_TENANT_CACHE = {}

class TenantMiddleware(MiddlewareMixin):
    def process_request(self, request):
        tenant_slug = None
        user = getattr(request, "user", None)

        host = request.get_host().split(":")[0].lower()

        # 1. Verification cache in-memory
        if host in _TENANT_CACHE:
            matched_lab = _TENANT_CACHE[host]
            if matched_lab:
                tenant_slug = matched_lab.slug

        # 1bis. Priorité N°1 : Nom de domaine personnalisé exact (ex: monfablab.fr)
        if not tenant_slug:
            matched_lab = FabLab.objects.only('id', 'slug', 'name', 'domain').filter(domain__iexact=host).first()
            if matched_lab:
                tenant_slug = matched_lab.slug
                _TENANT_CACHE[host] = matched_lab

        # 1ter. Sinon, sous-domaine HTTP de la plateforme (ex: polytech-nantes.localhost:8000)
        if not tenant_slug:
            host_parts = host.split(".")
            if len(host_parts) >= 2 and host_parts[0] not in RESERVED_SUBDOMAINS:
                subdomain = host_parts[0]
                matched_lab = FabLab.objects.only('id', 'slug', 'name', 'domain').filter(slug=subdomain).first()
                if not matched_lab:
                    clean_subdomain = subdomain.replace("fablab-", "").replace("lab-", "")
                    matched_lab = FabLab.objects.only('id', 'slug', 'name', 'domain').filter(slug=clean_subdomain).first()
                if matched_lab:
                    tenant_slug = matched_lab.slug
                    _TENANT_CACHE[host] = matched_lab

        # 2. Si pas de sous-domaine dans l'URL, priorité à l'utilisateur connecté non-SuperAdmin
        if not tenant_slug and user and user.is_authenticated and not (user.is_superuser or getattr(user, 'role', '') == 'ADMIN'):
            fablab = getattr(user, "fablab", None)
            if fablab and getattr(fablab, "slug", None):
                tenant_slug = fablab.slug

        # 3. En-tête HTTP explicite X-Tenant-Slug ou paramètre GET ?tenant=
        if not tenant_slug:
            tenant_slug = request.headers.get("X-Tenant-Slug") or request.GET.get("tenant")

        # 4. Variable de Session (pour SuperAdmin ou visiteurs sans sous-domaine)
        if not tenant_slug:
            tenant_slug = request.session.get("tenant_slug")

        # 5. Fallback au premier FabLab existant en base si aucun spécifié
        if not tenant_slug:
            first_lab = FabLab.objects.only('id', 'slug', 'name').first()
            if first_lab:
                tenant_slug = first_lab.slug

        if tenant_slug:
            ensure_tenant_db_registered(tenant_slug)
            set_current_tenant(tenant_slug)
            
            # Utiliser cache si disponible pour eviter requete repetitive
            tenant_obj = _TENANT_CACHE.get(f"slug:{tenant_slug}")
            if not tenant_obj:
                tenant_obj = FabLab.objects.only('id', 'slug', 'name', 'domain', 'is_active', 'logo', 'contact_email').filter(slug=tenant_slug).first()
                if tenant_obj:
                    _TENANT_CACHE[f"slug:{tenant_slug}"] = tenant_obj

            request.tenant = tenant_obj
            request.session["tenant_slug"] = tenant_slug
        else:
            set_current_tenant(None)
            request.tenant = None

    def process_response(self, request, response):
        set_current_tenant(None)
        return response
