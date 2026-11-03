from rest_framework import serializers

from .models import Measurement, Sensor


class MeasurementSerializer(serializers.ModelSerializer):
    """Измерение для создания: датчик, температура и необязательная картинка."""

    class Meta:
        model = Measurement
        fields = ['id', 'sensor', 'temperature', 'created_at', 'picture']
        read_only_fields = ['id', 'created_at']


class MeasurementDetailSerializer(serializers.ModelSerializer):
    """Измерение внутри датчика: датчик уже известен из родительского объекта."""

    class Meta:
        model = Measurement
        fields = ['temperature', 'created_at', 'picture']
        read_only_fields = fields


class SensorSerializer(serializers.ModelSerializer):
    """Краткая информация о датчике — для списка и создания."""

    class Meta:
        model = Sensor
        fields = ['id', 'name', 'description']
        read_only_fields = ['id']


class SensorDetailSerializer(serializers.ModelSerializer):
    """Датчик со списком всех его измерений."""

    measurements = serializers.SerializerMethodField()

    class Meta:
        model = Sensor
        fields = ['id', 'name', 'description', 'measurements']
        read_only_fields = ['id']

    def get_measurements(self, obj):
        # Датчик уже известен из родительского объекта, поэтому не дублируем его.
        serializer = MeasurementDetailSerializer(obj.measurements.all(), many=True)
        return serializer.data
