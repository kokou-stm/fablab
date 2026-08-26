from django.test import Client
from django.urls import reverse
from config.test_utils import BaseTenantTestCase
from accounts.models import User
from projects.models import Project

class ProjectsModelAndViewsTests(BaseTenantTestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="author_user",
            email="author@test.org",
            password="password123",
            is_approved=True
        )
        self.project = Project.objects.create(
            title="Projet Test",
            slug="projet-test",
            author=self.user,
            author_name=self.user.username,
            category="Impression 3D",
            description="Description du projet",
            is_public=True
        )

    def test_project_author_link(self):
        self.assertEqual(self.project.author, self.user)

    def test_project_list_view(self):
        response = self.client.get(reverse('project_list'))
        self.assertEqual(response.status_code, 200)

    def test_project_create_view_requires_login(self):
        response = self.client.get(reverse('project_create'))
        self.assertEqual(response.status_code, 302)

        self.client.login(username="author_user", password="password123")
        response = self.client.get(reverse('project_create'))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('project_create'), {
            'title': 'Nouveau Projet Publié',
            'category': 'Découpe Laser',
            'description': 'Tutoriel complet',
            'license': 'MIT',
            'is_public': 'on'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Project.objects.filter(slug='nouveau-projet-publie').exists())
