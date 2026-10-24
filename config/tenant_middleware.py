"""
Middleware de détection et d'activation du Tenant courant (FabLab).
"""

import os

from django.http import HttpResponseNotFound
from django.template.loader import render_to_string
from django.utils.deprecation import MiddlewareMixin
from config.tenant_router import set_current_tenant, ensure_tenant_db_registered, get_current_tenant
from fablabs.models import FabLab

RESERVED_SUBDOMAINS = {"app", "www", "api", "admin", "static", "media", "localhost", "127", "fablab", "autodiscover"}
BASE_DOMAIN = os.environ.get('DJANGO_BASE_DOMAIN', 'aidubber.fr')


_TENANT_CACHE = {}

class TenantMiddleware(MiddlewareMixin):
    def process_request(self, request):
        tenant_slug = None
        tenant_from_host = False
        user = getattr(request, "user", None)

        host = request.get_host().split(":")[0].lower()

        if host in _TENANT_CACHE:
            matched_lab = _TENANT_CACHE[host]
            if matched_lab:
                tenant_slug = matched_lab.slug
                tenant_from_host = True

        if not tenant_slug:
            matched_lab = FabLab.objects.only('id', 'slug', 'name', 'domain').filter(domain__iexact=host, domain_verified=True).first()
            if matched_lab:
                tenant_slug = matched_lab.slug
                tenant_from_host = True
                _TENANT_CACHE[host] = matched_lab

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
                    tenant_from_host = True
                    _TENANT_CACHE[host] = matched_lab
                elif host.endswith("." + BASE_DOMAIN):
                    html = render_to_string('errors/tenant_not_found.html', {
                        'host': host,
                        'base_domain': BASE_DOMAIN,
                    })
                    return HttpResponseNotFound(html)

        if not tenant_slug and user and user.is_authenticated and not (user.is_superuser or getattr(user, 'role', '') == 'ADMIN'):
            fablab = getattr(user, "fablab", None)
            if fablab and getattr(fablab, "slug", None):
                tenant_slug = fablab.slug

        if not tenant_slug:
            tenant_slug = request.headers.get("X-Tenant-Slug") or request.GET.get("tenant")

        if not tenant_slug:
            tenant_slug = request.session.get("tenant_slug")

        if not tenant_slug:
            first_lab = FabLab.objects.only('id', 'slug', 'name').first()
            if first_lab:
                tenant_slug = first_lab.slug

        if tenant_slug:
            ensure_tenant_db_registered(tenant_slug)
            set_current_tenant(tenant_slug)
            
            tenant_obj = _TENANT_CACHE.get(f"slug:{tenant_slug}")
            if not tenant_obj:
                tenant_obj = FabLab.objects.only('id', 'slug', 'name', 'domain', 'is_active', 'logo', 'contact_email').filter(slug=tenant_slug).first()
                if tenant_obj:
                    _TENANT_CACHE[f"slug:{tenant_slug}"] = tenant_obj

            request.tenant = tenant_obj
            request.tenant_from_host = tenant_from_host
            request.session["tenant_slug"] = tenant_slug
        else:
            set_current_tenant(None)
            request.tenant = None
            request.tenant_from_host = False

    def process_response(self, request, response):
        set_current_tenant(None)
        return response
