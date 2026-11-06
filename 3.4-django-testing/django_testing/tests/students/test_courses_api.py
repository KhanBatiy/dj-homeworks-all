import pytest
from rest_framework import status

from students.models import Course


@pytest.mark.django_db
def test_first_course(api_client, course_factory):
    # Arrange
    course = course_factory()
    url = f'/api/v1/courses/{course.id}/'

    # Act
    response = api_client.get(url)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data['id'] == course.id
    assert data['name'] == course.name


@pytest.mark.django_db
def test_first_course_not_found(api_client):
    # Act
    response = api_client.get('/api/v1/courses/999999/')

    # Assert
    assert response.status_code == 404


@pytest.mark.django_db
def test_list_courses(api_client, course_factory):
    # Arrange
    courses = course_factory(_quantity=5)

    # Act
    response = api_client.get('/api/v1/courses/')

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == len(courses)
    received_ids = {course['id'] for course in data}
    assert received_ids == {course.id for course in courses}


@pytest.mark.django_db
def test_filter_courses_by_id(api_client, course_factory):
    # Arrange
    courses = course_factory(_quantity=3)
    target = courses[1]

    # Act
    response = api_client.get('/api/v1/courses/', data={'id': target.id})

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]['id'] == target.id


@pytest.mark.django_db
def test_filter_courses_by_name(api_client, course_factory):
    # Arrange
    course_factory(name='Python')
    course_factory(name='JavaScript')
    course_factory(name='Python')

    # Act
    response = api_client.get('/api/v1/courses/', data={'name': 'Python'})

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(course['name'] == 'Python' for course in data)


@pytest.mark.django_db
def test_create_course(api_client):
    # Arrange
    count = Course.objects.count()
    data = {'name': 'Django'}

    # Act
    response = api_client.post('/api/v1/courses/', data=data)

    # Assert
    assert response.status_code == 201
    assert Course.objects.count() == count + 1
    created = Course.objects.last()
    assert created.name == 'Django'


@pytest.mark.django_db
def test_update_course(api_client, course_factory):
    # Arrange
    course = course_factory(name='Старое название')
    data = {'name': 'Новое название'}

    # Act
    response = api_client.patch(f'/api/v1/courses/{course.id}/', data=data)

    # Assert
    assert response.status_code == 200
    course.refresh_from_db()
    assert course.name == 'Новое название'


@pytest.mark.django_db
def test_delete_course(api_client, course_factory):
    # Arrange
    course = course_factory()
    url = f'/api/v1/courses/{course.id}/'

    # Act
    response = api_client.delete(url)

    # Assert
    assert response.status_code == 204
    assert not Course.objects.filter(id=course.id).exists()


@pytest.mark.django_db
def test_max_students_per_course_exceeded(api_client, course_factory,
                                           student_factory, settings):
    """Студентов больше лимита добавить нельзя.

    Лимит уменьшаем через фикстуру settings, чтобы не создавать 20 сущностей.
    """
    # Arrange
    settings.MAX_STUDENTS_PER_COURSE = 2
    course = course_factory()
    students = student_factory(_quantity=3)
    data = {'name': course.name, 'students': [student.id for student in students]}

    # Act
    response = api_client.patch(f'/api/v1/courses/{course.id}/', data=data)

    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_max_students_per_course_allowed(api_client, course_factory,
                                         student_factory, settings):
    """Студентов ровно по лимиту — добавляем успешно."""
    # Arrange
    settings.MAX_STUDENTS_PER_COURSE = 2
    course = course_factory()
    students = student_factory(_quantity=2)
    data = {'name': course.name, 'students': [student.id for student in students]}

    # Act
    response = api_client.patch(f'/api/v1/courses/{course.id}/', data=data)

    # Assert
    assert response.status_code == status.HTTP_200_OK
    course.refresh_from_db()
    assert course.students.count() == 2


@pytest.mark.django_db
@pytest.mark.parametrize('limit,students_count,expected_status', [
    (20, 20, 200),
    (20, 21, 400),
    (5, 5, 200),
    (5, 6, 400),
    (0, 1, 400),
])
def test_max_students_per_course_parametrized(api_client, course_factory,
                                              student_factory, settings,
                                              limit, students_count,
                                              expected_status):
    """Проверяем границу лимита при разных значениях настройки."""
    # Arrange
    settings.MAX_STUDENTS_PER_COURSE = limit
    course = course_factory()
    students = student_factory(_quantity=students_count)
    data = {'students': [student.id for student in students]}

    # Act
    response = api_client.patch(f'/api/v1/courses/{course.id}/', data=data)

    # Assert
    assert response.status_code == expected_status
