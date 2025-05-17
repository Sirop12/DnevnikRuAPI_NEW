from pydnevnikruapi.dnevnik import dnevnik
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import statistics
from collections import defaultdict

class DnevnikFormatter:
    """Класс для форматирования и анализа данных из API Дневник.ру."""
    
    def __init__(self, token: str, debug_mode: bool = True):
        """
        Инициализирует класс, подключается к API и загружает данные о предметах, учениках и учителях.

        Args:
            token (str): Токен авторизации API Дневник.ру.
            debug_mode (bool, optional): Включает отладочное логирование. Defaults to True.

        Raises:
            ValueError: Если не удалось получить person_id, school_id или group_id из контекста.

        """
        self.api = dnevnik.DiaryAPI(token=token)
        self.debug_mode = debug_mode
        self.context = self.api.get_context()
        self.person_id = self.context.get('personId')
        self.school_id = self.context.get('schools', [{}])[0].get('id')
        self.group_id = self.context.get('eduGroups', [{}])[0].get('id')
        self._lesson_cache = {}
        self._subject_cache = {}
        self._student_cache = {}
        self._teacher_cache = {}
        self._schedule_cache = {}
        self._log(f"Инициализация: person_id={self.person_id}, school_id={self.school_id}, group_id={self.group_id}")
        if not self.person_id or not self.school_id or not self.group_id:
            raise ValueError("Не удалось получить person_id, school_id или group_id из контекста")
        self._load_subjects()
        self._load_students()
        self._load_teachers()

    def _log(self, message: str):
        """
        Выводит отладочное сообщение в консоль, если включен debug_mode.

        Args:
            message (str): Сообщение для логирования.
        """
        if self.debug_mode:
            print(message)

    def _load_subjects(self):
        """
        Загружает список предметов группы и кэширует их.

        Errors:
            - Ошибка API приводит к пустому _subject_cache.
            - Отсутствие предметов в ответе API.

        """
        try:
            group_data = self.api.get_group_info(self.group_id)
            subjects = group_data.get('subjects', [])
            for subject in subjects:
                subject_id = subject.get('id')
                subject_name = subject.get('name', 'Неизвестный предмет').strip()
                if subject_id and subject_name:
                    self._subject_cache[subject_id] = subject_name
            self._log(f"Загружено предметов: {len(self._subject_cache)}")
        except Exception as e:
            self._log(f"Ошибка при загрузке предметов: {e}")
            self._subject_cache = {}

    def _load_students(self):
        """
        Загружает список учеников группы и кэширует их.

        Errors:
            - Ошибка API приводит к пустому _student_cache.
            - Отсутствие учеников в ответе API.

        """
        try:
            students = self.api.get_groups_pupils(self.group_id)
            for student in students:
                student_id = student.get('id')
                student_name = student.get('shortName', 'Unknown')
                if student_id and student_name:
                    self._student_cache[student_id] = student_name
            self._log(f"Загружено учеников: {len(self._student_cache)}")
        except Exception as e:
            self._log(f"Ошибка при загрузке учеников: {e}")
            self._student_cache = {}

    def _load_teachers(self):
        """
        Загружает список учителей школы и кэширует их.

        Errors:
            - Ошибка API приводит к пустому _teacher_cache.
            - Отсутствие учителей в ответе API.

        """
        try:
            teachers_data = self.api.get(f"schools/{self.school_id}/teachers")
            for teacher in teachers_data:
                teacher_id = teacher.get('Id')
                if not teacher_id:
                    continue
                teacher_name = teacher.get('ShortName', 'Unknown')
                full_name = f"{teacher.get('FirstName', '')} {teacher.get('MiddleName', '')} {teacher.get('LastName', '')}".strip()
                self._teacher_cache[str(teacher_id)] = {
                    'shortName': teacher_name,
                    'fullName': full_name,
                    'subjects': teacher.get('Subjects', 'None'),
                    'email': teacher.get('Email', ''),
                    'position': teacher.get('NameTeacherPosition', 'Unknown')
                }
            self._log(f"Загружено учителей: {len(self._teacher_cache)}")
        except Exception as e:
            self._log(f"Ошибка при загрузке учителей: {e}")
            self._teacher_cache = {}

    def _format_lesson_time(self, lesson_number: int) -> str:
        """
        Преобразует номер урока в строку времени.

        Args:
            lesson_number (int): Номер урока (1–7).

        Returns:
            str: Время урока (например, "08:30-09:15") или "Неизвестное время" для некорректного номера.

        Errors:
            - Номер урока вне диапазона 1–7 возвращает "Неизвестное время".

        """
        lesson_times = {
            1: "08:30-09:15", 2: "09:20-10:05", 3: "10:15-11:00", 4: "11:15-12:00",
            5: "12:20-13:05", 6: "13:25-14:10", 7: "14:15-15:00"
        }
        return lesson_times.get(lesson_number, "Неизвестное время")

    def _get_formatted_schedule_day(self, date: datetime) -> List[Dict[str, str]]:
        """
        Получает расписание уроков за указанную дату, включая предметы, домашние задания, учителей и оценки.

        Args:
            date (datetime): Дата расписания.

        Returns:
            List[Dict[str, str]]: Список уроков, каждый содержит:
                - time: Время урока.
                - subject: Название предмета.
                - homework: Домашнее задание.
                - title: Тема урока.
                - teacher: Имя учителя.
                - marks: Оценки.
            Пустой список, если уроков нет или произошла ошибка.

        Errors:
            - Ошибка API при запросе уроков или оценок.
            - Некорректные данные урока (например, неверная дата или номер урока).
            - Отсутствие уроков на дату.

        """
        date_str = date.strftime('%Y-%m-%d')
        if date_str in self._schedule_cache:
            self._log(f"Использую кэшированное расписание для {date_str}")
            return self._schedule_cache[date_str]

        try:
            lessons = self.api.get_group_lessons_info(self.group_id, date, date)
            self._log(f"Ответ get_group_lessons_info для {date_str}: {len(lessons)} уроков")
        except Exception as e:
            self._log(f"Ошибка при получении расписания за {date_str}: {e}")
            lessons = []

        if not lessons:
            self._log(f"Нет уроков на {date_str}")
            self._schedule_cache[date_str] = []
            return []

        try:
            marks_start_date = date - timedelta(days=7)
            marks = self.api.get_person_marks(self.person_id, self.school_id, marks_start_date, date)
            self._log(f"Оценки за {marks_start_date.strftime('%Y-%m-%d')} - {date_str}: {len(marks)} оценок")
            lesson_ids_in_marks = list(set(mark.get('lesson_str', '0') for mark in marks))
            self._log(f"Lesson IDs в оценках для расписания: {lesson_ids_in_marks}")
        except Exception as e:
            self._log(f"Ошибка при получении оценок за {marks_start_date.strftime('%Y-%m-%d')} - {date_str}: {e}")
            marks = []

        formatted_schedule = []
        for lesson in lessons:
            lesson_date = datetime.strptime(lesson['date'], '%Y-%m-%dT%H:%M:%S')
            if lesson_date.date() != date.date():
                self._log(f"Пропущен урок с некорректной датой: {lesson['date']}")
                continue

            lesson_number = lesson.get('number', 0)
            if lesson_number not in range(1, 8):
                self._log(f"Пропущен урок с некорректным номером: {lesson_number}, предмет: {lesson.get('subject', {}).get('name', 'Неизвестный')}")
                continue

            subject = lesson.get('subject', {})
            subject_id = subject.get('id')
            subject_name = subject.get('name', 'Неизвестный предмет').strip()
            if subject_id and subject_name != 'Неизвестный предмет':
                self._subject_cache[subject_id] = subject_name

            teacher_id = lesson.get('teachers', [None])[0]
            if teacher_id and str(teacher_id) not in self._teacher_cache:
                try:
                    person_data = self.api.get(f"persons/{teacher_id}")
                    full_name = f"{person_data.get('firstName', '')} {person_data.get('middleName', '')} {person_data.get('lastName', '')}".strip()
                    self._teacher_cache[str(teacher_id)] = {
                        'shortName': person_data.get('shortName', 'Неизвестный преподаватель'),
                        'fullName': full_name,
                        'subjects': person_data.get('subjects', 'None'),
                        'email': person_data.get('email', ''),
                        'position': person_data.get('nameTeacherPosition', 'Unknown')
                    }
                    self._log(f"Добавлен учитель {teacher_id}: {self._teacher_cache[str(teacher_id)]['shortName']}")
                except Exception as e:
                    self._log(f"Ошибка при запросе учителя {teacher_id}: {e}")
                    self._teacher_cache[str(teacher_id)] = {
                        'shortName': 'Неизвестный преподаватель',
                        'fullName': 'Неизвестный преподаватель',
                        'subjects': 'None',
                        'email': '',
                        'position': 'Unknown'
                    }
            teacher_info = self._teacher_cache.get(str(teacher_id), {
                'shortName': 'Неизвестный преподаватель',
                'fullName': 'Неизвестный преподаватель',
                'subjects': 'None',
                'email': '',
                'position': 'Unknown'
            }) if teacher_id else {
                'shortName': 'Неизвестный преподаватель',
                'fullName': 'Неизвестный преподаватель',
                'subjects': 'None',
                'email': '',
                'position': 'Unknown'
            }

            works = lesson.get('works', [])
            homework = [work['text'] for work in works if work.get('type') == 'Homework' and work.get('text') and work['text'].lower() != 'нет задания']
            homework_text = '; '.join(homework) if homework else 'Нет задания'

            lesson_id = str(lesson.get('id', '0'))
            lesson_marks = [
                {
                    'value': mark['value'],
                    'date': datetime.strptime(mark.get('date', '1970-01-01'), '%Y-%m-%dT%H:%M:%S.%f').strftime('%Y-%m-%d'),
                    'comment': mark.get('mood', '')
                }
                for mark in marks
                if str(mark.get('lesson_str', '0')) == lesson_id
            ]
            marks_text = ', '.join([m['value'] for m in lesson_marks]) if lesson_marks else 'Нет оценок'
            self._log(f"Оценки для урока {lesson_id} ({subject_name}): {marks_text}")

            formatted_schedule.append({
                'time': self._format_lesson_time(lesson_number),
                'subject': subject_name,
                'homework': homework_text,
                'title': lesson.get('title', subject_name) or subject_name,
                'teacher': teacher_info['shortName'],
                'marks': marks_text
            })

        formatted_schedule = sorted(formatted_schedule, key=lambda x: x['time'])
        self._schedule_cache[date_str] = formatted_schedule
        return formatted_schedule

    def get_formatted_schedule(self, start_date: datetime, end_date: Optional[datetime] = None) -> Dict[str, List[Dict[str, str]]] | List[Dict[str, str]]:
        """
        Получает расписание уроков за одну дату или период.

        Args:
            start_date (datetime): Начальная дата расписания.
            end_date (Optional[datetime], optional): Конечная дата. Если None, возвращается расписание за start_date.

        Returns:
            Dict[str, List[Dict[str, str]]] | List[Dict[str, str]]: 
                - Если end_date=None: Список уроков за start_date.
                - Иначе: Словарь, где ключи — даты (YYYY-MM-DD), а значения — списки уроков.
                Каждый урок содержит: time, subject, homework, title, teacher, marks.
                Пустой список/словарь при ошибке или отсутствии уроков.

        Raises:
            ValueError: Если end_date раньше start_date.

        Errors:
            - Ошибка API при запросе уроков.
            - Некорректные данные уроков.

        """
        if end_date is None:
            return self._get_formatted_schedule_day(start_date)
        if end_date < start_date:
            raise ValueError("end_date не может быть раньше start_date")
        result = {}
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            result[date_str] = self._get_formatted_schedule_day(current_date)
            current_date += timedelta(days=1)
        return result

    def _get_lesson_info(self, lesson_id: str, force_refresh: bool = False) -> Optional[Dict]:
        """
        Получает данные об уроке по его ID, используя кэш или API.

        Args:
            lesson_id (str): ID урока.
            force_refresh (bool, optional): Принудительное обновление кэша. Defaults to False.

        Returns:
            Optional[Dict]: Данные урока (предмет, дата, работы и т.д.) или пустой словарь при ошибке.

        Errors:
            - Ошибка API при запросе урока.
            - Некорректный lesson_id.

        """
        if force_refresh or lesson_id not in self._lesson_cache:
            try:
                lesson_data = self.api.get_lesson_info(int(lesson_id))
                self._lesson_cache[lesson_id] = lesson_data
                subject_name = lesson_data.get('subject', {}).get('name', 'Неизвестный предмет')
                self._log(f"Загружена информация об уроке {lesson_id}: {lesson_data.get('title', 'No title')} (предмет: {subject_name})")
            except Exception as e:
                self._log(f"Ошибка при загрузке урока {lesson_id}: {e}")
                self._lesson_cache[lesson_id] = {}
        return self._lesson_cache[lesson_id] or {}

    def get_last_marks(self, count: int = 5, subject_id: Optional[int] = None) -> List[Dict[str, any]]:
        """
        Получает последние оценки ученика с фильтрацией по предмету.

        Args:
            count (int, optional): Количество возвращаемых оценок. Defaults to 5.
            subject_id (Optional[int], optional): ID предмета для фильтрации. Если None, все предметы.

        Returns:
            List[Dict[str, any]]: Список оценок, каждая содержит:
                - subject: Название предмета.
                - title: Тип работы (например, "Контрольная работа").
                - mark: Оценка.
                - class_distribution: Распределение оценок в классе (Dict[str, int]).
                - date: Дата оценки (DD.MM.YYYY).
                Пустой список при ошибке или отсутствии оценок.

        Errors:
            - Ошибка API при запросе оценок.
            - Отсутствие оценок за последние 90 дней.
            - Некорректный subject_id.

        """
        result = []
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)
            marks = self.api.get_person_marks(self.person_id, self.school_id, start_date, end_date)
            self._log(f"Получено {len(marks)} оценок за период {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')} для person_id={self.person_id}")
            for mark in marks:
                lesson_id = str(mark.get('lesson_str', '0'))
                mark_date = datetime.strptime(mark.get('date', '1970-01-01'), '%Y-%m-%dT%H:%M:%S.%f').date()
                lesson_data = self._get_lesson_info(lesson_id)
                subject_name = lesson_data.get('subject', {}).get('name', 'Неизвестный предмет')
                lesson_date = datetime.strptime(lesson_data.get('date', '1970-01-01'), '%Y-%m-%dT%H:%M:%S').date() if lesson_data.get('date') else None
                self._log(f"Оценка: lesson_id={lesson_id}, value={mark.get('value')}, mark_date={mark_date}, lesson_date={lesson_date}, subject={subject_name}")
            
            marks.sort(key=lambda x: (
                datetime.strptime(self._get_lesson_info(str(x.get('lesson_str', '0'))).get('date', '1970-01-01'), '%Y-%m-%dT%H:%M:%S').date()
                if self._get_lesson_info(str(x.get('lesson_str', '0'))).get('date')
                else datetime(1970, 1, 1),
                datetime.strptime(x.get('date', '1970-01-01'), '%Y-%m-%dT%H:%M:%S.%f')
            ), reverse=True)
            marks = marks[:count]
        except Exception as e:
            self._log(f"Ошибка при получении оценок: {e}")
            return result

        if not marks:
            self._log(f"Нет оценок за период {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')} для person_id={self.person_id}")
            return result

        work_type_mapping = {
            'CommonWork': 'Работа на уроке',
            'DefaultNewLessonWork': 'Работа на уроке',
            'LessonTestWork': 'Контрольная работа',
            'Homework': 'Домашняя работа'
        }

        number_to_word = {
            1: 'одна', 2: 'две', 3: 'три', 4: 'четыре', 5: 'пять',
            6: 'шесть', 7: 'семь', 8: 'восемь', 9: 'девять', 10: 'десять'
        }

        for mark in marks:
            lesson_id = str(mark.get('lesson_str', '0'))
            work_id = str(mark.get('work_str', '0'))
            mark_date = datetime.strptime(mark.get('date', '1970-01-01'), '%Y-%m-%dT%H:%M:%S.%f').date()
            subject_id_from_mark = None

            lesson_data = self._get_lesson_info(lesson_id) if lesson_id != '0' else {}
            if lesson_data and 'subject' in lesson_data and lesson_data['subject']:
                subject_id_from_mark = lesson_data['subject'].get('id')
                self._log(f"Для урока {lesson_id} определен предмет: {lesson_data['subject'].get('name')} (subject_id={subject_id_from_mark})")

            if subject_id and subject_id_from_mark != subject_id:
                self._log(f"Пропущена оценка для урока {lesson_id}: subject_id={subject_id_from_mark} не совпадает с запрошенным {subject_id}")
                continue

            mark_info = {
                'subject': 'Неизвестный предмет',
                'title': 'Работа на уроке',
                'mark': mark.get('value', 'Нет оценки'),
                'class_distribution': {},
                'date': datetime.strptime(mark.get('date', '1970-01-01'), '%Y-%m-%dT%H:%M:%S.%f').strftime('%d.%m.%Y')
            }

            if lesson_data and 'subject' in lesson_data and lesson_data['subject']:
                mark_info['subject'] = lesson_data['subject'].get('name', 'Неизвестный предмет').strip()
                subject_id_from_mark = lesson_data['subject'].get('id')
                lesson_title = lesson_data.get('title', 'Работа на уроке') or 'Работа на уроке'

                works = lesson_data.get('works', [])
                for work in works:
                    if str(work.get('id')) == work_id:
                        work_type = work.get('type', 'CommonWork')
                        mark_info['title'] = work_type_mapping.get(work_type, lesson_title)
                        break
                else:
                    mark_info['title'] = lesson_title

            try:
                if work_id != '0' and lesson_id != '0' and subject_id_from_mark:
                    class_dist = defaultdict(int)
                    for student_id in self._student_cache:
                        try:
                            student_marks = self.api.get_person_marks(student_id, self.school_id, start_date, end_date)
                            for student_mark in student_marks:
                                if (str(student_mark.get('lesson_str', '0')) == lesson_id and
                                    str(student_mark.get('work_str', '0')) == work_id and
                                    datetime.strptime(student_mark.get('date', '1970-01-01'), '%Y-%m-%dT%H:%M:%S.%f').date() ==
                                    mark_date):
                                    value = str(student_mark.get('value', ''))
                                    if value:
                                        class_dist[value] += 1
                        except Exception as e:
                            self._log(f"Ошибка при получении оценок для ученика {student_id}, урок {lesson_id}, работа {work_id}: {e}")
                            continue
                    mark_info['class_distribution'] = dict(class_dist)
                    self._log(f"Распределение оценок для работы {work_id}, урок {lesson_id}: {mark_info['class_distribution']}")
            except Exception as e:
                self._log(f"Ошибка при получении распределения оценок для работы {work_id}, урок {lesson_id}: {e}")

            result.append(mark_info)

        return result

    def get_group_teachers(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, str]]:
        """
        Получает список учителей группы за указанный период.

        Args:
            start_date (Optional[datetime], optional): Начальная дата. Defaults to текущая дата минус 7 дней.
            end_date (Optional[datetime], optional): Конечная дата. Defaults to текущая дата плюс 30 дней.

        Returns:
            List[Dict[str, str]]: Список учителей, каждый содержит:
                - id: ID учителя.
                - fullName: Полное имя.
                - shortName: Краткое имя.
                - subjects: Предметы.
                - email: Email.
                - position: Должность.
                Пустой список при ошибке или отсутствии учителей.

        Raises:
            ValueError: Если end_date раньше start_date.

        Errors:
            - Ошибка API при запросе уроков или данных учителя.
            - Отсутствие уроков в периоде.

        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now() + timedelta(days=30)
        if end_date < start_date:
            raise ValueError("end_date не может быть раньше start_date")
        try:
            lessons = self.api.get_group_lessons_info(self.group_id, start_date, end_date)
        except Exception as e:
            self._log(f"Ошибка при получении уроков: {e}")
            return []
        teacher_ids = set()
        for lesson in lessons:
            for teacher_id in lesson.get('teachers', []):
                teacher_ids.add(str(teacher_id))
        for teacher_id in teacher_ids:
            if teacher_id not in self._teacher_cache:
                try:
                    person_data = self.api.get(f"persons/{teacher_id}")
                    full_name = f"{person_data.get('firstName', '')} {person_data.get('middleName', '')} {person_data.get('LastName', '')}".strip()
                    self._teacher_cache[teacher_id] = {
                        'shortName': person_data.get('shortName', 'Неизвестный преподаватель'),
                        'fullName': full_name,
                        'subjects': person_data.get('subjects', 'None'),
                        'email': person_data.get('email', ''),
                        'position': person_data.get('nameTeacherPosition', 'Unknown')
                    }
                except Exception as e:
                    self._log(f"Ошибка при запросе учителя {teacher_id}: {e}")
                    self._teacher_cache[teacher_id] = {
                        'shortName': 'Неизвестный преподаватель',
                        'fullName': 'Неизвестный преподаватель',
                        'subjects': 'None',
                        'email': '',
                        'position': 'Unknown'
                    }
        result = []
        for teacher_id in sorted(teacher_ids):
            teacher_info = self._teacher_cache[teacher_id]
            result.append({
                'id': teacher_id,
                'fullName': teacher_info['fullName'],
                'shortName': teacher_info['shortName'],
                'subjects': teacher_info['subjects'],
                'email': teacher_info['email'],
                'position': teacher_info['position']
            })
        return result

    def get_formatted_marks(self, start_date: datetime, end_date: Optional[datetime] = None) -> Dict[str, List[Dict[str, str]]]:
        """
        Получает оценки за период, сгруппированные по предметам.

        Args:
            start_date (datetime): Начальная дата периода.
            end_date (Optional[datetime], optional): Конечная дата. Defaults to start_date.

        Returns:
            Dict[str, List[Dict[str, str]]]: Словарь, где ключи — названия предметов, а значения — списки оценок:
                - date: Дата оценки (DD.MM.YYYY).
                - value: Оценка.
                - comment: Комментарий к оценке.
                Пустой словарь при ошибке или отсутствии оценок.

        Errors:
            - Ошибка API при запросе оценок или домашнего задания.
            - Отсутствие оценок в периоде.
            - Некорректные данные урока (например, неизвестная дата).

        """
        if end_date is None:
            end_date = start_date
        query_start_date = start_date - timedelta(days=7)
        try:
            marks_data = self.api.get_person_marks(self.person_id, self.school_id, query_start_date, end_date)
            self._log(f"Получено {len(marks_data)} оценок за {query_start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')} для person_id={self.person_id}")
            lesson_ids_in_marks = list(set(mark.get('lesson_str', '0') for mark in marks_data))
            self._log(f"Lesson IDs в оценках: {lesson_ids_in_marks}")
        except Exception as e:
            self._log(f"Ошибка при получении оценок за {query_start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}: {e}")
            return {}
        
        lesson_ids = list(set(mark['lesson_str'] for mark in marks_data if 'lesson_str' in mark))
        lesson_subjects = {}
        lesson_dates = {}
        for lesson_id in lesson_ids:
            lesson_data = self._get_lesson_info(lesson_id)
            if lesson_data and 'subject' in lesson_data and lesson_data['subject'] and 'id' in lesson_data['subject']:
                subject_id = lesson_data['subject']['id']
                lesson_subjects[lesson_id] = subject_id
                lesson_date_str = lesson_data.get('date', '1970-01-01')
                try:
                    lesson_date = datetime.strptime(lesson_date_str, '%Y-%m-%dT%H:%M:%S').date()
                    lesson_dates[lesson_id] = lesson_date
                except ValueError:
                    self._log(f"Некорректный формат даты урока {lesson_id}: {lesson_date_str}")
                    lesson_dates[lesson_id] = None
            else:
                self._log(f"Нет данных о предмете для урока {lesson_id}")
        
        try:
            homework_data = self.api.get_school_homework(self.school_id, start_date, end_date)
            subjects = {s['id']: s['name'] for s in homework_data.get('subjects', []) if s.get('id') and s.get('name')}
            self._subject_cache.update(subjects)
        except Exception as e:
            self._log(f"Ошибка при получении данных о домашнем задании: {e}")
            subjects = {}
        
        formatted_marks = defaultdict(list)
        for mark in marks_data:
            lesson_id = mark.get('lesson_str', '0')
            subject_id = lesson_subjects.get(lesson_id) if lesson_id != '0' else None
            subject_name = self._subject_cache.get(subject_id, 'Неизвестный предмет').strip() if subject_id else 'Неизвестный предмет'
            mark_date = datetime.strptime(mark.get('date', '1970-01-01T00:00:00'), '%Y-%m-%dT%H:%M:%S.%f').date()
            
            lesson_date = lesson_dates.get(lesson_id)
            if lesson_date is None:
                self._log(f"Пропущена оценка для урока {lesson_id} с неизвестной датой урока")
                continue
            if lesson_date < start_date.date() or lesson_date > end_date.date():
                self._log(f"Пропущена оценка для урока {lesson_id} с датой урока {lesson_date} вне диапазона {start_date.date()} - {end_date.date()}")
                continue
            
            if mark_date != lesson_date:
                self._log(f"Оценка для урока {lesson_id} (дата урока: {lesson_date}) имеет дату оценки {mark_date}")
            
            formatted_marks[subject_name].append({
                'date': mark_date.strftime('%d.%m.%Y'),
                'value': str(mark.get('value', 'Нет оценки')),
                'comment': mark.get('mood', '')
            })
        
        for subject in formatted_marks:
            formatted_marks[subject] = sorted(formatted_marks[subject], key=lambda x: x['date'])
        return dict(formatted_marks)

    def _get_quarter_period_id(self, study_year: int, quarter: int) -> Optional[Tuple[int, datetime, datetime]]:
        """
        Получает ID и даты учебного периода для указанной четверти.

        Args:
            study_year (int): Учебный год.
            quarter (int): Номер четверти (1–4).

        Returns:
            Optional[Tuple[int, datetime, datetime]]: ID периода, начальная и конечная даты.
            None при ошибке или отсутствии периода.

        Errors:
            - Ошибка API при запросе периодов.
            - Отсутствие периода для указанного года и четверти.

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
            self._log(f"Не найдены периоды для четверти {quarter} в учебном году {study_year}")
            return None
        except Exception as e:
            self._log(f"Ошибка при получении периодов: {e}")
            return None

    def get_formatted_final_marks(self, study_year: int, quarter: int) -> List[Dict[str, str]]:
        """
        Получает итоговые оценки за четверть.

        Args:
            study_year (int): Учебный год.
            quarter (int): Номер четверти (1–4).

        Returns:
            List[Dict[str, str]]: Список итоговых оценок:
                - название предмета: Название предмета.
                - оценки: Список оценок.
                - итог: Средняя оценка.
                Пустой список при ошибке или отсутствии оценок.

        Raises:
            ValueError: Если quarter не в диапазоне 1–4.

        Errors:
            - Ошибка API при запросе оценок.
            - Отсутствие оценок в периоде.

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
        """
        Формирует рейтинг учеников класса по средней оценке за четверть.

        Args:
            study_year (int): Учебный год.
            quarter (int): Номер четверти (1–4).

        Returns:
            List[Dict]: Список учеников, отсортированный по убыванию средней оценки:
                - name: Имя ученика.
                - avg_grade: Средняя оценка.
                - marks_count: Количество оценок.
                Пустой список при ошибке.

        Raises:
            ValueError: Если quarter не в диапазоне 1–4.

        Errors:
            - Ошибка API при запросе оценок.
            - Отсутствие оценок для учеников.

        """
        if quarter not in [1, 2, 3, 4]:
            raise ValueError("Номер четверти должен быть от 1 до 4")
        period_data = self._get_quarter_period_id(study_year, quarter)
        if not period_data:
            return []
        period_id, start_date, finish_date = period_data
        grade_mapping = {'отлично': 5, 'хорошо': 4, 'удовлетворительно': 3, 'неудовлетворительно': 2}
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
                except Exception as e:
                    self._log(f"Ошибка при получении оценок для ученика {student_id}, предмет {subject_id}: {e}")
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
        """
        Получает гистограмму оценок по предмету за четверть.

        Args:
            study_year (int): Учебный год.
            quarter (int): Номер четверти (1–4).
            subject_id (int): ID предмета.

        Returns:
            Dict[str, int]: Словарь, где ключи — оценки, а значения — их количество.
            Пустой словарь при ошибке.

        Raises:
            ValueError: Если quarter не в диапазоне 1–4.

        Errors:
            - Ошибка API при запросе статистики.
            - Отсутствие оценок по предмету.

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
            for work in histogram.get('works', []):
                for mark_number in work.get('markNumbers', []):
                    for mark in mark_number.get('marks', []):
                        value = str(mark.get('value'))
                        count = mark.get('count', 0)
                        hist_data[value] += count
            return dict(hist_data)
        except Exception as e:
            self._log(f"Ошибка при получении статистики по предмету {subject_id}: {e}")
            return {}

    def get_subject_ranking(self, study_year: int, quarter: int, subject_id: int) -> List[Dict]:
        """
        Формирует рейтинг учеников по предмету за четверть.

        Args:
            study_year (int): Учебный год.
            quarter (int): Номер четверти (1–4).
            subject_id (int): ID предмета.

        Returns:
            List[Dict]: Список учеников, отсортированный по средней оценке:
                - name: Имя ученика.
                - avg_grade: Средняя оценка.
                - marks_count: Количество оценок.
                Пустой список при ошибке.

        Raises:
            ValueError: Если quarter не в диапазоне 1–4.

        Errors:
            - Ошибка API при запросе оценок.
            - Отсутствие оценок по предмету.

        """
        if quarter not in [1, 2, 3, 4]:
            raise ValueError("Номер четверти должен быть от 1 до 4")
        period_data = self._get_quarter_period_id(study_year, quarter)
        if not period_data:
            return []
        period_id, start_date, finish_date = period_data
        grade_mapping = {'отлично': 5, 'хорошо': 4, 'удовлетворительно': 3, 'неудовлетворительно': 2}
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
            except Exception as e:
                self._log(f"Ошибка при получении оценок для ученика {student_id}, предмет {subject_id}: {e}")
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
        """
        Получает статистику класса за четверть (общее количество оценок, средняя оценка, распределение).

        Args:
            study_year (int): Учебный год.
            quarter (int): Номер четверти (1–4).

        Returns:
            Dict: Статистика:
                - total_marks: Количество оценок.
                - average_class_grade: Средняя оценка класса.
                - grade_distribution: Процентное распределение оценок.
                Пустой словарь при ошибке.

        Raises:
            ValueError: Если quarter не в диапазоне 1–4.

        Errors:
            - Ошибка API при запросе статистики.
            - Отсутствие оценок в классе.

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
                for work in histogram.get('works', []):
                    for mark_number in work.get('markNumbers', []):
                        for mark in mark_number.get('marks', []):
                            value = str(mark.get('value'))
                            count = mark.get('count', 0)
                            if value.replace('.', '', 1).isdigit():
                                total_grades[value] += count
                                total_marks += count
            except Exception as e:
                self._log(f"Ошибка при получении статистики по предмету {subject_id}: {e}")
                continue
        average_class_grade = sum(float(k) * v for k, v in total_grades.items()) / total_marks if total_marks else 0
        grade_distribution = {k: v / total_marks * 100 for k, v in total_grades.items()} if total_marks else {}
        return {
            'total_marks': total_marks,
            'average_class_grade': round(average_class_grade, 2),
            'grade_distribution': grade_distribution
        }

