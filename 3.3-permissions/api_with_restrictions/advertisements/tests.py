from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from advertisements.models import Advertisement, Favorite

ADS_URL = '/api/advertisements/'


class BaseApiTestCase(APITestCase):
    """Общая база: два пользователя с токенами."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='alice', password='pass12345')
        cls.other = User.objects.create_user(username='bob', password='pass12345')
        cls.admin = User.objects.create_user(
            username='admin', password='pass12345', is_staff=True,
        )
        cls.user_token = Token.objects.create(user=cls.user)
        cls.other_token = Token.objects.create(user=cls.other)
        cls.admin_token = Token.objects.create(user=cls.admin)

    def setUp(self):
        # троттлинг использует кеш — сбрасываем счётчики перед каждым тестом
        cache.clear()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.user_token.key}')


class AuthTests(BaseApiTestCase):
    def test_list_is_public(self):
        self.client.credentials()
        response = self.client.get(ADS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_requires_auth(self):
        self.client.credentials()
        response = self.client.post(ADS_URL, {'title': 'Шкаф'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_sets_creator(self):
        response = self.client.post(
            ADS_URL, {'title': 'Шкаф', 'description': 'Срочно'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        ad = Advertisement.objects.get(pk=response.data['id'])
        self.assertEqual(ad.creator, self.user)


class AuthorPermissionTests(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        self.ad = Advertisement.objects.create(
            title='Чужое', creator=self.other,
        )

    def test_author_can_update(self):
        # объявление создал bob — работаем его токеном
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.other_token.key}')
        response = self.client.patch(
            f'{ADS_URL}{self.ad.id}/', {'status': 'CLOSED'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.ad.refresh_from_db()
        self.assertEqual(self.ad.status, 'CLOSED')

    def test_non_author_cannot_update(self):
        # credentials из setUp: alice (self.user), объявление создал bob
        response = self.client.patch(
            f'{ADS_URL}{self.ad.id}/', {'status': 'CLOSED'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_author_cannot_delete(self):
        response = self.client.delete(f'{ADS_URL}{self.ad.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Advertisement.objects.filter(pk=self.ad.pk).exists())

    def test_author_can_delete(self):
        self.ad.creator = self.user
        self.ad.save()
        response = self.client.delete(f'{ADS_URL}{self.ad.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_admin_can_update_any(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.patch(
            f'{ADS_URL}{self.ad.id}/', {'status': 'CLOSED'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_delete_any(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.delete(f'{ADS_URL}{self.ad.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class OpenLimitTests(BaseApiTestCase):
    def _create(self, title, status_value='OPEN'):
        return self.client.post(
            ADS_URL, {'title': title, 'status': status_value}, format='json'
        )

    def test_user_can_have_10_open(self):
        for i in range(10):
            response = self._create(f'Объявление {i}')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_11th_open_is_rejected(self):
        for i in range(10):
            self._create(f'Объявление {i}')
        response = self._create('Одиннадцатое')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_closed_does_not_count(self):
        for i in range(10):
            self._create(f'Объявление {i}')
        # закрытые не входят в лимит
        response = self._create('Закрытое', 'CLOSED')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_reopening_rejected_at_limit(self):
        """Лимит обходится через смену статуса на уже открытом объявлении."""
        ids = [self._create(f'Объявление {i}').data['id'] for i in range(10)]
        closed_id = self._create('Закрытое', 'CLOSED').data['id']
        # попытка открыть одиннадцатое объявление через PATCH
        response = self.client.patch(
            f'{ADS_URL}{closed_id}/', {'status': 'OPEN'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # а это объявление уже открыто — изменение описания не должно падать
        response = self.client.patch(
            f'{ADS_URL}{ids[0]}/', {'description': 'Обновил'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_draft_does_not_count(self):
        for i in range(10):
            self._create(f'Объявление {i}')
        response = self._create('Черновик', 'DRAFT')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class DraftVisibilityTests(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        self.draft = Advertisement.objects.create(
            title='Черновик', creator=self.user, status='DRAFT',
        )
        self.open_ad = Advertisement.objects.create(
            title='Открытое', creator=self.user,
        )

    def test_author_sees_own_draft(self):
        response = self.client.get(ADS_URL)
        titles = [ad['title'] for ad in response.data]
        self.assertIn('Черновик', titles)

    def test_other_user_does_not_see_draft(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.other_token.key}')
        response = self.client.get(ADS_URL)
        titles = [ad['title'] for ad in response.data]
        self.assertNotIn('Черновик', titles)

    def test_anonymous_does_not_see_draft(self):
        self.client.credentials()
        response = self.client.get(ADS_URL)
        titles = [ad['title'] for ad in response.data]
        self.assertNotIn('Черновик', titles)
        self.assertIn('Открытое', titles)

    def test_draft_detail_hidden_from_others(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.other_token.key}')
        response = self.client.get(f'{ADS_URL}{self.draft.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class FilterTests(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        self.ad1 = Advertisement.objects.create(title='Стул', creator=self.user)
        self.ad2 = Advertisement.objects.create(
            title='Стол', creator=self.other, status='CLOSED',
        )

    def test_filter_by_status(self):
        response = self.client.get(ADS_URL, {'status': 'CLOSED'})
        titles = [ad['title'] for ad in response.data]
        self.assertEqual(titles, ['Стол'])

    def test_filter_by_creator(self):
        response = self.client.get(ADS_URL, {'creator': self.other.id})
        titles = [ad['title'] for ad in response.data]
        self.assertEqual(titles, ['Стол'])

    def test_filter_by_created_at_range(self):
        response = self.client.get(
            ADS_URL, {'created_at_before': '2000-01-01'}
        )
        self.assertEqual(len(response.data), 0)
        response = self.client.get(
            ADS_URL, {'created_at_after': '2000-01-01'}
        )
        self.assertEqual(len(response.data), 2)


class FavoriteTests(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        self.ad = Advertisement.objects.create(title='Велосипед', creator=self.other)

    def test_add_to_favorite(self):
        response = self.client.post(f'{ADS_URL}{self.ad.id}/favorite/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Favorite.objects.filter(user=self.user, advertisement=self.ad).exists()
        )

    def test_author_cannot_favorite_own_ad(self):
        own = Advertisement.objects.create(title='Моё', creator=self.user)
        response = self.client.post(f'{ADS_URL}{own.id}/favorite/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_duplicates(self):
        self.client.post(f'{ADS_URL}{self.ad.id}/favorite/')
        response = self.client.post(f'{ADS_URL}{self.ad.id}/favorite/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Favorite.objects.count(), 1)

    def test_remove_from_favorite(self):
        self.client.post(f'{ADS_URL}{self.ad.id}/favorite/')
        response = self.client.delete(f'{ADS_URL}{self.ad.id}/favorite/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Favorite.objects.exists())

    def test_filter_favorites(self):
        self.client.post(f'{ADS_URL}{self.ad.id}/favorite/')
        Advertisement.objects.create(title='Другое', creator=self.other)
        response = self.client.get(ADS_URL, {'favorite': 'true'})
        titles = [ad['title'] for ad in response.data]
        self.assertEqual(titles, ['Велосипед'])

    def test_favorite_requires_auth(self):
        self.client.credentials()
        response = self.client.post(f'{ADS_URL}{self.ad.id}/favorite/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ThrottleTests(BaseApiTestCase):
    """Тесты лимитов: 10/мин аноним, 20/мин авторизованный."""

    def test_anonymous_10_per_minute(self):
        self.client.credentials()
        cache.clear()
        for _ in range(10):
            response = self.client.get(ADS_URL)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.get(ADS_URL)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_authenticated_20_per_minute(self):
        cache.clear()
        for _ in range(20):
            response = self.client.get(ADS_URL)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.get(ADS_URL)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_throttle_not_shared_between_users(self):
        """Лимиты у пользователей независимы."""
        cache.clear()
        for _ in range(20):
            self.client.get(ADS_URL)
        # у второго пользователя свой счётчик
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.other_token.key}')
        response = self.client.get(ADS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
