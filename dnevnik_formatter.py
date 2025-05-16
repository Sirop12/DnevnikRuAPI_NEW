from pydnevnikruapi.dnevnik import dnevnik
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import statistics
from collections import defaultdict

class DnevnikFormatter:
    """Класс для форматирования и анализа данных из API Дневник.ру.

    Предоставляет методы для получения расписания, оценок, итоговых оценок,
    рейтинга класса, статистики по предметам и классу.
    """

    def __init__(self, token: str):
        """Инициализация класса с токеном API Дневник.ру.

        Args:
            token (str): Токен для доступа к API Дневник.ру.

        Raises:
            ValueError: Если не удалось получить person_id, school_id или group_id из контекста.
        """
        self.api = dnevnik.DiaryAPI(token=token)
        self.context = self.api.get_context()
        self.person_id = self.context.get('personId')
        self.school_id = self.context.get('schools', [{}])[0].get('id')
        self.group_id = self.context.get('eduGroups', [{}])[0].get('id')
        self._lesson_cache = {}  # Кэш для данных об уроках
        self._subject_cache = {}  # Кэш для названий предметов
        self._student_cache = {}  # Кэш для учеников

        if not self.person_id or not self.school_id or not self.group_id:
            raise ValueError("Не удалось получить person_id, school_id или group_id из контекста")

        self._load_subjects()
        self._load_students()

    def _load_subjects(self):
        """Загрузка названий предметов из API.

        Запрашивает данные об образовательной группе и сохраняет предметы в кэш.
        Выводит сообщение о загруженных предметах.
        """
        try:
            group_data = self.api.get_group_info(self.group_id)
            subjects = group_data.get('subjects', [])
            for subject in subjects:
                self._subject_cache[subject['id']] = subject['name']
            print(f"Загружено предметов из get_edu_groups: {self._subject_cache}")
        except Exception:
            self._subject_cache = {}

    def _load_students(self):
        """Загрузка списка учеников класса.

        Запрашивает список учеников группы и сохраняет их в кэш.
        Выводит сообщение о загруженных учениках.
        """
        try:
            students = self.api.get_groups_pupils(self.group_id)
            for student in students:
                self._student_cache[student['id']] = student.get('shortName', 'Unknown')
            print(f"Загружено учеников: {self._student_cache}")
        except Exception:
            self._student_cache = {}

    def _format_lesson_time(self, lesson_number: int) -> str:
        """Форматирование времени урока по номеру урока.

        Args:
            lesson_number (int): Номер урока (1–7).

        Returns:
            str: Время урока в формате 'HH:MM-HH:MM' или 'Неизвестное время'.
        """
        lesson_times = {
            1: "08:30-09:15",
            2: "09:20-10:05",
            3: "10:15-11:00",
            4: "11:15-12:00",
            5: "12:20-13:05",
            6: "13:25-14:10",
            7: "14:15-15:00"
        }
        return lesson_times.get(lesson_number, "Неизвестное время")

    def get_formatted_schedule(self, date: datetime) -> List[Dict[str, str]]:
        """Получение расписания на указанную дату.

        Args:
            date (datetime): Дата для получения расписания.

        Returns:
            List[Dict[str, str]]: Список уроков с полями:
                - time: время урока (HH:MM-HH:MM)
                - subject: название предмета
                - title: название урока
                - homework: текст домашнего задания
                - teacher: имя преподавателя
        """
        homework_data = self.api.get_school_homework(self.school_id, date, date)
        lessons = homework_data.get('lessons', [])
        subjects = {s['id']: s['name'] for s in homework_data.get('subjects', [])}
        teachers = {t['id']: t['shortName'] for t in homework_data.get('teachers', [])}
        works = {w['id']: w['text'] for w in homework_data.get('works', [])}

        self._subject_cache.update(subjects)

        formatted_schedule = []

        for lesson in lessons:
            lesson_date = datetime.strptime(lesson['date'], '%Y-%m-%dT%H:%M:%S')
            if lesson_date.date() != date.date():
                continue

            subject_name = subjects.get(lesson['subjectId'], 'Неизвестный предмет')
            teacher_name = teachers.get(lesson['teachers'][0], 'Неизвестный преподаватель') if lesson.get('teachers') else 'Неизвестный преподаватель'
            homework = [works.get(work_id, 'Нет задания') for work_id in lesson.get('works', [])]
            homework_text = '; '.join(homework) if homework else 'Нет задания'

            formatted_schedule.append({
                'time': self._format_lesson_time(lesson['number']),
                'subject': subject_name,
                'title': lesson['title'],
                'homework': homework_text,
                'teacher': teacher_name
            })

        return sorted(formatted_schedule, key=lambda x: x['time'])

    def _get_lesson_info(self, lesson_id: str) -> Optional[Dict]:
        """Получение информации об уроке с кэшированием.

        Args:
            lesson_id (str): ID урока.

        Returns:
            Optional[Dict]: Данные урока или None при ошибке.
        """
        if lesson_id not in self._lesson_cache:
            try:
                lesson_data = self.api.get_lesson_info(int(lesson_id))
                self._lesson_cache[lesson_id] = lesson_data
            except Exception:
                self._lesson_cache[lesson_id] = {}
        return self._lesson_cache[lesson_id]

    def get_formatted_marks(self, start_date: datetime, end_date: Optional[datetime] = None) -> Dict[str, List[Dict[str, str]]]:
        """Получение оценок ученика за период.

        Args:
            start_date (datetime): Начальная дата периода.
            end_date (Optional[datetime]): Конечная дата периода (по умолчанию start_date).

        Returns:
            Dict[str, List[Dict[str, str]]]: Словарь, где ключи — названия предметов,
                значения — списки оценок с полями:
                - date: дата оценки (DD.MM.YYYY)
                - value: значение оценки
                - comment: комментарий к оценке
        """
        if end_date is None:
            end_date = start_date

        marks_data = self.api.get_person_marks(self.person_id, self.school_id, start_date, end_date)
        lesson_ids = list(set(mark['lesson_str'] for mark in marks_data if 'lesson_str' in mark))

        lesson_subjects = {}
        for lesson_id in lesson_ids:
            lesson_data = self._get_lesson_info(lesson_id)
            if lesson_data and 'subject' in lesson_data and 'id' in lesson_data['subject']:
                subject_id = lesson_data['subject']['id']
                lesson_subjects[lesson_id] = subject_id

        homework_data = self.api.get_school_homework(self.school_id, start_date, end_date)
        subjects = {s['id']: s['name'] for s in homework_data.get('subjects', [])}
        self._subject_cache.update(subjects)

        formatted_marks = {}

        for mark in marks_data:
            lesson_id = mark.get('lesson_str')
            subject_id = lesson_subjects.get(lesson_id) if lesson_id else None
            subject_name = self._subject_cache.get(subject_id, 'Неизвестный предмет') if subject_id else 'Неизвестный предмет'

            if subject_name not in formatted_marks:
                formatted_marks[subject_name] = []

            formatted_marks[subject_name].append({
                'date': datetime.strptime(mark.get('date', '1970-01-01T00:00:00'), '%Y-%m-%dT%H:%M:%S.%f').strftime('%d.%m.%Y'),
                'value': str(mark.get('value', 'Нет оценки')),
                'comment': mark.get('mood', '')
            })

        for subject in formatted_marks:
            formatted_marks[subject] = sorted(formatted_marks[subject], key=lambda x: x['date'])

        return formatted_marks

    def _get_quarter_period_id(self, study_year: int, quarter: int) -> Optional[Tuple[int, datetime, datetime]]:
        """Получение ID периода и дат для четверти.

        Args:
            study_year (int): Учебный год (например, 2024 для 2024-2025).
            quarter (int): Номер четверти (1–4).

        Returns:
            Optional[Tuple[int, datetime, datetime]]: Кортеж (period_id, start_date, finish_date)
                или None, если период не найден.
        """
        try:
            periods = self.api.get(f"edu-groups/{self.group_id}/reporting-periods")
            for period in periods:
                if period.get('type') == 'quarter' and period.get('number') == quarter:
                    start_date = datetime.strptime(period.get('start', '1970-01-01'), '%Y-%m-%dT%H:%M:%S')
                    finish_date = datetime.strptime(period.get('finish', '1970-01-01'), '%Y-%m-%dT%H:%M:%S')
                    if start_date.year == study_year or start_date.year == study_year + 1:
                        return period.get('id'), start_date, finish_date

            for period in periods:
                if period.get('type') != 'Semester':
                    continue
                start_date = datetime.strptime(period.get('start', '1970-01-01'), '%Y-%m-%dT%H:%M:%S')
                finish_date = datetime.strptime(period.get('finish', '1970-01-01'), '%Y-%m-%dT%H:%M:%S')
                if (quarter in [1, 2] and period.get('number') == 0 and start_date.year == study_year):
                    return period.get('id'), start_date, finish_date
                if (quarter in [3, 4] and period.get('number') == 1 and start_date.year == study_year + 1):
                    return period.get('id'), start_date, finish_date

            return None
        except Exception:
            return None

    def get_formatted_final_marks(self, study_year: int, quarter: int) -> List[Dict[str, str]]:
        """Получение итоговых оценок за четверть.

        Args:
            study_year (int): Учебный год (например, 2024 для 2024-2025).
            quarter (int): Номер четверти (1–4).

        Returns:
            List[Dict[str, str]]: Список словарей с полями:
                - название предмета: название предмета
                - оценки: список числовых оценок
                - итог: средний балл или 'Нет оценок'

        Raises:
            ValueError: Если номер четверти не в диапазоне 1–4.
        """
        if quarter not in [1, 2, 3, 4]:
            raise ValueError("Номер четверти должен быть от 1 до 4")

        period_data = self._get_quarter_period_id(study_year, quarter)
        if not period_data:
            return []

        period_id, start_date, finish_date = period_data
        marks = self.get_formatted_marks(start_date, finish_date)

        formatted_final_marks = []

        for subject_name, marks_list in marks.items():
            grades = [mark['value'] for mark in marks_list if mark['value'].replace('.', '', 1).isdigit()]
            if grades:
                try:
                    average = statistics.mean([float(grade) for grade in grades])
                    average_str = str(round(average, 1))
                except (ValueError, statistics.StatisticsError):
                    average_str = "Нет данных"
            else:
                average_str = "Нет оценок"

            formatted_final_marks.append({
                "название предмета": subject_name,
                "оценки": grades,
                "итог": average_str
            })

        return sorted(formatted_final_marks, key=lambda x: x["название предмета"])

    def get_class_ranking(self, study_year: int, quarter: int) -> List[Dict]:
        """Получение рейтинга класса по среднему баллу.

        Args:
            study_year (int): Учебный год (например, 2024 для 2024-2025).
            quarter (int): Номер четверти (1–4).

        Returns:
            List[Dict]: Список словарей с полями:
                - name: имя ученика
                - avg_grade: средний балл (округлен до 2 знаков)
                - marks_count: количество оценок

        Raises:
            ValueError: Если номер четверти не в диапазоне 1–4.
        """
        if quarter not in [1, 2, 3, 4]:
            raise ValueError("Номер четверти должен быть от 1 до 4")

        period_data = self._get_quarter_period_id(study_year, quarter)
        if not period_data:
            return []

        period_id, start_date, finish_date = period_data

        grade_mapping = {
            'отлично': 5,
            'хорошо': 4,
            'удовлетворительно': 3,
            'неудовлетворительно': 2
        }
        ranking = []

        for student_id, student_name in self._student_cache.items():
            student_grades = []
            for subject_id in self._subject_cache:
                try:
                    marks = self.api.get_person_subject_marks(student_id, subject_id, start_date, finish_date)
                    for mark in marks:
                        value = mark.get('value', '')
                        if value in grade_mapping:
                            student_grades.append(float(grade_mapping[value]))
                        else:
                            try:
                                grade = float(value)
                                student_grades.append(grade)
                            except (ValueError, TypeError):
                                continue
                except Exception:
                    continue

            avg_grade = sum(student_grades) / len(student_grades) if student_grades else 0
            ranking.append({
                'name': student_name,
                'avg_grade': round(avg_grade, 2),
                'marks_count': len(student_grades)
            })

        ranking.sort(key=lambda x: x['avg_grade'], reverse=True)
        return ranking

    def get_subject_stats(self, study_year: int, quarter: int, subject_id: int) -> Dict[str, int]:
        """Получение статистики оценок по предмету.

        Args:
            study_year (int): Учебный год.
            quarter (int): Номер четверти (1–4).
            subject_id (int): ID предмета.

        Returns:
            Dict[str, int]: Словарь с количеством оценок (например, {'2': 5, '3': 10, ...}).

        Raises:
            ValueError: Если номер четверти не в диапазоне 1–4.
        """
        if quarter not in [1, 2, 3, 4]:
            raise ValueError("Номер четверти должен быть от 1 до 4")

        period_data = self._get_quarter_period_id(study_year, quarter)
        if not period_data:
            return {}

        period_id, start_date, finish_date = period_data

        try:
            histogram = self.api.get_subject_marks_histogram(self.group_id, period_id, subject_id)
            hist_data = defaultdict(int)
            works = histogram.get('works', [])
            for work in works:
                mark_numbers = work.get('markNumbers', [])
                for mark_number in mark_numbers:
                    for mark in mark_number.get('marks', []):
                        value = mark.get('value')
                        count = mark.get('count', 0)
                        hist_data[value] += count

            return dict(hist_data)
        except Exception:
            return {}

    def get_subject_ranking(self, study_year: int, quarter: int, subject_id: int) -> List[Dict]:
        """Получение рейтинга учеников по предмету.

        Args:
            study_year (int): Учебный год.
            quarter (int): Номер четверти (1–4).
            subject_id (int): ID предмета.

        Returns:
            List[Dict]: Список словарей с полями:
                - name: имя ученика
                - avg_grade: средний балл (округлен до 2 знаков)
                - marks_count: количество оценок

        Raises:
            ValueError: Если номер четверти не в диапазоне 1–4.
        """
        if quarter not in [1, 2, 3, 4]:
            raise ValueError("Номер четверти должен быть от 1 до 4")

        period_data = self._get_quarter_period_id(study_year, quarter)
        if not period_data:
            return []

        period_id, start_date, finish_date = period_data

        grade_mapping = {
            'отлично': 5,
            'хорошо': 4,
            'удовлетворительно': 3,
            'неудовлетворительно': 2
        }
        ranking = []

        for student_id, student_name in self._student_cache.items():
            student_grades = []
            try:
                marks = self.api.get_person_subject_marks(student_id, subject_id, start_date, finish_date)
                for mark in marks:
                    value = mark.get('value', '')
                    if value in grade_mapping:
                        student_grades.append(float(grade_mapping[value]))
                    else:
                        try:
                            grade = float(value)
                            student_grades.append(grade)
                        except (ValueError, TypeError):
                            continue
            except Exception:
                continue

            avg_grade = sum(student_grades) / len(student_grades) if student_grades else 0
            ranking.append({
                'name': student_name,
                'avg_grade': round(avg_grade, 2),
                'marks_count': len(student_grades)
            })

        ranking.sort(key=lambda x: x['avg_grade'], reverse=True)
        return ranking

    def get_class_stats(self, study_year: int, quarter: int) -> Dict:
        """Получение общей статистики по классу.

        Args:
            study_year (int): Учебный год.
            quarter (int): Номер четверти (1–4).

        Returns:
            Dict: Словарь с полями:
                - total_marks: общее количество числовых оценок
                - average_class_grade: средний балл класса
                - grade_distribution: процентное распределение оценок

        Raises:
            ValueError: Если номер четверти не в диапазоне 1–4.
        """
        if quarter not in [1, 2, 3, 4]:
            raise ValueError("Номер четверти должен быть от 1 до 4")

        period_data = self._get_quarter_period_id(study_year, quarter)
        if not period_data:
            return {}

        period_id, start_date, finish_date = period_data

        total_grades = defaultdict(int)
        total_marks = 0

        for subject_id in self._subject_cache:
            try:
                histogram = self.api.get_subject_marks_histogram(self.group_id, period_id, subject_id)
                works = histogram.get('works', [])
                for work in works:
                    mark_numbers = work.get('markNumbers', [])
                    for mark_number in mark_numbers:
                        for mark in mark_number.get('marks', []):
                            value = mark.get('value')
                            count = mark.get('count', 0)
                            if value.replace('.', '', 1).isdigit():
                                total_grades[value] += count
                                total_marks += count
            except Exception:
                continue

        average_class_grade = sum(float(k) * v for k, v in total_grades.items()) / total_marks if total_marks else 0
        grade_distribution = {k: v / total_marks * 100 for k, v in total_grades.items()} if total_marks else {}

        return {
            'total_marks': total_marks,
            'average_class_grade': round(average_class_grade, 2),
            'grade_distribution': grade_distribution
        }
