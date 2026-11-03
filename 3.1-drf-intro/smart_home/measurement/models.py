from django.db import models


class Sensor(models.Model):
    """Программируемый датчик, измеряющий температуру."""

    name = models.CharField(max_length=255, verbose_name='название')
    description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='описание',
    )

    class Meta:
        verbose_name = 'датчик'
        verbose_name_plural = 'датчики'
        ordering = ['id']

    def __str__(self):
        return f'{self.name} ({self.pk})'


class Measurement(models.Model):
    """Одно измерение температуры, присланное датчиком."""

    sensor = models.ForeignKey(
        Sensor,
        on_delete=models.CASCADE,
        related_name='measurements',
        verbose_name='датчик',
    )
    temperature = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name='температура',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='дата и время измерения',
    )
    picture = models.ImageField(
        upload_to='measurements/',
        blank=True,
        null=True,
        verbose_name='изображение',
    )

    class Meta:
        verbose_name = 'измерение'
        verbose_name_plural = 'измерения'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.sensor_id}: {self.temperature} °C'
