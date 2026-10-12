from django.contrib import admin

from library.models import LibraryResource


@admin.register(LibraryResource)
class LibraryResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'resource_type', 'category', 'author', 'added_by', 'created_at')
    list_filter = ('resource_type', 'category')
    search_fields = ('title', 'author', 'description')
