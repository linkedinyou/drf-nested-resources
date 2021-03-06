from django.core.urlresolvers import resolve
from django.test import Client, TransactionTestCase
from django.test.client import ClientHandler
from nose.tools import eq_
from nose.tools import ok_
from rest_framework.reverse import reverse
from rest_framework.routers import SimpleRouter

from drf_nested_resources.routers import Resource
from drf_nested_resources.routers import make_urlpatterns_from_resources
from drf_nested_resources.routers import NestedResource
from tests.django_project.app.models import Developer
from tests.django_project.app.models import ProgrammingLanguage
from tests.django_project.app.models import ProgrammingLanguageVersion
from tests.django_project.app.views import DeveloperViewSet
from tests.django_project.app.views import ProgrammingLanguageVersionViewSet
from tests.django_project.app.views import ProgrammingLanguageViewSet


class TestURLPatternGeneration(object):

    @staticmethod
    def test_default_router():
        resources = []
        urlpatterns = make_urlpatterns_from_resources(resources)
        eq_(2, len(urlpatterns))

        url_path1 = reverse('api-root', urlconf=urlpatterns)
        eq_('/', url_path1)

        url_path2 = \
            reverse('api-root', kwargs={'format': 'json'}, urlconf=urlpatterns)
        eq_('/.json', url_path2)

    @staticmethod
    def test_resources_resolution_with_default_router():
        resources = [Resource('developer', 'developers', DeveloperViewSet)]
        urlpatterns = make_urlpatterns_from_resources(resources)

        url_path = reverse('developer-list', urlconf=urlpatterns)
        eq_('/developers/', url_path)

        view_callable, view_args, view_kwargs = resolve(url_path, urlpatterns)
        ok_(getattr(view_callable, 'is_fixture', False))
        eq_((), view_args)
        eq_({}, view_kwargs)

    @staticmethod
    def test_resources_resolution_with_custom_router():
        resources = [Resource('developer', 'developers', DeveloperViewSet)]
        urlpatterns = make_urlpatterns_from_resources(resources, SimpleRouter())
        eq_(2, len(urlpatterns))

        url_path1 = reverse('developer-list', urlconf=urlpatterns)
        eq_('/developers/', url_path1)

        url_path2 = \
            reverse('developer-detail', kwargs={'pk': 1}, urlconf=urlpatterns)
        eq_('/developers/1/', url_path2)

    @staticmethod
    def test_nested_resources_resolution():
        resources = [
            Resource(
                'developer',
                'developers',
                DeveloperViewSet,
                [
                    NestedResource(
                        'language',
                        'languages',
                        ProgrammingLanguageViewSet,
                        parent_field_lookup='author',
                    ),
                ],
            ),
        ]
        urlpatterns = make_urlpatterns_from_resources(resources)

        url_path = \
            reverse('language-list', kwargs={'author': 1}, urlconf=urlpatterns)
        eq_('/developers/1/languages/', url_path)


class TestDispatch(TransactionTestCase):

    reset_sequences = True

    def setUp(self):
        super(TestDispatch, self).setUp()

        self.developer1 = Developer.objects.create(name='Guido Rossum')
        self.developer2 = Developer.objects.create(name='Larry Wall')
        self.programming_language1 = ProgrammingLanguage.objects.create(
            name='Python',
            author=self.developer1,
            )
        self.programming_language2 = ProgrammingLanguage.objects.create(
            name='Perl',
            author=self.developer2,
            )
        self.programming_language_version = ProgrammingLanguageVersion.objects \
            .create(name='2.7', language=self.programming_language1)

    def test_parent_detail(self):
        resources = [Resource('developer', 'developers', DeveloperViewSet)]
        urlpatterns = make_urlpatterns_from_resources(resources)

        client = _TestClient(urlpatterns)

        url_path = reverse(
            'developer-detail',
            kwargs={'pk': self.developer1.pk},
            urlconf=urlpatterns,
            )
        response = client.get(url_path)
        eq_(200, response.status_code)

    def test_non_existing_parent_detail(self):
        resources = [Resource('developer', 'developers', DeveloperViewSet)]
        urlpatterns = make_urlpatterns_from_resources(resources)

        client = _TestClient(urlpatterns)

        url_path = reverse(
            'developer-detail',
            kwargs={'pk': self.developer2.pk + 1},
            urlconf=urlpatterns,
            )
        response = client.get(url_path)
        eq_(404, response.status_code)

    def test_child_detail(self):
        resources = [
            Resource(
                'developer',
                'developers',
                DeveloperViewSet,
                [
                    NestedResource(
                        'language',
                        'languages',
                        ProgrammingLanguageViewSet,
                        parent_field_lookup='author',
                        ),
                    ],
                ),
            ]
        urlpatterns = make_urlpatterns_from_resources(resources)

        client = _TestClient(urlpatterns)

        url_path = reverse(
            'language-detail',
            kwargs={
                'author': self.developer1.pk,
                'pk': self.programming_language1.pk},
            urlconf=urlpatterns,
            )
        response = client.get(url_path)
        eq_(200, response.status_code)

    def test_child_detail_with_wrong_parent(self):
        resources = [
            Resource(
                'developer',
                'developers',
                DeveloperViewSet,
                [
                    NestedResource(
                        'language',
                        'languages',
                        ProgrammingLanguageViewSet,
                        parent_field_lookup='author',
                        ),
                ],
            ),
        ]
        urlpatterns = make_urlpatterns_from_resources(resources)

        client = _TestClient(urlpatterns)

        url_path = reverse(
            'language-detail',
            kwargs={
                'author': self.developer1.pk,
                'pk': self.programming_language2.pk,
                },
            urlconf=urlpatterns,
            )
        response = client.get(url_path)
        eq_(404, response.status_code)

    def test_child_detail_with_non_existing_parent(self):
        resources = [
            Resource(
                'developer',
                'developers',
                DeveloperViewSet,
                [
                    NestedResource(
                        'language',
                        'languages',
                        ProgrammingLanguageViewSet,
                        parent_field_lookup='author',
                        ),
                ],
            ),
        ]
        urlpatterns = make_urlpatterns_from_resources(resources)

        client = _TestClient(urlpatterns)

        url_path = reverse(
            'language-detail',
            kwargs={
                'author': self.developer2.pk + 1,
                'pk': self.programming_language1.pk,
                },
            urlconf=urlpatterns,
            )
        response = client.get(url_path)
        eq_(404, response.status_code)

    def test_non_existing_child_detail(self):
        resources = [
            Resource(
                'developer',
                'developers',
                DeveloperViewSet,
                [
                    NestedResource(
                        'language',
                        'languages',
                        ProgrammingLanguageViewSet,
                        parent_field_lookup='author',
                        ),
                ],
            ),
        ]
        urlpatterns = make_urlpatterns_from_resources(resources)

        client = _TestClient(urlpatterns)

        url_path = reverse(
            'language-detail',
            kwargs={
                'author': self.developer1.pk,
                'pk': self.programming_language2.pk + 1,
                },
            urlconf=urlpatterns,
            )
        response = client.get(url_path)
        eq_(404, response.status_code)

    def test_grand_child_detail(self):
        resources = [
            Resource(
                'developer',
                'developers',
                DeveloperViewSet,
                [
                    NestedResource(
                        'language',
                        'languages',
                        ProgrammingLanguageViewSet,
                        [
                            NestedResource(
                                'version',
                                'versions',
                                ProgrammingLanguageVersionViewSet,
                                parent_field_lookup='language',
                                ),
                            ],
                        parent_field_lookup='author',
                        ),
                    ],
                ),
            ]
        urlpatterns = make_urlpatterns_from_resources(resources)

        client = _TestClient(urlpatterns)

        url_path = reverse(
            'version-detail',
            kwargs={
                'language__author': self.developer1.pk,
                'language': self.programming_language1.pk,
                'pk': self.programming_language_version.pk,
                },
            urlconf=urlpatterns,
            )
        response = client.get(url_path)
        eq_(200, response.status_code)


class _TestClient(Client):

    def __init__(self, urlconf, *args, **kwargs):
        super(_TestClient, self).__init__(*args, **kwargs)

        self.handler = _TestClientHandler(urlconf)


class _TestClientHandler(ClientHandler):

    def __init__(self, urlconf, *args, **kwargs):
        super(_TestClientHandler, self).__init__(*args, **kwargs)
        self._urlconf = urlconf

    def get_response(self, request):
        request.urlconf = self._urlconf
        return super(_TestClientHandler, self).get_response(request)
