from django.urls import path

from .views import (
    MeasurementCreateView,
    SensorListCreateView,
    SensorRetrieveUpdateView,
)

urlpatterns = [
    path('sensors/', SensorListCreateView.as_view(), name='sensor-list'),
    path('sensors/<int:pk>/', SensorRetrieveUpdateView.as_view(), name='sensor-detail'),
    path('measurements/', MeasurementCreateView.as_view(), name='measurement-create'),
]
