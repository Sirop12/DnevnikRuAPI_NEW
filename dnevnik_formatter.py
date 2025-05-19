import uuid
from pydnevnikruapi.dnevnik import dnevnik
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import statistics
from collections import defaultdict
import json

class DnevnikFormatter:
    """
    Класс для обработки и форматирования данных, полученных через API Дневник.ру.
    Предоставляет методы для работы с расписанием, оценками, информацией об учителях и
    статистикой класса. Использует кэширование для оптимизации запросов к API и
    обеспечивает обработку ошибок для повышения надёжности.
    """

    def __init__(self, token: str, debug_mode: bool = True):
        """
        Инициализирует экземпляр класса DnevnikFormatter, устанавливая соединение с API
        Дневник.ру и загружая базовые данные (предметы, ученики, учителя, типы работ).

        **Назначение**:
        Создаёт объект для работы с API, извлекает идентификаторы пользователя, школы и группы,
        инициализирует кэши и загружает начальные данные для дальнейшей работы.

        **Входные параметры**:
        - token (str): Токен авторизации для доступа к API Дневник.ру.
                       Должен быть действительным строковым токеном, полученным от API.
                       Пример: "42r2fdvf5g53gr45".
        - debug_mode (bool, необязательный): Флаг для включения отладочного логирования.
                                            Если True, в консоль выводятся подробные сообщения
                                            о действиях и ошибках. По умолчанию True.

        **Выходные данные**:
        - None: Метод не возвращает значений, но инициализирует объект класса, устанавливая
                внутренние атрибуты и кэши.

        **Алгоритм работы**:
        1. Создаёт клиент API с использованием предоставленного токена.
        2. Запрашивает контекст пользователя через endpoint /v2/users/me/context.
        3. Извлекает person_id, school_id и group_id из ответа API.
        4. Проверяет наличие всех идентификаторов; если хотя бы один отсутствует, вызывает исключение.
        5. Инициализирует словари для кэширования данных об уроках, предметах, учениках, учителях,
           расписании и типах работ.
        6. Вызывает методы для загрузки начальных данных: _load_subjects, _load_students,
           _load_teachers, _load_work_types.
        7. Логирует процесс инициализации, если включён debug_mode.

        **Исключения**:
        - ValueError: Вызывается, если не удалось получить person_id, school_id или group_id.
        - Exception: Любые ошибки API или сетевые проблемы логируются и перебрасываются.

        **Примечания**:
        - Кэши используются для минимизации запросов к API и ускорения работы.
        - Все идентификаторы преобразуются в строки для консистентности.
        - Логирование помогает диагностировать проблемы, особенно при нестабильном соединении.
        """
        # Инициализация клиента API с токеном
        self.api = dnevnik.DiaryAPI(token=token)
        # Сохранение режима отладки
        self.debug_mode = debug_mode

        try:
            # Запрос контекста пользователя
            self.context = self.api.get("users/me/context")
            # Логирование сырого ответа для отладки
            self._log(f"Ответ от /v2/users/me/context:\n{json.dumps(self.context, ensure_ascii=False, indent=2)}")

            # Извлечение идентификаторов
            self.person_id = str(self.context.get('personId', '0'))
            self.school_id = str(self.context.get('schools', [{}])[0].get('id', '0'))
            self.group_id = str(self.context.get('eduGroups', [{}])[0].get('id_str', '0'))

            # Проверка наличия идентификаторов
            if not self.person_id or not self.school_id or not self.group_id:
                raise ValueError("Не удалось получить person_id, school_id или group_id из контекста")

        except Exception as e:
            # Логирование ошибки и переброс исключения
            self._log(f"Ошибка при получении контекста: {str(e)}")
            raise

        # Инициализация кэшей
        self._lesson_cache = {}  # Кэш уроков: {lesson_id: lesson_data}
        self._subject_cache = {}  # Кэш предметов: {subject_id: subject_name}
        self._student_cache = {}  # Кэш учеников: {student_id: student_name}
        self._teacher_cache = {}  # Кэш учителей: {teacher_id: teacher_info}
        self._schedule_cache = {}  # Кэш расписания: {date_str: schedule_data}
        self._work_types_cache = {}  # Кэш типов работ: {work_type_id: work_type_name}

        # Логирование успешной инициализации
        self._log(f"Инициализация завершена: person_id={self.person_id}, school_id={self.school_id}, group_id={self.group_id}")

        # Загрузка начальных данных
        self._load_subjects()
        self._load_students()
        self._load_teachers()
        self._load_work_types()

    def clear_schedule_cache(self):
        """
        Очищает кэш расписания, заставляя последующие запросы загружать данные заново.

        **Назначение**:
        Сбрасывает кэш расписания, чтобы обеспечить получение актуальных данных при следующем
        вызове методов, работающих с расписанием (например, get_formatted_schedule).

        **Входные параметры**:
        - None

        **Выходные данные**:
        - None: Метод не возвращает значений, но изменяет внутренний кэш.

        **Алгоритм работы**:
        1. Устанавливает _schedule_cache в пустой словарь.
        2. Логирует действие, если включён debug_mode.

        **Примечания**:
        - Используется, если данные в кэше устарели или требуется принудительное обновление.
        """
        self._schedule_cache = {}
        self._log("Кэш расписания очищен")

    def _log(self, message: str):
        """
        Логирует отладочное сообщение в консоль, если включён режим отладки.

        **Назначение**:
        Обеспечивает централизованное логирование для отладки, позволяя включать или отключать
        вывод сообщений в зависимости от debug_mode.

        **Входные параметры**:
        - message (str): Сообщение для вывода в консоль. Может содержать любую информацию,
                         например, статус операции или ошибку.

        **Выходные данные**:
        - None: Метод только выводит сообщение, не возвращая значений.

        **Алгоритм работы**:
        1. Проверяет, включён ли debug_mode.
        2. Если debug_mode == True, выводит сообщение в консоль с помощью print.

        **Примечания**:
        - Помогает отслеживать выполнение программы и диагностировать ошибки.
        - Не влияет на функциональность, если debug_mode отключён.
        """
        if self.debug_mode:
            print(message)

    def _load_work_types(self):
        """
        Загружает список типов работ школы из API и кэширует их.

        **Назначение**:
        Получает типы работ (например, "Контрольная работа", "Домашняя работа") для школы
        и сохраняет их в кэш для использования в других методах, таких как get_last_marks.

        **Входные параметры**:
        - None: Метод использует self.school_id из инициализированного объекта.

        **Выходные данные**:
        - None: Метод изменяет внутренний кэш _work_types_cache, не возвращая значений.

        **Алгоритм работы**:
        1. Сбрасывает _work_types_cache в пустой словарь.
        2. Проверяет, что school_id определён и не равен '0'.
        3. Запрашивает типы работ через endpoint /work-types/{school_id}.
        4. Для каждого типа работы извлекает id и title, преобразует id в строку,
           удаляет пробелы из title и сохраняет в кэш.
        5. Логирует количество загруженных типов и их содержимое (если debug_mode).
        6. Если запрос не удался, использует запасной набор типов работ и логирует это.
        7. При ошибке school_id вызывает исключение ValueError.

        **Исключения**:
        - ValueError: Если school_id не определён или равен '0'.
        - Exception: Ловится для перехода к запасному набору типов работ.

        **Примечания**:
        - Формат ответа API: список словарей с ключами id (int) и title (str).
        - Запасной набор используется для устойчивости при сбоях API.
        - Кэш: {work_type_id (str): work_type_name (str)}.
        """
        self._work_types_cache = {}
        try:
            if not self.school_id or self.school_id == '0':
                raise ValueError("school_id не определён")
            work_types = self.api.get(f"work-types/{self.school_id}")
            for wt in work_types:
                work_type_id = str(wt.get('id', '0'))
                work_type_name = wt.get('title', 'Неизвестный тип').strip()
                if work_type_id and work_type_name:
                    self._work_types_cache[work_type_id] = work_type_name
            self._log(f"Загружено типов работ: {len(self._work_types_cache)}")
            if self.debug_mode:
                self._log(f"Типы работ:\n{json.dumps(self._work_types_cache, ensure_ascii=False, indent=2)}")
        except Exception as e:
            self._log(f"Ошибка при загрузке типов работ: {str(e)}")
            self._work_types_cache = {
                'CommonWork': 'Работа на уроке',
                'DefaultNewLessonWork': 'Работа на уроке',
                'LessonTestWork': 'Контрольная работа',
                'Homework': 'Домашняя работа',
                'CreativeWork': 'Творческая работа'
            }
            self._log(f"Использован запасной набор типов работ: {len(self._work_types_cache)}")

    def _load_subjects(self):
        """
        Загружает список предметов группы из API и кэширует их.

        **Назначение**:
        Получает список учебных предметов для группы (например, "Математика", "Русский язык")
        и сохраняет их в кэш для использования в методах, таких как get_formatted_schedule.

        **Входные параметры**:
        - None: Метод использует self.group_id и self.person_id.

        **Выходные данные**:
        - None: Метод изменяет внутренний кэш _subject_cache.

        **Алгоритм работы**:
        1. Сбрасывает _subject_cache в пустой словарь.
        2. Пытается загрузить предметы через /edu-groups/{group_id}/subjects.
        3. Для каждого предмета извлекает id и name, преобразует id в строку,
           удаляет пробелы из name и сохраняет в кэш.
        4. Логирует количество загруженных предметов.
        5. Если запрос не удался, переходит к запасному варианту:
           - Запрашивает расписание за учебный год (1 сентября - 31 августа).
           - Извлекает предметы из поля subjects в расписании.
           - Если предметы не найдены, пробует последние 30 дней.
        6. Логирует все попытки и результаты.
        7. Если debug_mode включён, выводит содержимое кэша.

        **Исключения**:
        - Exception: Ловится для перехода к запасным методам загрузки.

        **Примечания**:
        - Формат ответа /edu-groups/{group_id}/subjects: список словарей с id (int) и name (str).
        - Расписание запрашивается с тремя попытками для устойчивости.
        - Кэш: {subject_id (str): subject_name (str)}.
        """
        self._subject_cache = {}
        try:
            subjects = self.api.get(f"edu-groups/{self.group_id}/subjects")
            for subject in subjects:
                subject_id = str(subject.get('id'))
                subject_name = subject.get('name', 'Неизвестный предмет').strip()
                if subject_id and subject_name:
                    self._subject_cache[subject_id] = subject_name
            self._log(f"Загружено предметов из /edu-groups/subjects: {len(self._subject_cache)}")
        except Exception as e:
            self._log(f"Ошибка при загрузке предметов из /edu-groups/subjects: {str(e)}")
            try:
                now = datetime.now()
                start_date = now.replace(month=9, day=1, hour=0, minute=0, second=0, microsecond=0)
                if start_date > now:
                    start_date = start_date.replace(year=start_date.year - 1)
                end_date = start_date.replace(year=start_date.year + 1, month=8, day=31, hour=23, minute=59, second=59, microsecond=999999)
                max_attempts = 1
                attempt = 1
                schedule = {'days': []}
                while attempt <= max_attempts:
                    try:
                        schedule = self.api.get(
                            f"persons/{self.person_id}/groups/{self.group_id}/schedules",
                            params={
                                "startDate": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                "endDate": end_date.strftime("%Y-%m-%dT%H:%M:%S")
                            }
                        )
                        break
                    except Exception as e:
                        self._log(f"Попытка {attempt}/{max_attempts} не удалась: Ошибка при загрузке расписания: {str(e)}")
                        attempt += 1
                for day in schedule.get('days', []):
                    for subject in day.get('subjects', []):
                        subject_id = str(subject.get('id'))
                        subject_name = subject.get('name', 'Неизвестный предмет').strip()
                        if subject_id and subject_name:
                            self._subject_cache[subject_id] = subject_name
                self._log(f"Загружено предметов из расписания за год: {len(self._subject_cache)}")
                if not self._subject_cache:
                    self._log("Предметы не найдены за год, пробую последние 30 дней")
                    start_date = now - timedelta(days=30)
                    end_date = now
                    schedule = self.api.get(
                        f"persons/{self.person_id}/groups/{self.group_id}/schedules",
                        params={
                            "startDate": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
                            "endDate": end_date.strftime("%Y-%m-%dT%H:%M:%S")
                        }
                    )
                    for day in schedule.get('days', []):
                        for subject in day.get('subjects', []):
                            subject_id = str(subject.get('id'))
                            subject_name = subject.get('name', 'Неизвестный предмет').strip()
                            if subject_id and subject_name:
                                self._subject_cache[subject_id] = subject_name
                    self._log(f"Загружено предметов из расписания за 30 дней: {len(self._subject_cache)}")
            except Exception as e:
                self._log(f"Ошибка при загрузке предметов из расписания: {str(e)}")
        if self.debug_mode:
            self._log(f"Предметы:\n{json.dumps(self._subject_cache, ensure_ascii=False, indent=2)}")

    def _load_students(self):
        """
        Загружает список учеников группы из API и кэширует их.

        **Назначение**:
        Получает информацию об учениках группы для использования в методах, таких как
        get_class_ranking и get_subject_ranking.

        **Входные параметры**:
        - None: Метод использует self.group_id.

        **Выходные данные**:
        - None: Метод изменяет внутренний кэш _student_cache.

        **Алгоритм работы**:
        1. Запрашивает учеников через метод API get_groups_pupils.
        2. Для каждого ученика извлекает id и shortName, преобразует id в строку.
        3. Сохраняет данные в кэш, если id и имя валидны.
        4. Логирует количество загруженных учеников.
        5. При ошибке устанавливает пустой кэш и логирует ошибку.

        **Исключения**:
        - Exception: Ловится для обработки ошибок API.

        **Примечания**:
        - Формат ответа: список словарей с id (int) и shortName (str).
        - Кэш: {student_id (str): student_name (str)}.
        """
        try:
            students = self.api.get_groups_pupils(self.group_id)
            for student in students:
                student_id = str(student.get('id'))
                student_name = student.get('shortName', 'Неизвестный')
                if student_id and student_name:
                    self._student_cache[student_id] = student_name
            self._log(f"Загружено учеников: {len(self._student_cache)}")
        except Exception as e:
            self._log(f"Ошибка при загрузке учеников: {str(e)}")
            self._student_cache = {}

    def _load_teachers(self):
        """
        Загружает список учителей школы из API и кэширует их.

        **Назначение**:
        Получает информацию об учителях школы для использования в методах, таких как
        get_group_teachers.

        **Входные параметры**:
        - None: Метод использует self.school_id.

        **Выходные данные**:
        - None: Метод изменяет внутренний кэш _teacher_cache.

        **Алгоритм работы**:
        1. Запрашивает учителей через endpoint /schools/{school_id}/teachers.
        2. Для каждого учителя извлекает Id, ShortName, FirstName, MiddleName, LastName,
           Subjects, Email, NameTeacherPosition.
        3. Формирует полное имя и сохраняет данные в кэш в виде словаря.
        4. Пропускает записи без Id.
        5. Логирует количество загруженных учителей.
        6. При ошибке устанавливает пустой кэш и логирует ошибку.

        **Исключения**:
        - Exception: Ловится для обработки ошибок API.

        **Примечания**:
        - Формат ответа: список словарей с указанными ключами.
        - Кэш: {teacher_id (str): {shortName, fullName, subjects, email, position}}.
        """
        try:
            teachers = self.api.get(f"schools/{self.school_id}/teachers")
            for teacher in teachers:
                teacher_id = str(teacher.get('Id'))
                if not teacher_id:
                    continue
                teacher_name = teacher.get('ShortName', 'Неизвестно')
                full_name = f"{teacher.get('FirstName', '')} {teacher.get('MiddleName', '')} {teacher.get('LastName', '')}".strip()
                self._teacher_cache[teacher_id] = {
                    'shortName': teacher_name,
                    'fullName': full_name,
                    'subjects': teacher.get('Subjects', 'Неизвестно'),
                    'email': teacher.get('Email', ''),
                    'position': teacher.get('NameTeacherPosition', 'Неизвестно')
                }
            self._log(f"Загружено учителей: {len(self._teacher_cache)}")
        except Exception as e:
            self._log(f"Ошибка при загрузке учителей: {str(e)}")
            self._teacher_cache = {}

    def _get_lesson_info(self, lesson_id: str, force_refresh: bool = False) -> Optional[Dict]:
        """
        Получает информацию об уроке по его идентификатору, используя кэш или API.

        **Назначение**:
        Извлекает данные об уроке (например, тему, предмет, работы) для использования в методах,
        таких как get_last_marks.

        **Входные параметры**:
        - lesson_id (str): Идентификатор урока. Должен быть строкой, не равной '0' или пустой.
        - force_refresh (bool, необязательный): Если True, игнорирует кэш и запрашивает данные
                                              заново. По умолчанию False.

        **Выходные данные**:
        - Optional[Dict]: Словарь с данными урока (например, title, subject, works) или
                          пустой словарь, если lesson_id некорректен или данные не получены.

        **Алгоритм работы**:
        1. Проверяет, что lesson_id валиден.
        2. Если force_refresh=False и lesson_id есть в _lesson_cache, возвращает кэшированные данные.
        3. Иначе запрашивает данные через get_lesson_info, преобразовав lesson_id в int.
        4. Кэширует полученные данные.
        5. При ошибке кэширует пустой словарь и возвращает его.
        6. Логирует процесс загрузки.

        **Исключения**:
        - Exception: Ловится для обработки ошибок API.

        **Примечания**:
        - Формат ответа API: словарь с ключами title (str), subject (dict), works (list).
        - Кэш: {lesson_id (str): lesson_data (dict)}.
        """
        if not lesson_id or lesson_id == '0':
            self._log(f"Некорректный lesson_id: {lesson_id}")
            return {}
        if force_refresh or lesson_id not in self._lesson_cache:
            try:
                lesson_data = self.api.get_lesson_info(int(lesson_id))
                self._lesson_cache[lesson_id] = lesson_data
                self._log(f"Загружен урок {lesson_id}: {lesson_data.get('title', 'Без названия')}")
            except Exception as e:
                self._log(f"Ошибка при загрузке урока {lesson_id}: {str(e)}")
                self._lesson_cache[lesson_id] = {}
        return self._lesson_cache.get(lesson_id, {})

    def _get_formatted_schedule_day(self, date: datetime) -> List[Dict[str, any]]:
        """
        Получает и форматирует расписание уроков за указанную дату.

        **Назначение**:
        Извлекает данные расписания за один день и преобразует их в структурированный список
        уроков с информацией о времени, предмете, домашнем задании, учителе и оценках.

        **Входные параметры**:
        - date (datetime): Дата, для которой нужно получить расписание.

        **Выходные данные**:
        - List[Dict[str, any]]: Список словарей, каждый из которых описывает урок со следующими
                                ключами:
                                - time (str): Время урока.
                                - subject (str): Название предмета.
                                - homework (str): Текст домашнего задания.
                                - files (list): Список файлов домашнего задания.
                                - title (str): Название или тема урока.
                                - teacher (str): Имя учителя.
                                - mark_details (list): Список оценок.
                                - classroom (str): Место проведения урока.
                                - lesson_id (str): ID урока.
                                - works (list): Список работ.
                                - lesson_number (int): Номер урока.
                                - lesson_status (str): Статус урока.
                                - attendance (str): Посещаемость.
                                - is_important (bool): Флаг важности задания.
                                - sent_date (str): Дата отправки задания.

        **Алгоритм работы**:
        1. Форматирует дату в строку YYYY-MM-DD.
        2. Проверяет, есть ли расписание в кэше _schedule_cache.
        3. Если нет, запрашивает расписание через /persons/{person_id}/groups/{group_id}/schedules.
        4. Извлекает данные о предметах, учителях, работах, оценках и файлах.
        5. Обновляет кэши предметов и учителей.
        6. Форматирует уроки, исключая дубликаты.
        7. Обрабатывает домашние задания и оценки.
        8. Сортирует уроки по номеру.
        9. Кэширует и возвращает результат.
        10. При ошибке возвращает пустой список.

        **Исключения**:
        - Exception: Ловится для обработки ошибок API.

        **Примечания**:
        - Формат ответа API: словарь с полем days, содержащим список дней.
        - Использует множество для исключения дублирующихся уроков.
        """
        date_str = date.strftime('%Y-%m-%d')
        if date_str in self._schedule_cache:
            self._log(f"Использую кэшированное расписание для {date_str}")
            return self._schedule_cache[date_str]
        try:
            schedule = self.api.get(
                f"persons/{self.person_id}/groups/{self.group_id}/schedules",
                params={
                    "startDate": date.strftime("%Y-%m-%dT00:00:00"),
                    "endDate": date.strftime("%Y-%m-%dT23:59:59")
                }
            )
            self._log(f"Сырой ответ расписания:\n{json.dumps(schedule, ensure_ascii=False, indent=2)}")
        except Exception as e:
            self._log(f"Ошибка при получении расписания: {str(e)}")
            self._schedule_cache[date_str] = []
            return []
        if not schedule.get('days'):
            self._log(f"Нет данных расписания для {date_str}")
            self._schedule_cache[date_str] = []
            return []
        formatted_schedule = []
        seen_lesson_ids = set()
        for day in schedule.get('days', []):
            if not day.get('date', '').startswith(date_str):
                continue
            subjects = {str(s['id']): s['name'] for s in day.get('subjects', [])}
            for subject_id, subject_name in subjects.items():
                if subject_id not in self._subject_cache:
                    self._subject_cache[subject_id] = subject_name
                    self._log(f"Добавлен предмет в _subject_cache: {subject_id} -> {subject_name}")
            teachers = {str(t['person']['id']): t['person']['shortName'] for t in day.get('teachers', [])}
            homeworks = {str(w['id']): w for w in day.get('homeworks', [])}
            works = {str(w['id']): w for w in day.get('works', [])}
            work_types = {str(wt['id']): wt['name'] for wt in day.get('workTypes', [])}
            lesson_logs = {str(l['lesson_str']): l['status'] for l in day.get('lessonLogEntries', []) 
                          if str(l['person_str']) == self.person_id}
            marks = {str(m['work']): m for m in day.get('marks', []) if str(m['person']) == self.person_id}
            files = {str(f['id']): f for f in day.get('files', [])}
            for lesson in day.get('lessons', []):
                lesson_id = str(lesson.get('id', '0'))
                if lesson_id in seen_lesson_ids:
                    self._log(f"Пропущен дублирующийся урок ID={lesson_id}")
                    continue
                seen_lesson_ids.add(lesson_id)
                subject_id = str(lesson.get('subjectId', '0'))
                if subject_id not in subjects:
                    self._log(f"Пропущен урок ID={lesson_id}: subject_id={subject_id} отсутствует")
                    continue
                lesson_number = lesson.get('number', 0)
                subject_name = subjects.get(subject_id, 'Неизвестный предмет')
                teacher_ids = lesson.get('teachers', [])
                teacher_name = ', '.join(teachers.get(str(t), 'Неизвестно') for t in teacher_ids) or 'Неизвестно'
                floor = lesson.get('floor', '')
                classroom = f"{lesson.get('building', '')} {lesson.get('place', 'Не указан')}".strip()
                if floor:
                    classroom += f", этаж {floor}"
                lesson_title = lesson.get('title', subject_name) or subject_name
                time_str = lesson.get('hours', 'Неизвестное время')
                lesson_status = lesson.get('status', 'Неизвестно')
                attendance = lesson_logs.get(lesson_id, 'Присутствовал')
                for t in day.get('teachers', []):
                    teacher_id = str(t['person']['id'])
                    if teacher_id not in self._teacher_cache:
                        self._teacher_cache[teacher_id] = {
                            'shortName': t['person']['shortName'],
                            'fullName': t['person'].get('fullName', ''),
                            'subjects': 'Неизвестно',
                            'email': '',
                            'position': 'Неизвестно'
                        }
                homework_text = []
                homework_files = []
                is_important = False
                sent_dates = []
                for work_id in lesson.get('works', []):
                    work_id_str = str(work_id)
                    hw = homeworks.get(work_id_str)
                    if not hw or hw.get('type') != 'Homework':
                        continue
                    text = (hw.get('text') or '').strip()
                    if text and text.lower() not in ['нет', 'нет задания', '-', '.']:
                        homework_text.append(text)
                    for file_id in hw.get('files', []):
                        file = files.get(str(file_id))
                        if file:
                            homework_files.append(f"{file.get('name', 'Файл')} ({file.get('downloadUrl', '')})")
                    is_important = is_important or hw.get('isImportant', False)
                    sent_date = hw.get('sentDate')
                    if sent_date:
                        sent_dates.append(sent_date)
                if not homework_text and not homework_files:
                    homework_text = ['Нет задания']
                homework = '\n'.join(homework_text)
                homework_files = list(set(homework_files))
                sent_date = max(sent_dates, default=None) if sent_dates else None
                mark_details = []
                for work_id in lesson.get('works', []):
                    work_id_str = str(work_id)
                    if work_id_str in marks:
                        mark = marks[work_id_str]
                        work = works.get(work_id_str, {})
                        work_type_id = str(work.get('workType', '0'))
                        mark_details.append({
                            'value': mark.get('value', ''),
                            'work_type': work_types.get(work_type_id, 'Неизвестно'),
                            'mood': mark.get('mood', 'Нет'),
                            'lesson_title': lesson_title
                        })
                formatted_schedule.append({
                    'time': time_str,
                    'subject': subject_name,
                    'homework': homework,
                    'files': homework_files,
                    'title': lesson_title,
                    'teacher': teacher_name,
                    'mark_details': mark_details,
                    'classroom': classroom,
                    'lesson_id': lesson_id,
                    'works': lesson.get('works', []),
                    'lesson_number': lesson_number,
                    'lesson_status': lesson_status,
                    'attendance': attendance,
                    'is_important': is_important,
                    'sent_date': sent_date
                })
        formatted_schedule = sorted(formatted_schedule, key=lambda x: x['lesson_number'])
        self._schedule_cache[date_str] = formatted_schedule
        self._log(f"Итоговое расписание за {date_str}: {len(formatted_schedule)} уроков")
        return formatted_schedule

    def get_formatted_schedule(self, start_date: datetime, end_date: Optional[datetime] = None) -> Dict[str, List[Dict[str, any]]] | List[Dict[str, any]]:
        """
        Получает расписание уроков за одну дату или диапазон дат.

        **Назначение**:
        Предоставляет расписание уроков, вызывая _get_formatted_schedule_day для одной или
        нескольких дат, в зависимости от входных параметров.

        **Входные параметры**:
        - start_date (datetime): Начальная дата для расписания.
        - end_date (datetime, необязательный): Конечная дата. Если None, возвращается
                                              расписание только за start_date. По умолчанию None.

        **Выходные данные**:
        - Dict[str, List[Dict[str, any]]] | List[Dict[str, any]]:
            - Если end_date указан, возвращает словарь, где ключи — строки дат (YYYY-MM-DD),
              а значения — списки уроков (как в _get_formatted_schedule_day).
            - Если end_date не указан, возвращает список уроков за start_date.

        **Алгоритм работы**:
        1. Если end_date не указан, вызывает _get_formatted_schedule_day для start_date.
        2. Если end_date указан, проверяет, что end_date >= start_date.
        3. Для каждой даты в диапазоне вызывает _get_formatted_schedule_day и сохраняет
           результат в словарь.
        4. Возвращает результат.

        **Исключения**:
        - ValueError: Если end_date раньше start_date.

        **Примечания**:
        - Делегирует основную работу методу _get_formatted_schedule_day.
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

    def get_last_marks(self, count: int = 5, subject_id: Optional[int] = None) -> List[Dict[str, any]]:
        """
        Получает последние оценки ученика с возможной фильтрацией по предмету.

        **Назначение**:
        Извлекает заданное количество последних оценок, включая информацию о предмете,
        типе работы, теме урока и распределении оценок в классе.

        **Входные параметры**:
        - count (int, необязательный): Максимальное количество оценок для возврата.
                                      Должно быть положительным. По умолчанию 5.
        - subject_id (int, необязательный): ID предмета для фильтрации. Если None,
                                           возвращаются оценки по всем предметам. По умолчанию None.

        **Выходные данные**:
        - List[Dict[str, any]]: Список словарей, каждый из которых содержит:
            - subject (str): Название предмета.
            - work_type (str): Тип работы (например, "Контрольная работа").
            - lesson_title (str): Тема урока.
            - mark (str): Значение оценки.
            - class_distribution (dict): Распределение оценок в классе {оценка: количество}.
            - date (str): Дата оценки в формате DD.MM.YYYY.

        **Алгоритм работы**:
        1. Проверяет, есть ли subject_id в кэше предметов; если нет, отключает фильтр.
        2. Запрашивает оценки за последние 90 дней через get_person_marks.
        3. Сортирует оценки по дате (от новых к старым) и ограничивает количеством count.
        4. Для каждой оценки:
           - Извлекает lesson_id и work_id.
           - Получает данные урока через _get_lesson_info.
           - Проверяет соответствие subject_id, если указан.
           - Формирует словарь с информацией об оценке.
           - Извлекает тип работы из кэша _work_types_cache.
           - Запрашивает гистограмму оценок через get_marks_histogram.
        5. Логирует процесс обработки.
        6. При ошибке возвращает пустой список.

        **Исключения**:
        - Exception: Ловится для обработки ошибок API.

        **Примечания**:
        - Парсит даты с учётом двух форматов (с и без микросекунд).
        - Использует кэши для оптимизации.
        """
        if subject_id and str(subject_id) not in self._subject_cache:
            self._log(f"Предупреждение: subject_id={subject_id} отсутствует в _subject_cache. Фильтр отключён.")
            subject_id = None
        result = []
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)
            marks = self.api.get_person_marks(self.person_id, self.school_id, start_date, end_date)
            self._log(f"Получено оценок: {len(marks)} за период {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
        except Exception as e:
            self._log(f"Ошибка при получении оценок: {str(e)}")
            return result
        def parse_mark_date(date_str):
            try:
                return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f')
            except ValueError:
                try:
                    return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
                except ValueError:
                    self._log(f"Некорректный формат даты оценки: {date_str}")
                    return datetime.now()
        marks.sort(key=lambda x: parse_mark_date(x.get('date', '1970-01-01')), reverse=True)
        marks = marks[:count]
        for mark in marks:
            lesson_id = str(mark.get('lesson_str', '0'))
            work_id = str(mark.get('work_str', '0'))
            mark_date = parse_mark_date(mark.get('date', '1970-01-01')).date()
            lesson_data = self._get_lesson_info(lesson_id)
            subject_id_from_mark = str(lesson_data.get('subject', {}).get('id')) if lesson_data.get('subject') else None
            if subject_id and subject_id_from_mark and str(subject_id) != subject_id_from_mark:
                self._log(f"Пропущена оценка для урока {lesson_id}: subject_id={subject_id_from_mark} не совпадает с {subject_id}")
                continue
            mark_info = {
                'subject': self._subject_cache.get(subject_id_from_mark, 'Неизвестный предмет') if subject_id_from_mark else 'Неизвестный предмет',
                'work_type': 'Неизвестный тип',
                'lesson_title': 'Неизвестная тема',
                'mark': mark.get('value', 'Нет оценки'),
                'class_distribution': {},
                'date': mark_date.strftime('%d.%m.%Y')
            }
            self._log(f"Обрабатываю оценку: lesson_id={lesson_id}, subject_id={subject_id_from_mark}, mark={mark_info['mark']}")
            if lesson_data.get('subject'):
                mark_info['lesson_title'] = lesson_data.get('title', 'Неизвестная тема') or 'Неизвестная тема'
                works = lesson_data.get('works', [])
                for work in works:
                    if str(work.get('id')) == work_id:
                        work_type_id = str(work.get('workType', '0'))
                        mark_info['work_type'] = self._work_types_cache.get(work_type_id, 'Неизвестный тип')
                        self._log(f"Работа {work_id}: workType={work_type_id}, work_type={mark_info['work_type']}")
                        break
                else:
                    self._log(f"Работа {work_id} не найдена в lesson_data['works'] для урока {lesson_id}")
            try:
                if work_id != '0':
                    histogram = self.api.get_marks_histogram(int(work_id))
                    mark_distribution = {}
                    for mark_number in histogram.get('markNumbers', []):
                        for mark in mark_number.get('marks', []):
                            value = str(mark.get('value'))
                            count = mark.get('count', 0)
                            mark_distribution[value] = mark_distribution.get(value, 0) + count
                    mark_info['class_distribution'] = mark_distribution
                    self._log(f"Распределение оценок для работы {work_id}: {mark_info['class_distribution']}")
            except Exception as e:
                self._log(f"Ошибка при получении гистограммы для работы {work_id}: {str(e)}")
            result.append(mark_info)
        return result

    def get_formatted_marks(self, start_date: datetime, end_date: Optional[datetime] = None) -> Dict[str, List[Dict[str, str]]]:
        """
        Получает оценки за период, сгруппированные по предметам, с учётом даты урока.

        **Назначение**:
        Извлекает оценки за указанный период, группирует их по предметам и форматирует
        с информацией о дате урока, типе работы и настроении.

        **Входные параметры**:
        - start_date (datetime): Начальная дата периода.
        - end_date (datetime, необязательный): Конечная дата. Если None, используется start_date.
                                              По умолчанию None.

        **Выходные данные**:
        - Dict[str, List[Dict[str, str]]]: Словарь, где:
            - Ключи: названия предметов (str).
            - Значения: списки словарей с ключами:
                - lesson_date (str): Дата урока (DD.MM.YYYY).
                - mark_date (str): Дата выставления оценки (DD.MM.YYYY).
                - value (str): Значение оценки.
                - work_type (str): Тип работы.
                - mood (str): Настроение оценки.
                - lesson_title (str): Тема урока.

        **Алгоритм работы**:
        1. Если end_date не указан, устанавливает end_date = start_date.
        2. Запрашивает расписание за период.
        3. Собирает данные о предметах, уроках и оценках.
        4. Фильтрует оценки по предметам и датам.
        5. Форматирует оценки, группируя по предметам.
        6. Сортирует оценки по дате внутри каждого предмета.
        7. При ошибке возвращает пустой словарь.

        **Исключения**:
        - Exception: Ловится для обработки ошибок API.

        **Примечания**:
        - Проверяет, что даты уроков находятся в заданном диапазоне.
        """
        if end_date is None:
            end_date = start_date
        try:
            schedule = self.api.get(
                f"persons/{self.person_id}/groups/{self.group_id}/schedules",
                params={
                    "startDate": start_date.strftime("%Y-%m-%dT00:00:00"),
                    "endDate": end_date.strftime("%Y-%m-%dT23:59:59")
                }
            )
            self._log(f"Получено дней расписания: {len(schedule.get('days', []))}")
        except Exception as e:
            self._log(f"Ошибка при получении расписания: {str(e)}")
            return {}
        if not schedule.get('days'):
            self._log("Нет данных расписания за указанный период")
            return {}
        allowed_subject_ids = set()
        work_types = {}
        lessons = {}
        marks = []
        for day in schedule.get('days', []):
            day_date = datetime.strptime(day.get('date', '1970-01-01T00:00:00'), '%Y-%m-%dT%H:%M:%S').date()
            if start_date.date() <= day_date <= end_date.date():
                work_types.update({str(wt['id']): wt['name'] for wt in day.get('workTypes', [])})
                for lesson in day.get('lessons', []):
                    lessons[str(lesson['id'])] = lesson
                    subject_id = str(lesson.get('subjectId', '0'))
                    allowed_subject_ids.add(subject_id)
                    if subject_id not in self._subject_cache:
                        self._subject_cache[subject_id] = lesson.get('subjectName', 'Неизвестный предмет')
                        self._log(f"Добавлен предмет в _subject_cache: {subject_id} -> {self._subject_cache[subject_id]}")
                for mark in day.get('marks', []):
                    if str(mark['person']) == self.person_id:
                        marks.append(mark)
        formatted_marks = defaultdict(list)
        for mark in marks:
            lesson_id = str(mark.get('lesson_str', '0'))
            lesson_data = lessons.get(lesson_id, {})
            subject_id = str(lesson_data.get('subjectId', '0')) if lesson_data.get('subjectId') else None
            if not subject_id or subject_id not in allowed_subject_ids or subject_id not in self._subject_cache:
                self._log(f"Пропущена оценка для урока {lesson_id}: subject_id={subject_id} отсутствует")
                continue
            subject_name = self._subject_cache.get(subject_id, 'Неизвестный предмет')
            lesson_date_str = lesson_data.get('date', day.get('date', '1970-01-01T00:00:00'))
            try:
                lesson_date = datetime.strptime(lesson_date_str, '%Y-%m-%dT%H:%M:%S').date()
            except ValueError:
                self._log(f"Некорректная дата урока {lesson_id}: {lesson_date_str}")
                continue
            if lesson_date < start_date.date() or lesson_date > end_date.date():
                self._log(f"Пропущена оценка для урока {lesson_id}: дата {lesson_date} вне диапазона")
                continue
            mark_date = datetime.strptime(mark.get('date', '1970-01-01T00:00:00.000000'), '%Y-%m-%dT%H:%M:%S.%f').date()
            work_type_id = str(mark.get('workType', '0'))
            formatted_marks[subject_name].append({
                'lesson_date': lesson_date.strftime('%d.%m.%Y'),
                'mark_date': mark_date.strftime('%d.%m.%Y'),
                'value': str(mark.get('value', 'Нет оценки')),
                'work_type': work_types.get(work_type_id, 'Неизвестно'),
                'mood': mark.get('mood', 'Нет'),
                'lesson_title': lesson_data.get('title', 'Неизвестно')
            })
        for subject in formatted_marks:
            formatted_marks[subject] = sorted(formatted_marks[subject], key=lambda x: x['mark_date'])
        return dict(formatted_marks)

    def get_group_teachers(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, str]]:
        """
        Получает список учителей группы за указанный период.

        **Назначение**:
        Извлекает информацию об учителях, преподающих в группе, на основе уроков за период.

        **Входные параметры**:
        - start_date (datetime, необязательный): Начальная дата. Если None, используется
                                                текущая дата минус 7 дней. По умолчанию None.
        - end_date (datetime, необязательный): Конечная дата. Если None, используется
                                              текущая дата плюс 30 дней. По умолчанию None.

        **Выходные данные**:
        - List[Dict[str, str]]: Список словарей, каждый из которых содержит:
            - id (str): ID учителя.
            - fullName (str): Полное имя.
            - shortName (str): Краткое имя.
            - subjects (str): Предметы.
            - email (str): Электронная почта.
            - position (str): Должность.

        **Алгоритм работы**:
        1. Устанавливает даты по умолчанию, если не указаны.
        2. Проверяет, что end_date >= start_date.
        3. Запрашивает уроки через /persons/{person_id}/school/{school_id}/homeworks.
        4. Собирает уникальные ID учителей.
        5. Формирует список учителей из кэша _teacher_cache.
        6. Сортирует по ID.
        7. При ошибке возвращает пустой список.

        **Исключения**:
        - ValueError: Если end_date раньше start_date.
        - Exception: Ловится для обработки ошибок API.

        **Примечания**:
        - Использует кэш для минимизации запросов.
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now() + timedelta(days=30)
        if end_date < start_date:
            raise ValueError("end_date не может быть раньше start_date")
        try:
            homeworks = self.api.get(
                f"persons/{self.person_id}/school/{self.school_id}/homeworks",
                params={
                    "startDate": start_date.strftime('%Y-%m-%d'),
                    "endDate": end_date.strftime('%Y-%m-%d')
                }
            )
            lessons = homeworks.get('lessons', [])
        except Exception as e:
            self._log(f"Ошибка при получении уроков: {str(e)}")
            return []
        teacher_ids = set()
        for lesson in lessons:
            lesson_date = datetime.strptime(lesson.get('date', '1970-01-01'), '%Y-%m-%dT%H:%M:%S').date()
            if start_date.date() <= lesson_date <= end_date.date():
                for teacher_id in lesson.get('teachers', []):
                    teacher_ids.add(str(teacher_id))
        result = []
        for teacher_id in sorted(teacher_ids):
            teacher_info = self._teacher_cache.get(teacher_id, {
                'shortName': 'Неизвестно',
                'fullName': 'Неизвестно',
                'subjects': 'Неизвестно',
                'email': '',
                'position': 'Неизвестно'
            })
            result.append({
                'id': teacher_id,
                'fullName': teacher_info['fullName'],
                'shortName': teacher_info['shortName'],
                'subjects': teacher_info['subjects'],
                'email': teacher_info['email'],
                'position': teacher_info['position']
            })
        return result

    def _get_quarter_period_id(self, study_year: int, quarter: int) -> Optional[Tuple[str, datetime, datetime]]:
        """
        Получает ID периода и даты для указанной четверти.

        **Назначение**:
        Определяет идентификатор и временной диапазон семестра, соответствующего четверти.

        **Входные параметры**:
        - study_year (int): Учебный год (например, 2025 для 2024-2025).
        - quarter (int): Номер четверти (1-4).

        **Выходные данные**:
        - Optional[Tuple[str, datetime, datetime]]: Кортеж из:
            - ID периода (str).
            - Начальная дата (datetime).
            - Конечная дата (datetime).
            Если период не найден, возвращается None.

        **Алгоритм работы**:
        1. Запрашивает периоды через /edu-groups/{group_id}/reporting-periods.
        2. Сопоставляет четверть с номером семестра (1,2 -> 0; 3,4 -> 1).
        3. Ищет подходящий семестр по типу, номеру и году.
        4. Парсит даты начала и конца периода.
        5. Возвращает кортеж или None при ошибке.

        **Исключения**:
        - Exception: Ловится для обработки ошибок API.

        **Примечания**:
        - Поддерживает два формата дат (с и без микросекунд).
        """
        try:
            periods = self.api.get(f"edu-groups/{self.group_id}/reporting-periods")
            self._log(f"Сырой ответ reporting-periods:\n{json.dumps(periods, ensure_ascii=False, indent=2)}")
        except Exception as e:
            self._log(f"Ошибка при получении периодов: {str(e)}")
            return None
        quarter_to_semester = {1: 0, 2: 0, 3: 1, 4: 1}
        target_semester = quarter_to_semester.get(quarter)
        if target_semester is None:
            self._log(f"Некорректный номер четверти: {quarter}")
            return None
        for period in periods:
            period_type = period.get('type', '')
            period_number = period.get('number', -1)
            period_year = period.get('year', 0)
            start_date_str = period.get('start', '')
            finish_date_str = period.get('finish', '')
            self._log(f"Проверяю период: type={period_type}, number={period_number}, start={start_date_str}, finish={finish_date_str}")
            if period_type != 'Semester' or period_number != target_semester or period_year != study_year - 1:
                continue
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M:%S')
                finish_date = datetime.strptime(finish_date_str, '%Y-%m-%dT%H:%M:%S')
            except ValueError:
                try:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M:%S.%f')
                    finish_date = datetime.strptime(finish_date_str, '%Y-%m-%dT%H:%M:%S.%f')
                except ValueError:
                    self._log(f"Некорректный формат дат: start={start_date_str}, finish={finish_date_str}")
                    continue
            self._log(f"Найден семестр для четверти {quarter}: ID={period.get('id')}")
            return str(period.get('id')), start_date, finish_date
        self._log(f"Период для четверти {quarter} не найден")
        return None

    def get_formatted_final_marks(self, study_year: int, quarter: int) -> List[Dict[str, any]]:
        """
        Получает итоговые оценки за четверть для предметов с уроками в периоде.

        **Назначение**:
        Извлекает оценки по предметам за четверть, включая средний балл.

        **Входные параметры**:
        - study_year (int): Учебный год.
        - quarter (int): Номер четверти (1-4).

        **Выходные данные**:
        - List[Dict[str, any]]: Список словарей, каждый из которых содержит:
            - название предмета (str): Название предмета.
            - оценки (list): Список оценок.
            - средЛАТЕКС (str): Средний балл (str): Средний балл или сообщение о статусе.

        **Алгоритм работы**:
        1. Проверяет валидность номера четверти.
        2. Получает ID периода и даты через _get_quarter_period_id.
        3. Запрашивает расписание за период.
        4. Собирает активные предметы.
        5. Для каждого предмета запрашивает оценки и вычисляет средний балл.
        6. Сортирует результат по названию предмета.

        **Исключения**:
        - ValueError: Если номер четверти некорректен.
        - Exception: Ловится для обработки ошибок API.

        **Примечания**:
        - Учитывает только предметы с уроками в периоде.
        """
        if quarter not in [1, 2, 3, 4]:
            raise ValueError("Номер четверти должен быть от 1 до 4")
        period_data = self._get_quarter_period_id(study_year, quarter)
        if not period_data:
            return []
        period_id, start_date, finish_date = period_data
        try:
            schedule = self.api.get(
                f"persons/{self.person_id}/groups/{self.group_id}/schedules",
                params={
                    "startDate": start_date.strftime("%Y-%m-%dT00:00:00"),
                    "endDate": finish_date.strftime("%Y-%m-%dT23:59:59")
                }
            )
            self._log(f"Получено дней расписания: {len(schedule.get('days', []))}")
        except Exception as e:
            self._log(f"Ошибка при получении расписания: {str(e)}")
            schedule = {'days': []}
        active_subject_ids = set()
        for day in schedule.get('days', []):
            day_date = datetime.strptime(day.get('date', '1970-01-01T00:00:00'), '%Y-%m-%dT%H:%M:%S').date()
            if start_date.date() <= day_date <= finish_date.date():
                for lesson in day.get('lessons', []):
                    subject_id = str(lesson.get('subjectId', '0'))
                    active_subject_ids.add(subject_id)
                    for subject in day.get('subjects', []):
                        subj_id = str(subject.get('id'))
                        subj_name = subject.get('name', 'Неизвестный предмет').strip()
                        if subj_id and subj_name and subj_id not in self._subject_cache:
                            self._subject_cache[subj_id] = subj_name
                            self._log(f"Добавлен предмет в _subject_cache: {subj_id} -> {subj_name}")
        if not active_subject_ids:
            self._log("Расписание пустое, использую все предметы из _subject_cache")
            active_subject_ids = set(self._subject_cache.keys())
        formatted_marks = []
        for subject_id in active_subject_ids:
            if subject_id not in self._subject_cache:
                self._log(f"Пропущен предмет {subject_id}: отсутствует в _subject_cache")
                continue
            try:
                marks = self.api.get_person_subject_marks(self.person_id, int(subject_id), start_date, finish_date)
            except Exception as e:
                self._log(f"Ошибка при получении оценок для предмета {subject_id}: {str(e)}")
                marks = []
            grades = [mark['value'] for mark in marks if mark.get('value', '').replace('.', '', 1).isdigit()]
            if grades:
                try:
                    average = statistics.mean([float(g) for g in grades])
                    average_str = str(round(average, 1))
                except statistics.StatisticsError:
                    average_str = "Нет данных"
            else:
                average_str = "Нет оценок"
            formatted_marks.append({
                'название предмета': self._subject_cache.get(subject_id, 'Неизвестный предмет'),
                'оценки': grades,
                'средний балл': average_str
            })
        return sorted(formatted_marks, key=lambda x: x['название предмета'])

    def get_class_ranking(self, study_year: int, quarter: int) -> List[Dict]:
        """
        Формирует рейтинг учеников класса по средней оценке за четверть.

        **Назначение**:
        Создаёт упорядоченный список учеников на основе их среднего балла за четверть.

        **Входные параметры**:
        - study_year (int): Учебный год.
        - quarter (int): Номер четверти (1-4).

        **Выходные данные**:
        - List[Dict]: Список словарей, каждый из которых содержит:
            - name (str): Имя ученика.
            - avg_grade (float): Средний балл, округлённый до 2 знаков.
            - marks_count (int): Количество оценок.

        **Алгоритм работы**:
        1. Проверяет валидность номера четверти.
        2. Получает период через _get_quarter_period_id.
        3. Для каждого ученика:
           - Собирает оценки по всем предметам.
           - Вычисляет средний балл.
           - Формирует запись рейтинга.
        4. Сортирует по убыванию среднего балла.

        **Исключения**:
        - ValueError: Если номер четверти некорректен.
        - Exception: Ловится для обработки ошибок API.

        **Примечания**:
        - Учитывает только числовые оценки.
        """
        if quarter not in [1, 2, 3, 4]:
            raise ValueError("Номер четверти должен быть от 1 до 4")
        period_data = self._get_quarter_period_id(study_year, quarter)
        if not period_data:
            return []
        period_id, start_date, finish_date = period_data
        ranking = []
        for student_id, student_name in self._student_cache.items():
            student_grades = []
            for subject_id in self._subject_cache:
                try:
                    marks = self.api.get_person_subject_marks(student_id, int(subject_id), start_date, finish_date)
                    grades = [float(mark['value']) for mark in marks if mark.get('value', '').replace('.', '', 1).isdigit()]
                    student_grades.extend(grades)
                except Exception as e:
                    self._log(f"Ошибка при получении оценок для ученика {student_id}, предмет {subject_id}: {str(e)}")
            avg_grade = statistics.mean(student_grades) if student_grades else 0
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

        **Назначение**:
        Формирует распределение оценок по предмету для всей группы.

        **Входные параметры**:
        - study_year (int): Учебный год.
        - quarter (int): Номер четверти (1-4).
        - subject_id (int): ID предмета.

        **Выходные данные**:
        - Dict[str, int]: Словарь, где ключи — значения оценок, а значения — их количество.

        **Алгоритм работы**:
        1. Проверяет валидность номера четверти.
        2. Получает период через _get_quarter_period_id.
        3. Запрашивает гистограмму через get_subject_marks_histogram.
        4. Суммирует количество оценок для каждого значения.
        5. При ошибке возвращает пустой словарь.

        **Исключения**:
        - ValueError: Если номер четверти некорректен.
        - Exception: Ловится для обработки ошибок API.

        **Примечания**:
        - Формат ответа API: словарь с полем works, содержащим гистограмму.
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
            self._log(f"Ошибка при получении статистики по предмету {subject_id}: {str(e)}")
            return {}

    def get_subject_ranking(self, study_year: int, quarter: int, subject_id: int) -> List[Dict]:
        """
        Формирует рейтинг учеников по предмету за четверть.

        **Назначение**:
        Создаёт упорядоченный список учеников на основе их среднего балла по предмету.

        **Входные параметры**:
        - study_year (int): Учебный год.
        - quarter (int): Номер четверти (1-4).
        - subject_id (int): ID предмета.

        **Выходные данные**:
        - List[Dict]: Список словарей, каждый из которых содержит:
            - name (str): Имя ученика.
            - avg_grade (float): Средний балл, округлённый до 2 знаков.
            - marks_count (int): Количество оценок.

        **Алгоритм работы**:
        1. Проверяет валидность номера четверти и наличие предмета.
        2. Если кэш учеников пуст, загружает данные через /edu-groups/{group_id}.
        3. Для каждого ученика:
           - Запрашивает оценки по предмету.
           - Вычисляет средний балл.
           - Формирует запись рейтинга.
        4. Сортирует по убыванию среднего балла.

        **Исключения**:
        - ValueError: Если номер четверти некорректен.
        - Exception: Ловится для обработки ошибок API.

        **Примечания**:
        - Учитывает только числовые оценки.
        """
        if quarter not in [1, 2, 3, 4]:
            raise ValueError("Номер четверти должен быть от 1 до 4")
        period_data = self._get_quarter_period_id(study_year, quarter)
        if not period_data:
            return []
        period_id, start_date, finish_date = period_data
        if str(subject_id) not in self._subject_cache:
            self._log(f"Предмет {subject_id} отсутствует в _subject_cache")
            return []
        if not self._student_cache:
            self._log("Кэш учеников пуст, загружаю данные")
            try:
                group = self.api.get(f"edu-groups/{self.group_id}")
                for student in group.get('students', []):
                    student_id = str(student.get('id'))
                    student_name = student.get('shortName', 'Неизвестный ученик')
                    self._student_cache[student_id] = student_name
                self._log(f"Загружено учеников: {len(self._student_cache)}")
            except Exception as e:
                self._log(f"Ошибка при загрузке учеников: {str(e)}")
                return []
        ranking = []
        for student_id, student_name in self._student_cache.items():
            try:
                marks = self.api.get_person_subject_marks(student_id, subject_id, start_date, finish_date)
                grades = [float(mark['value']) for mark in marks if mark.get('value', '').replace('.', '', 1).isdigit()]
                avg_grade = statistics.mean(grades) if grades else 0
                ranking.append({
                    'name': student_name,
                    'avg_grade': round(avg_grade, 2),
                    'marks_count': len(grades)
                })
            except Exception as e:
                self._log(f"Ошибка при получении оценок для ученика {student_id}, предмет {subject_id}: {str(e)}")
        ranking.sort(key=lambda x: x['avg_grade'], reverse=True)
        return ranking

    def get_class_stats(self, study_year: int, quarter: int) -> Dict:
        """
        Получает статистику класса за четверть.

        **Назначение**:
        Формирует общую статистику класса, включая общее количество оценок, средний балл
        и распределение оценок.

        **Входные параметры**:
        - study_year (int): Учебный год.
        - quarter (int): Номер четверти (1-4).

        **Выходные данные**:
        - Dict: Словарь, содержащий:
            - total_marks (int): Общее количество оценок.
            - average_class_grade (float): Средний балл класса, округлённый до 2 знаков.
            - grade_distribution (dict): Процентное распределение оценок {оценка: процент}.

        **Алгоритм работы**:
        1. Проверяет валидность номера четверти.
        2. Получает период через _get_quarter_period_id.
        3. Для каждого предмета запрашивает гистограмму оценок.
        4. Суммирует оценки и вычисляет статистику.
        5. При ошибке возвращает пустой словарь.

        **Исключения**:
        - ValueError: Если номер четверти некорректен.
        - Exception: Ловится для обработки ошибок API.

        **Примечания**:
        - Учитывает только числовые оценки.
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
                histogram = self.api.get_subject_marks_histogram(self.group_id, period_id, int(subject_id))
                for work in histogram.get('works', []):
                    for mark_number in work.get('markNumbers', []):
                        for mark in mark_number.get('marks', []):
                            value = str(mark.get('value'))
                            count = mark.get('count', 0)
                            if value.replace('.', '', 1).isdigit():
                                total_grades[value] += count
                                total_marks += count
            except Exception as e:
                self._log(f"Ошибка при получении статистики по предмету {subject_id}: {str(e)}")
        average_class_grade = sum(float(k) * v for k, v in total_grades.items()) / total_marks if total_marks else 0
        grade_distribution = {k: v / total_marks * 100 for k, v in total_grades.items()} if total_marks else {}
        return {
            'total_marks': total_marks,
            'average_class_grade': round(average_class_grade, 2),
            'grade_distribution': grade_distribution
        }

if __name__ == "__main__":
    """
    Точка входа для тестирования класса DnevnikFormatter.

    Инициализирует formatter с токеном, включает отладочный режим и получает последние 5 оценок
    в качестве примера использования.
    """
    token = "token"
    formatter = DnevnikFormatter(token=token, debug_mode=True)
    schedule = formatter.get_last_marks()
    print(schedule)
