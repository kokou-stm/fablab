import os
from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = "Crée ou met à jour le compte Administrateur / SuperAdmin Système pour la production."

    def add_arguments(self, parser):
        parser.add_argument('--username', default=os.environ.get('DJANGO_ADMIN_USERNAME', 'admin'))
        parser.add_argument('--email', default=os.environ.get('DJANGO_ADMIN_EMAIL', 'admin@labos.com'))
        parser.add_argument('--password', default=os.environ.get('DJANGO_ADMIN_PASSWORD', 'AdminFabLab2026!'))

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'role': 'ADMIN',
                'is_staff': True,
                'is_superuser': True,
                'is_approved': True,
                'first_name': 'Super',
                'last_name': 'Admin',
            }
        )

        user.set_password(password)
        user.email = email
        user.role = 'ADMIN'
        user.is_staff = True
        user.is_superuser = True
        user.is_approved = True
        user.save()

        action = "créé" if created else "mis à jour"
        self.stdout.write(self.style.SUCCESS(f"✓ Compte Administrateur '{username}' ({email}) {action} avec succès."))
