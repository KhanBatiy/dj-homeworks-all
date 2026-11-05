from django.contrib import admin

from advertisements.models import Advertisement, Favorite


@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'status', 'creator', 'created_at']
    list_filter = ['status']
    search_fields = ['title', 'description']
    raw_id_fields = ['creator']


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'advertisement', 'created_at']
    raw_id_fields = ['user', 'advertisement']
