from rest_framework.generics import CreateAPIView, ListCreateAPIView, RetrieveUpdateAPIView

from .models import Measurement, Sensor
from .serializers import (
    MeasurementSerializer,
    SensorDetailSerializer,
    SensorSerializer,
)


class SensorListCreateView(ListCreateAPIView):
    """GET /api/sensors/ — список датчиков; POST /api/sensors/ — создать датчик."""

    queryset = Sensor.objects.all()
    serializer_class = SensorSerializer


class SensorRetrieveUpdateView(RetrieveUpdateAPIView):
    """GET/PATCH /api/sensors/<id>/ — детали датчика с измерениями и его изменение."""

    queryset = Sensor.objects.prefetch_related('measurements')
    serializer_class = SensorDetailSerializer


class MeasurementCreateView(CreateAPIView):
    """POST /api/measurements/ — добавить измерение."""

    queryset = Measurement.objects.all()
    serializer_class = MeasurementSerializer
