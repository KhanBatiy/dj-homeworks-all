from django_filters import rest_framework as filters

from advertisements.models import Advertisement, AdvertisementStatusChoices


class AdvertisementFilter(filters.FilterSet):
    """Фильтры для объявлений."""

    # фильтрация по дате создания: ?created_at_after=2021-01-01&created_at_before=2021-12-31
    created_at = filters.DateFromToRangeFilter()

    # фильтрация по статусу: ?status=OPEN
    status = filters.ChoiceFilter(choices=AdvertisementStatusChoices.choices)

    # фильтрация по создателю: ?creator=3
    creator = filters.NumberFilter(field_name='creator_id')

    # фильтрация по избранным текущего пользователя: ?favorite=true
    favorite = filters.BooleanFilter(
        method='filter_favorite',
        label='В избранном у текущего пользователя',
    )

    class Meta:
        model = Advertisement
        # fields = [] — не даём django-filter автоматически сгенерировать
        # фильтры по всем полям модели
        fields = []

    def filter_favorite(self, queryset, name, value):
        user = self.request.user
        if not user.is_authenticated:
            # у анонимного пользователя избранного быть не может
            return queryset.none()
        if value:
            return queryset.filter(favorited_by__user=user)
        return queryset.exclude(favorited_by__user=user)
