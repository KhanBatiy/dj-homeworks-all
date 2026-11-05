from django.db import models
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from advertisements.filters import AdvertisementFilter
from advertisements.models import (
    Advertisement,
    AdvertisementStatusChoices,
    Favorite,
)
from advertisements.permissions import IsAuthorOrReadOnly
from advertisements.serializers import AdvertisementSerializer


class AdvertisementViewSet(ModelViewSet):
    """ViewSet для объявлений."""

    serializer_class = AdvertisementSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = AdvertisementFilter

    def get_queryset(self):
        """Объявления, доступные текущему пользователю.

        Черновики видит только автор; остальные статусы доступны всем.
        """
        queryset = Advertisement.objects.select_related('creator')
        user = self.request.user
        if user.is_authenticated:
            # свои черновики видны, чужие — нет
            return queryset.filter(models.Q(status=AdvertisementStatusChoices.DRAFT, creator=user)
                                   | ~models.Q(status=AdvertisementStatusChoices.DRAFT))
        return queryset.exclude(status=AdvertisementStatusChoices.DRAFT)

    def get_permissions(self):
        """Получение прав для действий."""
        if self.action == "create":
            return [IsAuthenticated()]
        if self.action in ["update", "partial_update", "destroy"]:
            # изменять и удалять может только автор (или админ)
            return [IsAuthenticated(), IsAuthorOrReadOnly()]
        if self.action == "favorite":
            # в избранное добавляет любой авторизованный, но не автор объявления
            return [IsAuthenticated()]
        return []

    @action(detail=True, methods=['post', 'delete'])
    def favorite(self, request, pk=None):
        """POST — добавить в избранное, DELETE — убрать.

        Автор не может добавить в избранное своё объявление.
        """
        advertisement = self.get_object()

        if request.method == 'DELETE':
            Favorite.objects.filter(
                user=request.user, advertisement=advertisement
            ).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        if advertisement.creator_id == request.user.id:
            raise ValidationError('Нельзя добавить в избранное своё объявление.')

        _, created = Favorite.objects.get_or_create(
            user=request.user, advertisement=advertisement
        )
        if not created:
            raise ValidationError('Объявление уже в избранном.')
        return Response(status=status.HTTP_201_CREATED)
