from django.conf import settings
from rest_framework import serializers

from students.models import Course


class CourseSerializer(serializers.ModelSerializer):

    class Meta:
        model = Course
        fields = ("id", "name", "students")

    def validate_students(self, value):
        """Не даём записать в курс больше студентов, чем разрешено настройками."""

        max_students = getattr(settings, 'MAX_STUDENTS_PER_COURSE', 20)
        if len(value) > max_students:
            raise serializers.ValidationError(
                f'На курсе может быть не больше {max_students} студентов.'
            )
        return value
