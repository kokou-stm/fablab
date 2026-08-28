from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from core import views
from accounts import views as account_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Authentification, Profils & Membres
    path('login/', account_views.login_view, name='login'),
    path('logout/', account_views.logout_view, name='logout'),
    path('signup/', account_views.signup_view, name='signup'),
    path('signup-pending/', account_views.signup_pending_view, name='signup_pending'),
    path('password-reset/', account_views.password_reset_view, name='password_reset'),
    path('password-reset/confirm/<uidb64>/<token>/', account_views.password_reset_confirm_view, name='password_reset_confirm'),
    path('profile/', account_views.profile_view, name='profile'),
    path('members/', account_views.member_list_view, name='member_list'),
    path('superadmin/', account_views.superadmin_dashboard_view, name='superadmin_dashboard'),

    # Landing Page & Dashboard & Multi-tenant Switching
    path('', views.landing_view, name='landing'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('switch-tenant/<slug:slug>/', views.switch_tenant_view, name='switch_tenant'),
    path('register-lab/', views.register_tenant_view, name='register_tenant'),

    # Machines & Equipements
    path('equipment/', views.equipment_list_view, name='equipment_list'),
    path('equipment/create/', views.equipment_create_view, name='equipment_create'),
    path('equipment/<slug:slug>/', views.equipment_detail_view, name='equipment_detail'),

    # Réservations, Planning & Habilitations
    path('reservations/', views.reservation_list_view, name='reservation_list'),
    path('reservations/<int:pk>/cancel/', views.reservation_cancel_view, name='reservation_cancel'),
    path('reservations/calendar/', views.reservation_calendar_view, name='reservation_calendar'),
    path('reservations/calendar/api/', views.reservation_calendar_api, name='reservation_calendar_api'),
    path('reservations/history/', views.usage_history_view, name='usage_history'),
    path('certifications/', views.certification_list_view, name='certification_list'),

    # Ateliers, Formations & Événements
    path('workshops/', views.workshop_list_view, name='workshop_list'),
    path('workshops/<int:pk>/', views.workshop_detail_view, name='workshop_detail'),

    # Inventaire & Consommables
    path('inventory/', views.inventory_list_view, name='inventory_list'),

    # Galerie & Publication des Projets Makers
    path('projects/', views.project_list_view, name='project_list'),
    path('projects/create/', views.project_create_view, name='project_create'),

    # Maintenance & Incidents
    path('maintenance/', views.maintenance_list_view, name='maintenance_list'),

    # Messagerie Interne & Chat Multi-tenant
    path('messaging/', views.messaging_view, name='messaging'),

    # API Notifications en Temps Réel
    path('api/notifications/', views.notifications_api_view, name='notifications_api'),
]

from django.urls import re_path
from django.views.static import serve

# Service des fichiers médias (justificatifs, photos de machines, documents) en prod et dev
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

