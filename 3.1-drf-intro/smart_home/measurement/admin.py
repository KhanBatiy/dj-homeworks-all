from django.contrib import admin

from .models import Measurement, Sensor


@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'description']
    search_fields = ['name', 'description']


@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = ['id', 'sensor', 'temperature', 'created_at', 'picture']
    list_filter = ['sensor']
