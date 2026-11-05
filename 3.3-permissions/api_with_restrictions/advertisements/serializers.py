from django.contrib.auth.models import User
from rest_framework import serializers

from advertisements.models import Advertisement, AdvertisementStatusChoices

MAX_OPEN_ADVERTISEMENTS = 10


class UserSerializer(serializers.ModelSerializer):
    """Serializer для пользователя."""

    class Meta:
        model = User
        fields = ('id', 'username', 'first_name',
                  'last_name',)


class AdvertisementSerializer(serializers.ModelSerializer):
    """Serializer для объявления."""

    creator = UserSerializer(
        read_only=True,
    )

    class Meta:
        model = Advertisement
        fields = ('id', 'title', 'description', 'creator',
                  'status', 'created_at', )

    def create(self, validated_data):
        """Метод для создания"""

        # Простановка значения поля создатель по-умолчанию.
        # Текущий пользователь является создателем объявления
        # изменить или переопределить его через API нельзя.
        # обратите внимание на `context` – он выставляется автоматически
        # через методы ViewSet.
        # само поле при этом объявляется как `read_only=True`
        validated_data["creator"] = self.context["request"].user
        return super().create(validated_data)

    def validate(self, data):
        """Метод для валидации. Вызывается при создании и обновлении."""

        status = data.get('status')

        # при частичном обновлении статус может не передаваться —
        # тогда берём текущее значение объявления
        if status is None and self.instance is not None:
            return data

        if status != AdvertisementStatusChoices.OPEN:
            return data

        user = self.context['request'].user

        # не даём открыть одиннадцатое объявление; при обновлении
        # не считаем само редактируемое объявление, если оно уже открыто
        open_advertisements = Advertisement.objects.filter(
            creator=user,
            status=AdvertisementStatusChoices.OPEN,
        )
        if self.instance is not None:
            open_advertisements = open_advertisements.exclude(pk=self.instance.pk)

        if open_advertisements.count() >= MAX_OPEN_ADVERTISEMENTS:
            raise serializers.ValidationError(
                f'Нельзя иметь больше {MAX_OPEN_ADVERTISEMENTS} открытых объявлений.'
            )

        return data
