from rest_framework import status
from rest_framework.test import APITestCase

from logistic.models import Product, Stock, StockProduct

PRODUCTS_URL = '/api/v1/products/'
STOCKS_URL = '/api/v1/stocks/'


class ProductApiTests(APITestCase):
    def setUp(self):
        self.tomato = Product.objects.create(
            title='Помидор', description='Лучшие помидоры на рынке'
        )
        self.cucumber = Product.objects.create(title='Огурец', description='Свежий')

    def test_create_product(self):
        response = self.client.post(
            PRODUCTS_URL, {'title': 'Кабачок', 'description': 'Молодой'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Кабачок')

    def test_list_is_paginated(self):
        response = self.client.get(PRODUCTS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(response.data.keys()), {'count', 'next', 'previous', 'results'}
        )
        self.assertEqual(response.data['count'], 2)

    def test_partial_update_product(self):
        response = self.client.patch(
            f'{PRODUCTS_URL}{self.tomato.pk}/',
            {'description': 'Самые сочные и ароматные помидорки'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.tomato.refresh_from_db()
        self.assertEqual(self.tomato.description, 'Самые сочные и ароматные помидорки')

    def test_delete_product(self):
        response = self.client.delete(f'{PRODUCTS_URL}{self.tomato.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Product.objects.filter(pk=self.tomato.pk).exists())

    def test_search_by_title(self):
        response = self.client.get(PRODUCTS_URL, {'search': 'помидор'})
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Помидор')

    def test_search_by_description(self):
        response = self.client.get(PRODUCTS_URL, {'search': 'Свежий'})
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Огурец')

    def test_search_is_case_insensitive(self):
        response = self.client.get(PRODUCTS_URL, {'search': 'ПОМИДОР'})
        self.assertEqual(response.data['count'], 1)


class StockApiTests(APITestCase):
    def setUp(self):
        self.tomato = Product.objects.create(title='Помидор', description='Красный')
        self.cucumber = Product.objects.create(title='Огурец', description='Зелёный')

    def _create_stock(self, address='Ленинградский склад'):
        return self.client.post(
            STOCKS_URL,
            {
                'address': address,
                'positions': [
                    {'product': self.tomato.pk, 'quantity': 250, 'price': '120.50'},
                    {'product': self.cucumber.pk, 'quantity': 100, 'price': '180.00'},
                ],
            },
            format='json',
        )

    def test_create_stock_with_positions(self):
        response = self._create_stock()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['positions']), 2)
        self.assertEqual(StockProduct.objects.count(), 2)

    def test_update_stock_positions(self):
        stock_id = self._create_stock().data['id']
        response = self.client.patch(
            f'{STOCKS_URL}{stock_id}/',
            {
                'positions': [
                    {'product': self.tomato.pk, 'quantity': 100, 'price': '130.80'},
                    {'product': self.cucumber.pk, 'quantity': 243, 'price': '145.00'},
                ]
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # позиции обновлены, а не продублированы
        self.assertEqual(StockProduct.objects.count(), 2)
        position = StockProduct.objects.get(stock_id=stock_id, product=self.tomato)
        self.assertEqual(position.quantity, 100)
        self.assertEqual(str(position.price), '130.80')

    def test_update_adds_new_position(self):
        stock_id = self._create_stock().data['id']
        extra = Product.objects.create(title='Кабачок')
        self.client.patch(
            f'{STOCKS_URL}{stock_id}/',
            {'positions': [{'product': extra.pk, 'quantity': 5, 'price': '99.00'}]},
            format='json',
        )
        self.assertEqual(StockProduct.objects.filter(stock_id=stock_id).count(), 3)

    def test_filter_stocks_by_product(self):
        self._create_stock()
        response = self.client.get(STOCKS_URL, {'products': self.cucumber.pk})
        self.assertEqual(response.data['count'], 1)

    def test_filter_returns_empty_for_unknown_product(self):
        self._create_stock()
        response = self.client.get(STOCKS_URL, {'products': 999})
        self.assertEqual(response.data['count'], 0)

    def test_filter_with_invalid_product_id_returns_400(self):
        """Нечисловой ?products= не должен ронять сервер пятисоткой."""
        response = self.client.get(STOCKS_URL, {'products': 'abc'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('products', response.data)

    def test_search_stocks_by_product_title(self):
        """Дополнительное задание: поиск складов по части названия продукта."""
        self._create_stock()
        response = self.client.get(STOCKS_URL, {'search': 'помид'})
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['address'], 'Ленинградский склад')

    def test_search_stocks_by_product_description(self):
        self._create_stock()
        response = self.client.get(STOCKS_URL, {'search': 'Зелёный'})
        self.assertEqual(response.data['count'], 1)

    def test_search_does_not_duplicate_stock(self):
        """Склад с двумя подходящими позициями не должен повторяться в выдаче."""
        self.tomato.description = 'Помидор'
        self.tomato.save()
        self.cucumber.description = 'Помидор'
        self.cucumber.save()
        self._create_stock()
        response = self.client.get(STOCKS_URL, {'search': 'Помидор'})
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)

    def test_delete_stock(self):
        stock_id = self._create_stock().data['id']
        response = self.client.delete(f'{STOCKS_URL}{stock_id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(StockProduct.objects.count(), 0)
