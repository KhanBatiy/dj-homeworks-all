from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAuthorOrReadOnly(BasePermission):
    """Изменять и удалять объявление может только его автор (админ — тоже).

    Чтение разрешено всем. Правило переиспользуется для update,
    partial_update и destroy, поэтому вынесено в отдельный класс.
    """

    message = 'Изменять или удалять объявление может только его автор.'

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if request.user and request.user.is_staff:
            return True
        return obj.creator_id == request.user.id