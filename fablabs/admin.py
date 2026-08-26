from django.contrib import admin
from fablabs.models import FabLab

@admin.register(FabLab)
class FabLabAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'city', 'plan', 'is_approved', 'is_active', 'justification_document', 'created_at')
    list_filter = ('is_approved', 'is_active', 'plan', 'city')
    search_fields = ('name', 'slug', 'contact_email', 'city')
    actions = ['approve_selected_fablabs']

    @admin.action(description="Approuver les FabLabs sélectionnés (Validation SuperAdmin)")
    def approve_selected_fablabs(self, request, queryset):
        count = queryset.update(is_approved=True, is_active=True)
        self.message_user(request, f"{count} espace(s) FabLab ont été approuvés avec succès.")
