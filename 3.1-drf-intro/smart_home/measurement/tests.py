import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Measurement, Sensor


def _make_image():
    buffer = io.BytesIO()
    Image.new('RGB', (1, 1), color='white').save(buffer, format='JPEG')
    return SimpleUploadedFile('sensor.jpg', buffer.getvalue(), content_type='image/jpeg')


class SensorApiTests(APITestCase):
    def setUp(self):
        self.sensor = Sensor.objects.create(name='ESP32', description='Кухня')

    def test_create_sensor(self):
        response = self.client.post(
            '/api/sensors/', {'name': 'ESP32', 'description': 'Балкон'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'ESP32')

    def test_sensor_list_brief_fields(self):
        response = self.client.get('/api/sensors/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data[0].keys()), {'id', 'name', 'description'})

    def test_update_sensor(self):
        response = self.client.patch(
            f'/api/sensors/{self.sensor.pk}/', {'description': 'Балкон'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.sensor.refresh_from_db()
        self.assertEqual(self.sensor.description, 'Балкон')

    def test_detail_contains_measurements(self):
        Measurement.objects.create(sensor=self.sensor, temperature='22.30')
        response = self.client.get(f'/api/sensors/{self.sensor.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['measurements']), 1)
        self.assertEqual(response.data['measurements'][0]['temperature'], '22.30')
        # Датчик-родитель не дублируется внутри измерения.
        self.assertNotIn('sensor', response.data['measurements'][0])

    def test_detail_404(self):
        response = self.client.get('/api/sensors/999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_measurement(self):
        response = self.client.post(
            '/api/measurements/', {'sensor': self.sensor.pk, 'temperature': 22.5}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Measurement.objects.count(), 1)
        self.assertEqual(response.data['temperature'], '22.50')

    def test_measurement_without_picture(self):
        """Старые датчики без картинки продолжают работать."""
        response = self.client.post(
            '/api/measurements/', {'sensor': self.sensor.pk, 'temperature': 20}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['picture'])

    def test_measurement_requires_valid_sensor(self):
        response = self.client.post(
            '/api/measurements/', {'sensor': 999, 'temperature': 20}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('sensor', response.data)

    def test_measurement_picture_is_optional(self):
        response = self.client.post(
            '/api/measurements/',
            {'sensor': self.sensor.pk, 'temperature': 21.0, 'picture': _make_image()},
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data['picture'])
