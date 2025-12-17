import uuid
import aiofiles
import asyncio
from pydnevnikruapi.aiodnevnik import dnevnik
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import statistics
from collections import defaultdict
import json
import re
from openai import AsyncOpenAI
import os
import logging
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.text import Text
from rich import box
import time

# Ключевая константа: API-ключ для интеграции с DeepSeek через OpenRouter
# Этот ключ используется для отправки запросов к AI для анализа данных
API_KEY = "YOUR_API_KEY"  # Замените на ваш ключ OpenRouter
# Настройка логирования в файл bot.log и консоль
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DnevnikFormatter:
    """
    Асинхронный класс для обработки и форматирования данных из API Дневник.ру.
    Предоставляет методы для получения расписания, оценок, информации об учителях и статистики класса.
    Использует кэширование для оптимизации запросов, обработку ошибок и интеграцию с AI для анализа данных.

    **Назначение**:
    Этот класс предназначен для упрощения работы с API Дневник.ру, предоставляя высокоуровневые методы
    для получения отформатированных данных: расписание уроков, оценки, списки тестов, рейтинги учеников.
    Асинхронная архитектура делает его подходящим для приложений с высокой нагрузкой, таких как Telegram-боты.

    **Основные особенности**:
    - Асинхронные запросы через `pydnevnikruapi.aiodnevnik`.
    - Кэширование данных (уроки, предметы, ученики, учителя) для минимизации запросов к API.
    - Интеграция с AI (DeepSeek через OpenRouter) для анализа расписания, оценок и рейтингов.
    - Гибкая обработка ошибок с логированием для упрощения отладки.
    - Поддержка работы с четвертями, семестрами и учебными годами.
    - Использование семафоров для ограничения параллельных запросов и защиты API от перегрузки.

    **Применение**:
    Используется в Telegram-ботах, школьных порталах или личных ассистентах для предоставления
    расписания, оценок, уведомлений о тестах и аналитики успеваемости.

    **Ограничения**:
    - Требуется действительный токен API Дневник.ру.
    - Зависит от структуры API, которая может измениться.
    - Требуется файл `prompts.json` для AI-анализа.
    - Ограничение на 10 параллельных запросов через семафор.
    """

    def __init__(self, token: str, debug_mode: bool = True, max_concurrent_requests: int = 10):
        """
        Инициализирует экземпляр класса DnevnikFormatter, устанавливая соединение с API Дневник.ру
        и подготавливая кэши для данных.

        **Параметры**:
        - token (str): Токен авторизации для доступа к API Дневник.ру. Должен быть действительным.
        - debug_mode (bool): Если True, включает подробное логирование. По умолчанию True.
        - max_concurrent_requests (int): Максимальное количество параллельных запросов к API. По умолчанию 10.

        **Алгоритм работы**:
        1. Сохраняет токен, режим отладки и максимальное количество параллельных запросов.
        2. Инициализирует переменные для идентификаторов (person_id, school_id, group_id).
        3. Создает кэши для данных: уроки, предметы, ученики, учителя, типы работ, расписание.
        4. Определяет словарь `title_to_weight` с весами типов работ для анализа важности тестов.
        5. Инициализирует семафор для ограничения параллельных запросов.

        **Возвращаемые значения**:
        - None: Инициализирует объект, не возвращает данных.

        **Исключения**:
        - Не выбрасывает исключений напрямую, но метод `initialize` может вызвать ошибки,
          если токен недействителен или API недоступен.

        **Пример использования**:
        ```python
        formatter = DnevnikFormatter(token="your_token", debug_mode=True)
        await formatter.initialize()
        ```
        """
        self.token = token
        self.debug_mode = debug_mode
        self.api = None
        self.person_id = None
        self.school_id = None
        self.group_id = None
        self._lesson_cache = {}
        self._subject_cache = {}
        self._student_cache = {}
        self._teacher_cache = {}
        self._work_types_cache = {}
        self._schedule_cache = {}
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.title_to_weight = {
            'Административная контрольная работа': 10,
            'Арифметический диктант': 4,
            'Входная контрольная работа': 5,
            'Входной контрольный диктант': 5,
            'Государственная итоговая аттестация': 10,
            'Диагностическая работа': 4,
            'Диктант': 8,
            'Зачет': 8,
            'Интегральный зачет': 3,
            'Итоговая контрольная работа': 9,
            'Контрольная': 9,
            'Контрольное списывание': 7,
            'Контрольный диктант': 9,
            'Лабораторная работа': 7,
            'Математический диктант': 4,
            'Практическая работа': 8,
            'Проверочная работа': 8,
            'Работа с контурными картами': 5,
            'Словарный диктант': 4,
            'Стартовая контрольная работа': 3,
            'Тест': 5,
            'Техника чтения': 5,
            'Устный счет': 4,
            'Экзамен': 10
        }

    async def initialize(self):
        """
        Асинхронно инициализирует клиент API и загружает начальные данные.

        **Назначение**:
        Завершает настройку экземпляра, устанавливая соединение с API и заполняя кэши
        предметов, учеников, учителей и типов работ.

        **Алгоритм работы**:
        1. Создает асинхронный клиент API с токеном.
        2. Запрашивает контекст пользователя через `/v2/users/me/context`.
        3. Извлекает person_id, school_id, group_id.
        4. Проверяет корректность идентификаторов, иначе выбрасывает исключение.
        5. Параллельно загружает данные через `asyncio.gather`.
        6. Логирует успех или ошибки.

        **Возвращаемые значения**:
        - None: Инициализирует объект.

        **Исключения**:
        - ValueError: Если идентификаторы отсутствуют.
        - Exception: Ошибки API (логируются и выбрасываются).
        """
        start_time = time.time()
        try:
            async with dnevnik.AsyncDiaryAPI(token=self.token) as dn:
                self.api = dn
                self.context = await self.api.get("users/me/context")
                logger.info(f"Ответ от /v2/users/me/context:\n{json.dumps(self.context, ensure_ascii=False, indent=2)}")

                self.person_id = str(self.context.get('personId', '0'))
                self.school_id = str(self.context.get('schools', [{}])[0].get('id', '0'))
                self.group_id = str(self.context.get('eduGroups', [{}])[0].get('id_str', '0'))

                if not self.person_id or not self.school_id or not self.group_id:
                    raise ValueError("Не удалось получить person_id, school_id или group_id")

                logger.info(f"Инициализация: person_id={self.person_id}, school_id={self.school_id}, group_id={self.group_id}")

                await asyncio.gather(
                    self._load_subjects(),
                    self._load_students(),
                    self._load_teachers(),
                    self._load_work_types(),
                    return_exceptions=True
                )
        except Exception as e:
            logger.error(f"Ошибка при инициализации: {str(e)}")
            raise
        finally:
            elapsed_time = time.time() - start_time
            logger.info(f"Инициализация завершена за {elapsed_time:.2f} секунд")

    async def make_ai_request(self, prompt: str) -> str:
        """
        Выполняет асинхронный запрос к API DeepSeek через OpenRouter.

        **Назначение**:
        Отправляет промпт к AI для анализа данных и возвращает человекочитаемый результат.

        **Параметры**:
        - prompt (str): Текст запроса для AI.

        **Алгоритм работы**:
        1. Создает клиент AsyncOpenAI с настройками OpenRouter.
        2. Отправляет запрос к модели deepseek/deepseek-chat.
        3. Извлекает и возвращает ответ или логирует ошибку.

        **Возвращаемые значения**:
        - str: Ответ AI или сообщение об ошибке.
        """
        start_time = time.time()
        try:
            async with self.semaphore:
                client = AsyncOpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=API_KEY,
                )
                completion = await client.chat.completions.create(
                    model="deepseek/deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    extra_body={}
                )
                response = completion.choices[0].message.content
                logger.info(f"AI запрос выполнен: {len(response)} символов")
                return response
        except Exception as e:
            logger.error(f"Ошибка AI запроса: {str(e)}")
            return f"Ошибка AI запроса: {str(e)}"
        finally:
            elapsed_time = time.time() - start_time
            logger.info(f"AI запрос завершен за {elapsed_time:.2f} секунд")

    def clear_schedule_cache(self):
        """
        Очищает кэш расписания для обновления данных.

        **Назначение**:
        Сбрасывает кэш расписания, чтобы при следующем запросе данные загружались заново.

        **Алгоритм работы**:
        1. Очищает словарь _schedule_cache.
        2. Логирует действие.

        **Возвращаемые значения**:
        - None: Модифицирует внутреннее состояние.
        """
        self._schedule_cache = {}
        logger.info("Кэш расписания очищен")

    async def _load_work_types(self):
        """
        Загружает и кэширует типы работ школы.

        **Назначение**:
        Получает типы работ (например, контрольная, домашняя) и сохраняет в кэш.

        **Алгоритм работы**:
        1. Очищает кэш _work_types_cache.
        2. Запрашивает типы работ через `/work-types/{school_id}`.
        3. Сохраняет ID и название типов в кэш.
        4. При ошибке использует запасной набор типов.

        **Возвращаемые значения**:
        - None: Заполняет кэш.
        """
        start_time = time.time()
        self._work_types_cache = {}
        try:
            if not self.school_id or self.school_id == '0':
                raise ValueError("school_id не определён")
            async with self.semaphore:
                async with dnevnik.AsyncDiaryAPI(token=self.token) as dn:
                    work_types = await dn.get(f"work-types/{self.school_id}")
                    for wt in work_types:
                        work_type_id = str(wt.get('id', '0'))
                        work_type_name = wt.get('title', 'Неизвестный тип').strip()
                        if work_type_id and work_type_name:
                            self._work_types_cache[work_type_id] = work_type_name
                    logger.info(f"Загружено типов работ: {len(self._work_types_cache)}")
        except Exception as e:
            logger.error(f"Ошибка загрузки типов работ: {str(e)}")
            self._work_types_cache = {
                'CommonWork': 'Работа на уроке',
                'DefaultNewLessonWork': 'Работа на уроке',
                'LessonTestWork': 'Контрольная работа',
                'Homework': 'Домашняя работа',
                'CreativeWork': 'Творческая работа'
            }
            logger.info(f"Использован запасной набор типов работ: {len(self._work_types_cache)}")
        finally:
            elapsed_time = time.time() - start_time
            logger.info(f"Загрузка типов работ завершена за {elapsed_time:.2f} секунд")

    async def _read_prompts(self) -> Dict[str, str]:
        """
        Читает промпты для AI-анализа из prompts.json.

        **Назначение**:
        Загружает шаблоны запросов для AI из файла prompts.json.

        **Алгоритм работы**:
        1. Асинхронно читает файл prompts.json.
        2. Парсит JSON и извлекает промпты для 'weeks', 'marks', 'ranking'.
        3. Логирует успех или ошибки.

        **Возвращаемые значения**:
        - Dict[str, str]: Словарь промптов.
        """
        start_time = time.time()
        try:
            async with aiofiles.open("prompts.json", 'r', encoding='utf-8') as f:
                content = await f.read()
                prompts_data = json.loads(content)
            prompts = {key: data.get("prompt", "") for key, data in prompts_data.items()}
            logger.info(f"Промпты загружены: {list(prompts.keys())}")
            return prompts
        except Exception as e:
            logger.error(f"Ошибка чтения prompts.json: {str(e)}")
            raise
        finally:
            elapsed_time = time.time() - start_time
            logger.info(f"Чтение промптов завершено за {elapsed_time:.2f} секунд")

    async def _load_subjects(self):
        """
        Загружает и кэширует предметы учебной группы.

        **Назначение**:
        Получает список предметов группы и сохраняет в кэш.

        **Алгоритм работы**:
        1. Очищает кэш _subject_cache.
        2. Пытается загрузить предметы через `/edu-groups/{group_id}/subjects`.
        3. При ошибке загружает предметы из расписания за год или 30 дней.
        4. Логирует успех или ошибки.

        **Возвращаемые значения**:
        - None: Заполняет кэш.
        """
        start_time = time.time()
        self._subject_cache = {}
        try:
            async with self.semaphore:
                async with dnevnik.AsyncDiaryAPI(token=self.token) as dn:
                    subjects = await dn.get(f"edu-groups/{self.group_id}/subjects")
                    for subject in subjects:
                        subject_id = str(subject.get('id'))
                        subject_name = subject.get('name', 'Неизвестный предмет').strip()
                        if subject_id and subject_name:
                            self._subject_cache[subject_id] = subject_name
                    logger.info(f"Загружено предметов: {len(self._subject_cache)}")
        except Exception as e:
            logger.error(f"Ошибка загрузки предметов: {str(e)}")
            try:
                now = datetime.now()
                start_date = now.replace(month=9, day=1)
                if start_date > now:
                    start_date = start_date.replace(year=start_date.year - 1)
                end_date = start_date.replace(year=start_date.year + 1, month=8, day=31)
                async with self.semaphore:
                    async with dnevnik.AsyncDiaryAPI(token=self.token) as dn:
                        schedule = await dn.get(
                            f"persons/{self.person_id}/groups/{self.group_id}/schedules",
                            params={
                                "startDate": start_date.strftime("%Y-%m-%dT00:00:00"),
                                "endDate": end_date.strftime("%Y-%m-%dT23:59:59")
                            }
                        )
                        for day in schedule.get('days', []):
                            for subject in day.get('subjects', []):
                                subject_id = str(subject.get('id'))
                                subject_name = subject.get('name', 'Неизвестный предмет').strip()
                                if subject_id and subject_name:
                                    self._subject_cache[subject_id] = subject_name
                        logger.info(f"Загружено предметов из расписания: {len(self._subject_cache)}")
            except Exception as e:
                logger.error(f"Ошибка загрузки предметов из расписания: {str(e)}")
        finally:
            elapsed_time = time.time() - start_time
            logger.info(f"Загрузка предметов завершена за {elapsed_time:.2f} секунд")

    async def _load_students(self):
        """
        Загружает и кэширует список учеников группы.

        **Назначение**:
        Получает данные об учениках и сохраняет в кэш.

        **Алгоритм работы**:
        1. Запрашивает учеников через get_groups_pupils.
        2. Сохраняет ID и имена в _student_cache.
        3. Логирует успех или ошибки.

        **Возвращаемые значения**:
        - None: Заполняет кэш.
        """
        start_time = time.time()
        try:
            async with self.semaphore:
                async with dnevnik.AsyncDiaryAPI(token=self.token) as dn:
                    students = await dn.get_groups_pupils(self.group_id)
                    for student in students:
                        student_id = str(student.get('id'))
                        student_name = student.get('shortName', 'Неизвестный')
                        if student_id and student_name:
                            self._student_cache[student_id] = student_name
                    logger.info(f"Загружено учеников: {len(self._student_cache)}")
        except Exception as e:
            logger.error(f"Ошибка загрузки учеников: {str(e)}")
            self._student_cache = {}
        finally:
            elapsed_time = time.time() - start_time
            logger.info(f"Загрузка учеников завершена за {elapsed_time:.2f} секунд")

    async def _load_teachers(self):
        """
        Загружает и кэширует список учителей школы.

        **Назначение**:
        Получает данные об учителях и сохраняет в кэш.

        **Алгоритм работы**:
        1. Запрашивает учителей через `/schools/{school_id}/teachers`.
        2. Сохраняет ID, имена, предметы, email и должности в _teacher_cache.
        3. Логирует успех или ошибки.

        **Возвращаемые значения**:
        - Dict: Словарь с данными учителей.
        """
        start_time = time.time()
        try:
            async with self.semaphore:
                async with dnevnik.AsyncDiaryAPI(token=self.token) as dn:
                    teachers = await dn.get(f"schools/{self.school_id}/teachers")
                    teacher_dict = {}
                    for teacher in teachers:
                        teacher_id = str(teacher.get('Id'))
                        if not teacher_id:
                            continue
                        teacher_name = teacher.get('ShortName', 'Неизвестно')
                        full_name = f"{teacher.get('FirstName', '')} {teacher.get('MiddleName', '')} {teacher.get('LastName', '')}".strip()
                        teacher_dict[teacher_id] = {
                            'shortName': teacher_name,
                            'fullName': full_name,
                            'subjects': teacher.get('Subjects', 'Неизвестно'),
                            'email': teacher.get('Email', ''),
                            'position': teacher.get('NameTeacherPosition', 'Неизвестно')
                        }
                    self._teacher_cache = teacher_dict
                    logger.info(f"Загружено учителей: {len(self._teacher_cache)}")
                    return teacher_dict
        except Exception as e:
            logger.error(f"Ошибка загрузки учителей: {str(e)}")
            return {}
        finally:
            elapsed_time = time.time() - start_time
            logger.info(f"Загрузка учителей завершена за {elapsed_time:.2f} секунд")

    async def _get_lesson_info(self, lesson_id: str, force_refresh: bool = False) -> Optional[Dict]:
        """
        Получает информацию об уроке по ID.

        **Назначение**:
        Извлекает данные об уроке, используя кэш или API.

        **Параметры**:
        - lesson_id (str): ID урока.
        - force_refresh (bool): Игнорировать кэш и загружать заново.

        **Алгоритм работы**:
        1. Проверяет корректность lesson_id.
        2. Возвращает данные из кэша, если доступны и не требуется обновление.
        3. Запрашивает данные через get_lesson_info.
        4. Кэширует результат и логирует.

        **Возвращаемые значения**:
        - Optional[Dict]: Данные урока или пустой словарь.
        """
        start_time = time.time()
        if not lesson_id or lesson_id == '0':
            logger.warning(f"Некорректный lesson_id: {lesson_id}")
            return {}
        if force_refresh or lesson_id not in self._lesson_cache:
            try:
                async with self.semaphore:
                    async with dnevnik.AsyncDiaryAPI(token=self.token) as dn:
                        lesson_data = await dn.get_lesson_info(int(lesson_id))
                        self._lesson_cache[lesson_id] = lesson_data
                        logger.info(f"Загружен урок {lesson_id}: {lesson_data.get('title', 'Без названия')}")
            except Exception as e:
                logger.error(f"Ошибка загрузки урока {lesson_id}: {str(e)}")
                self._lesson_cache[lesson_id] = {}
        elapsed_time = time.time() - start_time
        logger.info(f"Получение урока {lesson_id} завершено за {elapsed_time:.2f} секунд")
        return self._lesson_cache.get(lesson_id, {})

    async def _get_work_marks_by_id(self, work_id: int) -> List[Dict[str, str]]:
        """
        Получает список учеников и их оценок для указанной работы асинхронно.
        
        Args:
            work_id (int): ID работы.
            
        Returns:
            List[Dict[str, str]]: Список словарей с полями:
                - name (str): Краткое имя ученика.
                - mark (str): Оценка.
                
        Raises:
            ValueError: Если work_id некорректен.
            Exception: При сетевых ошибках (логируется).
        """
        result = []
        try:
            # Проверяем наличие учеников в кэше
            if not self._student_cache:
                logger.info("Student cache is empty, cannot fetch work marks")
                return result

            logger.info(f"Запрос оценок для work_id={work_id}, учеников в кэше: {len(self._student_cache)}")
            async with dnevnik.AsyncDiaryAPI(token=self.token) as dn:
                for student_id, student_name in self._student_cache.items():
                    try:
                        # Пытаемся получить оценки, учитывая возможную корутину
                        marks_response = await dn.get_person_work_marks(person_id=student_id, work_id=work_id)
                        marks_response = await marks_response


                        # Обрабатываем каждую оценку
                        for mark in marks_response:
                            mark_value = mark.get("value", "")
                            if mark_value:
                                result.append({
                                    "name": student_name,
                                    "mark": mark_value
                                })
                    except Exception as e:
                        logger.info(f"Ошибка при запросе оценок для person_id={student_id}: {e}")
                        continue
            
            logger.info(f"Fetched marks for work_id={work_id}: {len(result)} records")
            return result
            
        except ValueError as e:
            logger.info(f"Invalid work_id={work_id}: {e}")
            raise
        except Exception as e:
            logger.info(f"Error fetching marks for work_id={work_id}: {e}")
            return result

    async def _get_formatted_schedule_day(self, date: datetime) -> List[Dict[str, any]]:
        """
        Форматирует расписание уроков за один день.

        **Назначение**:
        Извлекает и форматирует данные расписания на указанную дату.

        **Параметры**:
        - date (datetime): Дата расписания.

        **Алгоритм работы**:
        1. Проверяет кэш _schedule_cache.
        2. Запрашивает расписание через API, если кэш пуст или устарел.
        3. Форматирует данные: предметы, учителя, домашние задания, оценки.
        4. Сортирует уроки по номеру и кэширует результат.

        **Возвращаемые значения**:
        - List[Dict[str, any]]: Список уроков с подробной информацией.
        """
        start_time = time.time()
        date_str = date.strftime('%Y-%m-%d')
        if date_str in self._schedule_cache:
            logger.info(f"Использован кэш расписания для {date_str}")
            return self._schedule_cache[date_str]
        try:
            async with self.semaphore:
                async with dnevnik.AsyncDiaryAPI(token=self.token) as dn:
                    schedule = await dn.get(
                        f"persons/{self.person_id}/groups/{self.group_id}/schedules",
                        params={
                            "startDate": date.strftime("%Y-%m-%dT00:00:00"),
                            "endDate": date.strftime("%Y-%m-%dT23:59:59")
                        }
                    )
        except Exception as e:
            logger.error(f"Ошибка получения расписания за {date_str}: {str(e)}")
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
                    logger.info(f"Добавлен предмет: {subject_id} -> {subject_name}")
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
                    logger.warning(f"Пропущен дублирующийся урок ID={lesson_id}")
                    continue
                seen_lesson_ids.add(lesson_id)
                subject_id = str(lesson.get('subjectId', '0'))
                if subject_id not in subjects:
                    logger.warning(f"Пропущен урок ID={lesson_id}: subject_id={subject_id} отсутствует")
                    continue
                lesson_number = lesson.get('number', 0)
                subject_name = subjects.get(subject_id, 'Неизвестный предмет')
                teacher_name = ', '.join(teachers.get(str(t), 'Неизвестно') for t in lesson.get('teachers', [])) or 'Неизвестно'
                classroom = f"{lesson.get('building', 'Не указан')} {lesson.get('place', 'Не указан')} {lesson.get('floor', '')}".strip()
                if classroom == "Не указан Не указан":
                    classroom = "Не указан"
                lesson_title = lesson.get('title', subject_name) or subject_name
                time_str = lesson.get('hours', 'Неизвестное время')
                lesson_status = lesson.get('status', 'Неизвестно')
                attendance = lesson_logs.get(lesson_id, 'Присутствовал')
                lesson_works = []
                for work_id in lesson.get('works', []):
                    work_id_str = str(work_id)
                    work = works.get(work_id_str)
                    if work:
                        work_type_id = str(work.get('workType', '0'))
                        work_type_name = work_types.get(work_type_id, self._work_types_cache.get(work_type_id, 'Неизвестный тип'))
                        lesson_works.append({'work': work_type_name})
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
                homework = '\n'.join(homework_text) or 'Нет задания'
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
                            'work_type': work_types.get(work_type_id, self._work_types_cache.get(work_type_id, 'Неизвестный тип')),
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
                    'works': lesson_works,
                    'lesson_number': lesson_number,
                    'lesson_status': lesson_status,
                    'attendance': attendance,
                    'is_important': is_important,
                    'sent_date': sent_date
                })
        formatted_schedule.sort(key=lambda x: x['lesson_number'])
        self._schedule_cache[date_str] = formatted_schedule
        logger.info(f"Расписание за {date_str}: {len(formatted_schedule)} уроков")
        elapsed_time = time.time() - start_time
        logger.info(f"Форматирование расписания за {date_str} завершено за {elapsed_time:.2f} секунд")
        return formatted_schedule

    async def get_formatted_schedule(self, start_date: datetime, end_date: Optional[datetime] = None) -> Dict[str, List[Dict[str, any]]] | List[Dict[str, any]]:
        """
        Получает расписание за одну дату или диапазон дат.

        **Назначение**:
        Предоставляет расписание уроков с подробной информацией.

        **Параметры**:
        - start_date (datetime): Начальная дата.
        - end_date (Optional[datetime]): Конечная дата.

        **Алгоритм работы**:
        1. Если end_date не указан, возвращает расписание за start_date.
        2. Проверяет корректность дат.
        3. Вызывает _get_formatted_schedule_day для каждой даты.
        4. Возвращает словарь или список уроков.

        **Возвращаемые значения**:
        - Dict[str, List[Dict[str, any]]] | List[Dict[str, any]]: Расписание за период или день.
        """
        start_time = time.time()
        if end_date is None:
            result = await self._get_formatted_schedule_day(start_date)
            logger.info(f"Получение расписания за {start_date.strftime('%Y-%m-%d')} завершено")
            return result
        if end_date < start_date:
            raise ValueError("end_date не может быть раньше start_date")
        result = {}
        tasks = []
        dates = []
        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date)
            tasks.append(self._get_formatted_schedule_day(current_date))
            current_date += timedelta(days=1)
        schedules = await asyncio.gather(*tasks, return_exceptions=True)
        for date, schedule in zip(dates, schedules):
            date_str = date.strftime('%Y-%m-%d')
            result[date_str] = [] if isinstance(schedule, Exception) else schedule
        elapsed_time = time.time() - start_time
        logger.info(f"Получение расписания за диапазон завершено за {elapsed_time:.2f} секунд")
        return result

    async def get_last_marks(self, count: int = 5, subject_id: Optional[int] = None) -> List[Dict[str, any]]:
        """
        Получает последние оценки ученика.

        **Назначение**:
        Извлекает последние count оценок, возможно, по предмету.

        **Параметры**:
        - count (int): Количество оценок (по умолчанию 5).
        - subject_id (Optional[int]): ID предмета.

        **Алгоритм работы**:
        1. Проверяет корректность count.
        2. Загружает кэши, если пусты.
        3. Запрашивает оценки за последние 90 дней.
        4. Фильтрует и форматирует оценки, включая распределение по классу.

        **Возвращаемые значения**:
        - List[Dict[str, any]]: Список оценок с деталями.
        """
        start_time = time.time()
        if count <= 0:
            raise ValueError("Count должен быть положительным")
        result = []
        try:
            if not self._student_cache:
                await self._load_students()
            if not self._subject_cache:
                await self._load_subjects()
            if subject_id and str(subject_id) not in self._subject_cache:
                logger.warning(f"subject_id={subject_id} отсутствует, фильтр отключен")
                subject_id = None
            async with self.semaphore:
                async with dnevnik.AsyncDiaryAPI(token=self.token) as dn:
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=90)
                    marks = await dn.get_person_marks(self.person_id, self.school_id, start_date, end_date)
                    logger.info(f"Получено оценок: {len(marks)}")
            def parse_mark_date(date_str):
                for fmt in ('%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d'):
                    try:
                        return datetime.strptime(date_str, fmt)
                    except ValueError:
                        continue
                logger.warning(f"Некорректная дата оценки: {date_str}")
                return datetime.now()
            marks.sort(key=lambda x: parse_mark_date(x.get('date', '1970-01-01')), reverse=True)
            marks = marks[:count]
            async def process_mark(mark):
                lesson_id = str(mark.get('lesson_str', '0'))
                work_id = str(mark.get('work_str', '0'))
                mark_date = parse_mark_date(mark.get('date', '1970-01-01')).date()
                lesson_data = await self._get_lesson_info(lesson_id)
                subject_id_from_mark = str(lesson_data.get('subject', {}).get('id')) if lesson_data.get('subject') else None
                if subject_id and subject_id_from_mark and str(subject_id) != subject_id_from_mark:
                    return None
                mark_info = {
                    'subject': self._subject_cache.get(subject_id_from_mark, 'Неизвестный предмет'),
                    'work_type': 'Неизвестный тип',
                    'lesson_title': lesson_data.get('title', 'Неизвестная тема'),
                    'mark': mark.get('value', 'Нет оценки'),
                    'class_distribution': {},
                    'date': mark_date.strftime('%d.%m.%Y')
                }
                if lesson_data.get('works'):
                    for work in lesson_data.get('works', []):
                        if str(work.get('id')) == work_id:
                            work_type_id = str(work.get('workType', '0'))
                            mark_info['work_type'] = self._work_types_cache.get(work_type_id, 'Неизвестный тип')
                            break
                if work_id and work_id != '0' and self._student_cache:
                    try:
                        student_marks = await self._get_work_marks_by_id(int(work_id))
                        distribution = defaultdict(lambda: {"count": 0, "student_marks": []})
                        for sm in student_marks:
                            mark_value = sm["mark"]
                            distribution[mark_value]["count"] += 1
                            distribution[mark_value]["student_marks"].append({
                                "name": sm["name"],
                                "mark": mark_value
                            })
                        mark_info['class_distribution'] = dict(distribution)
                    except Exception as e:
                        logger.error(f"Ошибка получения распределения для work_id={work_id}: {str(e)}")
                return mark_info
            tasks = [process_mark(mark) for mark in marks]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            result = [r for r in results if not isinstance(r, Exception) and r]
            logger.info(f"Получено последних оценок: {len(result)}")
        except Exception as e:
            logger.error(f"Ошибка в get_last_marks: {str(e)}")
        finally:
            elapsed_time = time.time() - start_time
            logger.info(f"Получение последних оценок завершено за {elapsed_time:.2f} секунд")
        return result

    async def get_formatted_marks(self, start_date: datetime, end_date: Optional[datetime] = None) -> Dict[str, List[Dict[str, str]]]:
        """
        Получает оценки за период, сгруппированные по предметам.

        **Назначение**:
        Извлекает оценки за указанный период, форматируя их по предметам.

        **Параметры**:
        - start_date (datetime): Начальная дата.
        - end_date (Optional[datetime]): Конечная дата.

        **Алгоритм работы**:
        1. Устанавливает end_date = start_date, если не указан.
        2. Запрашивает расписание за период.
        3. Форматирует оценки, группируя по предметам.
        4. Сортирует оценки по дате.

        **Возвращаемые значения**:
        - Dict[str, List[Dict[str, str]]]: Оценки по предметам.
        """
        start_time = time.time()
        end_date = end_date or start_date
        try:
            async with self.semaphore:
                async with dnevnik.AsyncDiaryAPI(token=self.token) as dn:
                    schedule = await dn.get(
                        f"persons/{self.person_id}/groups/{self.group_id}/schedules",
                        params={
                            "startDate": start_date.strftime("%Y-%m-%dT00:00:00"),
                            "endDate": end_date.strftime("%Y-%m-%dT23:59:59")
                        }
                    )
                    logger.info(f"Получено дней расписания: {len(schedule.get('days', []))}")
        except Exception as e:
            logger.error(f"Ошибка получения расписания: {str(e)}")
            return {}
        formatted_marks = defaultdict(list)
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
                        logger.info(f"Добавлен предмет: {subject_id} -> {self._subject_cache[subject_id]}")
                for mark in day.get('marks', []):
                    if str(mark['person']) == self.person_id:
                        marks.append(mark)
        for mark in marks:
            lesson_id = str(mark.get('lesson_str', '0'))
            lesson_data = lessons.get(lesson_id, {})
            subject_id = str(lesson_data.get('subjectId', '0')) if lesson_data.get('subjectId') else None
            if not subject_id or subject_id not in allowed_subject_ids:
                continue
            subject_name = self._subject_cache.get(subject_id, 'Неизвестный предмет')
            try:
                lesson_date = datetime.strptime(lesson_data.get('date', day.get('date', '1970-01-01T00:00:00')), '%Y-%m-%dT%H:%M:%S').date()
                mark_date = datetime.strptime(mark.get('date', '1970-01-01T00:00:00.000000'), '%Y-%m-%dT%H:%M:%S.%f').date()
            except ValueError:
                logger.warning(f"Некорректная дата для урока {lesson_id}")
                continue
            if lesson_date < start_date.date() or lesson_date > end_date.date():
                continue
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
            formatted_marks[subject].sort(key=lambda x: x['mark_date'])
        elapsed_time = time.time() - start_time
        logger.info(f"Получение оценок завершено за {elapsed_time:.2f} секунд")
        return dict(formatted_marks)

    async def get_group_teachers(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, str]]:
        """
        Получает список учителей группы за период.

        **Назначение**:
        Извлекает информацию об учителях из домашних заданий.

        **Параметры**:
        - start_date (Optional[datetime]): Начальная дата (по умолчанию -7 дней).
        - end_date (Optional[datetime]): Конечная дата (по умолчанию +30 дней).

        **Алгоритм работы**:
        1. Устанавливает даты по умолчанию, если не указаны.
        2. Запрашивает уроки с домашними заданиями.
        3. Извлекает учителей и форматирует данные.
        4. Сортирует по ID.

        **Возвращаемые значения**:
        - List[Dict[str, str]]: Список учителей с данными.
        """
        start_time = time.time()
        start_date = start_date or (datetime.now() - timedelta(days=7))
        end_date = end_date or (datetime.now() + timedelta(days=30))
        if end_date < start_date:
            raise ValueError("end_date не может быть раньше start_date")
        try:
            async with self.semaphore:
                async with dnevnik.AsyncDiaryAPI(token=self.token) as dn:
                    homeworks = await dn.get(
                        f"persons/{self.person_id}/school/{self.school_id}/homeworks",
                        params={
                            "startDate": start_date.strftime('%Y-%m-%d'),
                            "endDate": end_date.strftime('%Y-%m-%d')
                        }
                    )
                    lessons = homeworks.get('lessons', [])
        except Exception as e:
            logger.error(f"Ошибка получения уроков: {str(e)}")
            return []
        teacher_ids = set()
        for lesson in lessons:
            lesson_date = datetime.strptime(lesson.get('date', '1970-01-01'), '%Y-%m-%dT%H:%M:%S').date()
            if start_date.date() <= lesson_date <= end_date.date():
                for teacher_id in lesson.get('teachers', []):
                    teacher_ids.add(str(teacher_id))
        result = []
        teachers_dict = await self._load_teachers()
        for teacher_id in sorted(teacher_ids):
            teacher_info = teachers_dict.get(teacher_id, {
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
        elapsed_time = time.time() - start_time
        logger.info(f"Получение учителей завершено за {elapsed_time:.2f} секунд")
        return result

    async def _get_quarter_period_id(self, quarter: int, study_year: Optional[int] = None) -> Optional[Tuple[str, datetime, datetime]]:
        """
        Получает ID и даты периода для четверти.

        **Назначение**:
        Определяет учебный период для указанной четверти.

        **Параметры**:
        - quarter (int): Номер четверти (1–4).
        - study_year (Optional[int]): Учебный год.

        **Алгоритм работы**:
        1. Проверяет корректность quarter.
        2. Запрашивает периоды через `/edu-groups/{group_id}/reporting-periods`.
        3. Выбирает текущий или ближайший период.
        4. Возвращает ID, даты или None.

        **Возвращаемые значения**:
        - Optional[Tuple[str, datetime, datetime]]: ID и даты периода.
        """
        start_time = time.time()
        if quarter not in [1, 2, 3, 4, 5, 6]:
            logger.error(f"Некорректная четверть: {quarter}")
            return None
        try:
            async with self.semaphore:
                async with dnevnik.AsyncDiaryAPI(token=self.token) as dn:
                    periods = await dn.get(f"edu-groups/{self.group_id}/reporting-periods")
                    logger.info(periods)
            quarter_to_number = {'Quarter': quarter - 1, 'Semester': 0 if quarter in [1, 2] else 1,'Trimester': quarter - 1,'Module': quarter - 1}
            current_date = datetime.now()
            candidate_periods = []
            min_date_diff = None
            closest_period = None
            for period in periods:
                period_type = period.get('type', '')
                period_number = period.get('number', -1)
                start_date_str = period.get('start', '')
                finish_date_str = period.get('finish', '')
                period_year = period.get('year', 0)
                period_name = period.get('name', 'Неизвестный период')
                if period_type not in ['Quarter', 'Semester', 'Trimester', 'Module']:
                    continue
                if period_number != quarter_to_number.get(period_type):
                    continue
                try:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M:%S')
                    finish_date = datetime.strptime(finish_date_str, '%Y-%m-%dT%H:%M:%S')
                except ValueError:
                    try:
                        start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M:%S.%f')
                        finish_date = datetime.strptime(finish_date_str, '%Y-%m-%dT%H:%M:%S.%f')
                    except ValueError:
                        logger.warning(f"Некорректные даты: start={start_date_str}, finish={finish_date_str}")
                        continue
                effective_year = start_date.year if start_date.month >= 9 else finish_date.year
                if study_year is not None and effective_year != study_year and effective_year != study_year - 1:
                    continue
                period_data = (str(period.get('id')), start_date, finish_date, period_name)
                if start_date <= current_date <= finish_date:
                    logger.info(f"Выбран текущий период: ID={period_data[0]}, name={period_name}")
                    return period_data[:3]
                candidate_periods.append(period_data)
                date_diff = abs((start_date - current_date).total_seconds())
                if min_date_diff is None or date_diff < min_date_diff:
                    min_date_diff = date_diff
                    closest_period = period_data
            if closest_period:
                logger.info(f"Выбран ближайший период: ID={closest_period[0]}, name={closest_period[3]}")
                return closest_period
            logger.warning(f"Период для {quarter} не найден")
            return None
        except Exception as e:
            logger.error(f"Ошибка получения периодов: {str(e)}")
            return None
        finally:
            elapsed_time = time.time() - start_time
            logger.info(f"Получение ID периода завершено за {elapsed_time:.2f} секунд")

    async def get_formatted_final_marks(self, quarter: int, study_year: Optional[int] = None) -> List[Dict[str, any]]:
        """
        Получает итоговые оценки за четверть.

        **Назначение**:
        Извлекает средние оценки по предметам за четверть.

        **Параметры**:
        - quarter (int): Номер четверти (1–4).
        - study_year (Optional[int]): Учебный год.

        **Алгоритм работы**:
        1. Проверяет корректность quarter.
        2. Получает ID и даты периода.
        3. Запрашивает расписание и оценки.
        4. Вычисляет средние баллы по предметам.

        **Возвращаемые значения**:
        - List[Dict[str, any]]: Список с предметами, оценками и средними баллами.
        """
        start_time = time.time()
        if quarter not in [1, 2, 3, 4]:
            raise ValueError("Номер четверти должен быть от 1 до 4")
        period_data = await self._get_quarter_period_id(quarter, study_year)
        if not period_data:
            return []
        period_id, start_date, finish_date = period_data
        try:
            async with self.semaphore:
                async with dnevnik.AsyncDiaryAPI(token=self.token) as dn:
                    schedule = await dn.get(
                        f"persons/{self.person_id}/groups/{self.group_id}/schedules",
                        params={
                            "startDate": start_date.strftime("%Y-%m-%dT00:00:00"),
                            "endDate": finish_date.strftime("%Y-%m-%dT23:59:59")
                        }
                    )
            active_subject_ids = set()
            for day in schedule.get('days', []):
                day_date = datetime.strptime(day.get('date', '1970-01-01T00:00:00'), '%Y-%m-%dT%H:%M:%S').date()
                if start_date.date() <= day_date <= finish_date.date():
                    for lesson in day.get('lessons', []):
                        subject_id = str(lesson.get('subjectId', '0'))
                        active_subject_ids.add(subject_id)
                        for subject in day.get('subjects', []):
                            subj_id = str(subject.get('id'))
                            if subj_id not in self._subject_cache:
                                self._subject_cache[subj_id] = subject.get('name', 'Неизвестный предмет')
                                logger.info(f"Добавлен предмет: {subj_id} -> {self._subject_cache[subj_id]}")
            if not active_subject_ids:
                active_subject_ids = set(self._subject_cache.keys())
            async def fetch_marks(subject_id):
                async with self.semaphore:
                    try:
                        async with dnevnik.AsyncDiaryAPI(token=self.token) as dn:
                            marks = await dn.get_person_subject_marks(self.person_id, int(subject_id), start_date, finish_date)
                        grades = [mark['value'] for mark in marks if mark.get('value', '').replace('.', '', 1).isdigit()]
                        average = str(round(statistics.mean([float(g) for g in grades]), 1)) if grades else "Нет оценок"
                        return {
                            'название предмета': self._subject_cache.get(subject_id, 'Неизвестный предмет'),
                            'оценки': grades,
                            'средний балл': average
                        }
                    except Exception as e:
                        logger.error(f"Ошибка получения оценок для предмета {subject_id}: {str(e)}")
                        return None
            tasks = [fetch_marks(subject_id) for subject_id in active_subject_ids]
            formatted_marks = await asyncio.gather(*tasks, return_exceptions=True)
            formatted_marks = [mark for mark in formatted_marks if not isinstance(mark, Exception) and mark]
            formatted_marks.sort(key=lambda x: x['название предмета'])
            logger.info(f"Получено итоговых оценок: {len(formatted_marks)}")
            return formatted_marks
        except Exception as e:
            logger.error(f"Ошибка в get_formatted_final_marks: {str(e)}")
            return []
        finally:
            elapsed_time = time.time() - start_time
            logger.info(f"Получение итоговых оценок завершено за {elapsed_time:.2f} секунд")

    async def get_class_ranking(self, quarter: int, study_year: Optional[int] = None) -> List[Dict]:
        """
        Формирует рейтинг класса по средним оценкам.

        **Назначение**:
        Вычисляет средний балл учеников за четверть и сортирует по убыванию.

        **Параметры**:
        - quarter (int): Номер четверти (1–4).
        - study_year (Optional[int]): Учебный год.

        **Алгоритм работы**:
        1. Проверяет корректность quarter.
        2. Получает ID и даты периода.
        3. Для каждого ученика вычисляет средний балл.
        4. Сортирует по среднему баллу.

        **Возвращаемые значения**:
        - List[Dict]: Рейтинг учеников с именами, средними баллами и количеством оценок.
        """
        start_time = time.time()
        if quarter not in [1, 2, 3, 4]:
            raise ValueError("Номер четверти должен быть от 1 до 4")
        period_data = await self._get_quarter_period_id(quarter, study_year)
        if not period_data:
            return []
        period_id, start_date, finish_date = period_data
        ranking = []
        async def fetch_grades(student_id, student_name):
            async with self.semaphore:
                student_grades = []
                for subject_id in self._subject_cache:
                    try:
                        async with dnevnik.AsyncDiaryAPI(token=self.token) as dn:
                            marks = await dn.get_person_subject_marks(student_id, int(subject_id), start_date, finish_date)
                            grades = [float(mark['value']) for mark in marks if mark.get('value', '').replace('.', '', 1).isdigit()]
                            student_grades.extend(grades)
                    except Exception as e:
                        logger.error(f"Ошибка получения оценок для ученика {student_id}, предмет {subject_id}: {str(e)}")
                avg_grade = statistics.mean(student_grades) if student_grades else 0
                return {
                    'name': student_name,
                    'avg_grade': round(avg_grade, 2),
                    'marks_count': len(student_grades)
                }
        tasks = [fetch_grades(student_id, student_name) for student_id, student_name in self._student_cache.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        ranking = [res for res in results if not isinstance(res, Exception)]
        ranking.sort(key=lambda x: x['avg_grade'], reverse=True)
        elapsed_time = time.time() - start_time
        logger.info(f"Формирование рейтинга класса завершено за {elapsed_time:.2f} секунд")
        return ranking

    async def get_subject_stats(self, quarter: int, subject_id: int, study_year: Optional[int] = None) -> Dict[str, int]:
        """
        Получает гистограмму оценок по предмету за четверть.

        **Назначение**:
        Возвращает распределение оценок по предмету.

        **Параметры**:
        - quarter (int): Номер четверти (1–4).
        - subject_id (int): ID предмета.
        - study_year (Optional[int]): Учебный год.

        **Алгоритм работы**:
        1. Проверяет корректность quarter.
        2. Получает ID и даты периода.
        3. Запрашивает гистограмму через get_subject_marks_histogram.
        4. Суммирует оценки.

        **Возвращаемые значения**:
        - Dict[str, int]: Распределение оценок.
        """
        start_time = time.time()
        if quarter not in [1, 2, 3, 4]:
            raise ValueError("Номер четверти должен быть от 1 до 4")
        period_data = await self._get_quarter_period_id(quarter, study_year)
        if not period_data:
            return {}
        period_id, start_date, finish_date = period_data
        try:
            async with self.semaphore:
                async with dnevnik.AsyncDiaryAPI(token=self.token) as dn:
                    histogram = await dn.get_subject_marks_histogram(self.group_id, period_id, subject_id)
                    hist_data = defaultdict(int)
                    for work in histogram.get('works', []):
                        for mark_number in work.get('markNumbers', []):
                            for mark in mark_number.get('marks', []):
                                value = str(mark.get('value'))
                                count = mark.get('count', 0)
                                hist_data[value] += count
                    return dict(hist_data)
        except Exception as e:
            logger.error(f"Ошибка получения статистики для предмета {subject_id}: {str(e)}")
            return {}
        finally:
            elapsed_time = time.time() - start_time
            logger.info(f"Получение статистики завершено за {elapsed_time:.2f} секунд")

    async def get_subject_ranking(self, quarter: int, subject_id: int, study_year: Optional[int] = None) -> List[Dict]:
        """
        Формирует рейтинг учеников по предмету за четверть.

        **Назначение**:
        Вычисляет средний балл учеников по предмету и сортирует.

        **Параметры**:
        - quarter (int): Номер четверти (1–4).
        - subject_id (int): ID предмета.
        - study_year (Optional[int]): Учебный год.

        **Алгоритм работы**:
        1. Проверяет корректность quarter и subject_id.
        2. Получает ID и даты периода.
        3. Загружает учеников, если кэш пуст.
        4. Вычисляет средние баллы и сортирует.

        **Возвращаемые значения**:
        - List[Dict]: Рейтинг учеников по предмету.
        """
        start_time = time.time()
        if quarter not in [1, 2, 3, 4]:
            raise ValueError("Номер четверти должен быть от 1 до 4")
        period_data = await self._get_quarter_period_id(quarter, study_year)
        if not period_data:
            return []
        period_id, start_date, finish_date = period_data
        if str(subject_id) not in self._subject_cache:
            logger.error(f"Предмет {subject_id} отсутствует")
            return []
        if not self._student_cache:
            await self._load_students()
            if not self._student_cache:
                logger.error("Не удалось загрузить учеников")
                return []
        ranking = []
        async def fetch_grades(student_id, student_name):
            async with self.semaphore:
                try:
                    async with dnevnik.AsyncDiaryAPI(token=self.token) as dn:
                        marks = await dn.get_person_subject_marks(student_id, subject_id, start_date, finish_date)
                        grades = [float(mark['value']) for mark in marks if mark.get('value', '').replace('.', '', 1).isdigit()]
                        avg_grade = statistics.mean(grades) if grades else 0
                        return {
                            'name': student_name,
                            'avg_grade': round(avg_grade, 2),
                            'marks_count': len(grades)
                        }
                except Exception as e:
                    logger.error(f"Ошибка получения оценок для ученика {student_id}: {str(e)}")
                    return None
        tasks = [fetch_grades(student_id, student_name) for student_id, student_name in self._student_cache.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        ranking = [res for res in results if not isinstance(res, Exception) and res]
        ranking.sort(key=lambda x: x['avg_grade'], reverse=True)
        elapsed_time = time.time() - start_time
        logger.info(f"Формирование рейтинга по предмету завершено за {elapsed_time:.2f} секунд")
        return ranking

    async def get_upcoming_tests(self) -> List[Dict[str, str]]:
        """
        Получает список предстоящих тестов на 2 недели.

        **Назначение**:
        Извлекает тесты с весом >= 5 на ближайшие 14 дней.

        **Алгоритм работы**:
        1. Устанавливает период (текущая дата + 14 дней).
        2. Получает расписание через get_formatted_schedule.
        3. Извлекает тесты с весом >= 5.
        4. Сортирует по дате.

        **Возвращаемые значения**:
        - List[Dict[str, str]]: Список тестов с датой, предметом, типом и весом.
        """
        start_time = time.time()
        start_date = datetime.now()
        end_date = start_date + timedelta(days=14)
        schedule = await self.get_formatted_schedule(start_date, end_date)
        tests = []
        for date_str, lessons in schedule.items():
            for lesson in lessons:
                for work in lesson.get("works", []):
                    work_type = work["work"]
                    if work_type in self.title_to_weight and self.title_to_weight[work_type] >= 5:
                        tests.append({
                            "date": date_str,
                            "subject": lesson["subject"],
                            "work_type": work_type,
                            "description": f"{work_type}: {lesson['title']}",
                            "weight": self.title_to_weight[work_type]
                        })
        tests.sort(key=lambda x: datetime.strptime(x["date"], "%Y-%m-%d"))
        logger.info(f"Найдено тестов: {len(tests)}")
        elapsed_time = time.time() - start_time
        logger.info(f"Получение тестов завершено за {elapsed_time:.2f} секунд")
        return tests

    async def analyze_data(self, analysis_type: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, quarter: Optional[int] = None, study_year: Optional[int] = None) -> str:
        """
        Выполняет AI-анализ данных.

        **Назначение**:
        Отправляет данные в AI для анализа (расписание, оценки, рейтинг).

        **Параметры**:
        - analysis_type (str): Тип анализа ('weeks', 'marks', 'ranking').
        - start_date (Optional[datetime]): Начальная дата.
        - end_date (Optional[datetime]): Конечная дата.
        - quarter (Optional[int]): Номер четверти.
        - study_year (Optional[int]): Учебный год.

        **Алгоритм работы**:
        1. Проверяет корректность analysis_type.
        2. Загружает промпты из prompts.json.
        3. Формирует данные и отправляет в AI.
        4. Возвращает ответ AI.

        **Возвращаемые значения**:
        - str: Ответ AI или сообщение об ошибке.
        """
        start_time = time.time()
        valid_types = ['weeks', 'marks', 'ranking']
        if analysis_type not in valid_types:
            logger.error(f"Некорректный тип анализа: {analysis_type}")
            return f"Ошибка: Некорректный тип анализа '{analysis_type}'"
        try:
            prompts = await self._read_prompts()
            prompt_text = prompts.get(analysis_type, "")
            if not prompt_text:
                logger.error(f"Промпт для '{analysis_type}' не найден")
                return f"Ошибка: Промпт для '{analysis_type}' не найден"
            if analysis_type == 'weeks':
                if not start_date or not end_date:
                    return "Ошибка: Укажите start_date и end_date"
                schedule_data = await self.get_formatted_schedule(start_date, end_date)
                works_data = await self.get_upcoming_tests()
                full_prompt = prompt_text.format(
                    schedule_data=json.dumps(schedule_data, ensure_ascii=False, indent=2),
                    works_data=json.dumps(works_data, ensure_ascii=False, indent=2)
                )
            elif analysis_type == 'marks':
                if not start_date or not end_date:
                    return "Ошибка: Укажите start_date и end_date"
                marks_data = await self.get_formatted_marks(start_date, end_date)
                full_prompt = prompt_text.format(
                    marks_data=json.dumps(marks_data, ensure_ascii=False, indent=2)
                )
            elif analysis_type == 'ranking':
                if not quarter:
                    return "Ошибка: Укажите quarter"
                ranking_data = await self.get_class_ranking(quarter, study_year)
                full_prompt = prompt_text.format(
                    ranking_data=json.dumps(ranking_data, ensure_ascii=False, indent=2)
                )
            response = await self.make_ai_request(full_prompt)
            return response
        except Exception as e:
            logger.error(f"Ошибка анализа '{analysis_type}': {str(e)}")
            return f"Ошибка анализа '{analysis_type}': {str(e)}"
        finally:
            elapsed_time = time.time() - start_time
            logger.info(f"Анализ данных '{analysis_type}' завершен за {elapsed_time:.2f} секунд")

