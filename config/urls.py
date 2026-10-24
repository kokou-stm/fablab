from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from core import views
from accounts import views as account_views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('login/', account_views.login_view, name='login'),
    path('logout/', account_views.logout_view, name='logout'),
    path('signup/', account_views.signup_view, name='signup'),
    path('signup-pending/', account_views.signup_pending_view, name='signup_pending'),
    path('password-reset/', account_views.password_reset_view, name='password_reset'),
    path('password-reset/confirm/<uidb64>/<token>/', account_views.password_reset_confirm_view, name='password_reset_confirm'),
    path('profile/', account_views.profile_view, name='profile'),
    path('members/', account_views.member_list_view, name='member_list'),
    path('superadmin/', account_views.superadmin_dashboard_view, name='superadmin_dashboard'),

    path('', views.landing_view, name='landing'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('switch-tenant/<slug:slug>/', views.switch_tenant_view, name='switch_tenant'),
    path('register-lab/', views.register_tenant_view, name='register_tenant'),

    path('equipment/', views.equipment_list_view, name='equipment_list'),
    path('equipment/create/', views.equipment_create_view, name='equipment_create'),
    path('equipment/<slug:slug>/', views.equipment_detail_view, name='equipment_detail'),

    path('reservations/', views.reservation_list_view, name='reservation_list'),
    path('reservations/<int:pk>/cancel/', views.reservation_cancel_view, name='reservation_cancel'),
    path('reservations/calendar/', views.reservation_calendar_view, name='reservation_calendar'),
    path('reservations/calendar/api/', views.reservation_calendar_api, name='reservation_calendar_api'),
    path('reservations/history/', views.usage_history_view, name='usage_history'),
    path('certifications/', views.certification_list_view, name='certification_list'),

    path('workshops/', views.workshop_list_view, name='workshop_list'),
    path('workshops/<int:pk>/', views.workshop_detail_view, name='workshop_detail'),

    path('library/', views.library_list_view, name='library_list'),

    path('inventory/', views.inventory_list_view, name='inventory_list'),

    path('projects/', views.project_list_view, name='project_list'),
    path('projects/create/', views.project_create_view, name='project_create'),

    path('maintenance/', views.maintenance_list_view, name='maintenance_list'),

    path('messaging/', views.messaging_view, name='messaging'),

    path('api/notifications/', views.notifications_api_view, name='notifications_api'),
    path('api/notifications/read/', views.mark_notification_read_api_view, name='mark_notification_read_api'),
]

from django.urls import re_path
from core.media_views import protected_media_view

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', protected_media_view),
]

