from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.viewsets import ModelViewSet

from logistic.models import Product, Stock
from logistic.serializers import ProductSerializer, StockSerializer


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    # поиск продуктов по названию и описанию: ?search=помидор
    filter_backends = [SearchFilter]
    search_fields = ['title', 'description']

    def get_queryset(self):
        return super().get_queryset().order_by('id')


class StockViewSet(ModelViewSet):
    queryset = Stock.objects.all()
    serializer_class = StockSerializer
    # поиск складов с продуктом по названию/описанию: ?search=помид
    filter_backends = [SearchFilter]
    search_fields = [
        'address',
        'positions__product__title',
        'positions__product__description',
    ]

    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related('positions__product')

        # фильтрация складов по идентификатору продукта: ?products=2
        product_id = self.request.query_params.get('products')
        if product_id:
            try:
                product_id = int(product_id)
            except (TypeError, ValueError):
                raise ValidationError(
                    {'products': 'Ожидается целое число — идентификатор продукта.'}
                )
            queryset = queryset.filter(positions__product_id=product_id)

        # distinct обязателен: поиск идёт через обратную связь positions,
        # и склад с несколькими подходящими позициями иначе повторится в выдаче
        return queryset.distinct().order_by('id')
