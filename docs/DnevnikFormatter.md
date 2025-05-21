# Документация по модулю DnevnikFormatter

![Static Badge](https://img.shields.io/badge/DnevnikRuAPI_NEW-Sirop12)
![GitHub top language](https://img.shields.io/github/languages/top/Sirop12/DnevnikRuAPI_NEW)
![GitHub](https://img.shields.io/github/license/Sirop12/DnevnikRuAPI_NEW)
![GitHub Repo stars](https://img.shields.io/github/stars/Sirop12/DnevnikRuAPI_NEW)
![GitHub issues](https://img.shields.io/github/issues/Sirop12/DnevnikRuAPI_NEW)

[СВЯЗЬ](https://t.me/Sirop1)

[ПОЛУЧИТЬ ТОКЕН](https://androsovpavel.pythonanywhere.com/)

## СКОРО
- Автоматическая регистрация через госуслуги
- ГОТОВО!!!
- Расширенная статистика по классам по школе
- тг бот??

## Общее описание

`DnevnikFormatter` — это Python-класс для обработки данных, получаемых через API Дневник.ру, предназначенный для разработчиков, интегрирующих информацию об учебном процессе в свои приложения. Класс предоставляет структурированные данные о расписании, оценках, учителях, тестах и статистике класса, оптимизируя запросы через кэширование и поддерживая ИИ-анализ через DeepSeek (OpenRouter).

### Основные возможности
- Получение расписания уроков за день или период с деталями (время, предмет, домашние задания, оценки).
- Извлечение последних оценок с фильтрацией по предмету и распределением по классу.
- Формирование оценок за период, сгруппированных по предметам.
- Получение итоговых оценок за четверть с вычислением среднего балла.
- Список учителей группы с информацией о предметах и контактах.
- Формирование рейтингов учеников класса или по предмету.
- Статистика по предметам и классу (распределение оценок, средний балл).
- Получение списка предстоящих тестов, включая контрольные работы.
- ИИ-анализ расписания, оценок и рейтингов с рекомендациями.

### Требования
- **Python**: Версия 3.8 или выше (рекомендуется 3.10+).
- **Библиотеки**:
  - `pydnevnikruapi==2.1.3` — для работы с API Дневник.ру.
  - `openai==1.47.1` — для ИИ-анализа через DeepSeek (опционально).
  - `python-dateutil==2.9.0.post0` — для работы с датами.
  - Встроенные модули: `datetime`, `statistics`, `collections`, `json`, `typing`.
- **Токен API**: Действующий токен авторизации от Дневник.ру.
- **Файл `prompts.json`**: Для ИИ-анализа (опционально).
- **Переменная окружения `OPENROUTER_API_KEY`**: Для доступа к OpenRouter (опционально).
- **Доступ к интернету**: Для выполнения запросов к API.

### Установка и настройка
1. Установите Python (рекомендуется 3.10+).
2. Установите необходимые библиотеки:
   ```bash
   pip install pydnevnikruapi==2.1.3 openai==1.47.1 python-dateutil==2.9.0.post0
   ```
3. Получите токен API:
   - Зарегистрируйтесь на платформе Дневник.ру.
   - Используйте [ссылку](https://androsovpavel.pythonanywhere.com/) или обратитесь к документации API для получения токена (например, `FDSf234refd23fdf232`).
4. (Опционально) Настройте ИИ-анализ:
   - Создайте файл `prompts.json` с промптами:
     ```json
     {
       "weeks": "Анализируй расписание за период {start_date}–{end_date}. Определи загруженность и предложи рекомендации.",
       "marks": "Проанализируй оценки за период {start_date}–{end_date}. Выяви сильные и слабые предметы.",
       "ranking": "Проанализируй рейтинг за {quarter}-ю четверть {study_year}. Оцени позицию ученика."
     }
     ```
   - Установите переменную окружения:
     ```bash
     export OPENROUTER_API_KEY="your_openrouter_api_key"
     ```
5. Импортируйте класс и модули:
   ```python
   from DnevnikFormatter import DnevnikFormatter
   from datetime import datetime
   ```

### Инициализация класса
Класс инициализируется с токеном API и параметром отладки.

#### Синтаксис
```python
formatter = DnevnikFormatter(token, debug_mode=True)
```

#### Параметры
- **token** (`str`): Токен авторизации API.
  - **Пример**: `"FDSf234refd23fdf232"`.
  - **Ограничения**: Должен быть действительным, иначе вызывается `ValueError`.
- **debug_mode** (`bool`, по умолчанию `True`): Включает отладочные сообщения.
  - **Описание**: Выводит логи запросов, ошибок и состояния кэшей в `bot.log` и консоль.
  - **Пример**: `False` для продакшена.

#### Пример инициализации
```python
from DnevnikFormatter import DnevnikFormatter
from datetime import datetime

# Инициализация
token = "FDSf234refd23fdf232"
formatter = DnevnikFormatter(token=token, debug_mode=True)

# Проверка
print(f"ID пользователя: {formatter.person_id}")
```

#### Нюансы
- **Кэширование**: При инициализации загружаются кэши (`_subject_cache`, `_student_cache`, `_teacher_cache`, `_work_types_cache`).
- **Ошибки**:
  - `ValueError`: Недействительный токен или отсутствие API-ключа OpenRouter (если требуется).
  - Сетевые ошибки API логируются и перебрасываются.
- **Отладка**: `debug_mode=True` полезен для диагностики.

---

## Основные методы класса

Ниже описаны девять основных методов с обработанным выводом и примерами использования. Метод `get_class_stats` заменён на `get_upcoming_tests`, а `analyze_data` добавлен для ИИ-анализа.

### 1. `get_formatted_schedule`

#### Назначение
Получает расписание уроков за одну дату или период с деталями: время, предмет, домашнее задание, учитель, оценки, место проведения.

#### Синтаксис
```python
result = formatter.get_formatted_schedule(start_date, end_date=None)
```

#### Входные параметры
- **start_date** (`datetime`): Начальная дата.
  - **Описание**: Дата начала расписания.
  - **Ограничения**: Валидная `datetime`.
  - **Пример**: `datetime(2025, 5, 21)`.
- **end_date** (`Optional[datetime]`, по умолчанию `None`): Конечная дата.
  - **Описание**: Если указана, возвращается расписание за период. Если `None`, за `start_date`.
  - **Ограничения**: Не раньше `start_date`.
  - **Пример**: `datetime(2025, 5, 28)`.

#### Выходные данные
- **Тип**:
  - `List[Dict[str, any]]` (для одной даты).
  - `Dict[str, List[Dict[str, any]]]` (для периода).
- **Структура урока**:
  - `time` (`str`): Время урока.
  - `subject` (`str`): Название предмета.
  - `homework` (`str`): Домашнее задание.
  - `files` (`list`): Файлы задания (имя и URL).
  - `title` (`str`): Тема урока.
  - `teacher` (`str`): Имя учителя.
  - `mark_details` (`list`): Оценки (`value`, `work_type`, `mood`, `lesson_title`).
  - `classroom` (`str`): Место проведения.
  - `lesson_id` (`str`): ID урока.
  - `works` (`list`): Тесты/работы (`work: str`, `weight: int`)
  - `lesson_number` (`int`): Номер урока.
  - `lesson_status` (`str`): Статус урока.
  - `attendance` (`str`): Посещаемость.
  - `is_important` (`bool`): Важность задания.
  - `sent_date` (`str`): Дата отправки задания.

#### Обработанный вывод (для одной даты)
```python
[
  {
    "time": "08:30-09:15",
    "subject": "Математика",
    "homework": "Решить задачи 1-5 на стр. 45",
    "files": ["tasks.pdf (http://example.com/tasks.pdf)"],
    "title": "Решение уравнений",
    "teacher": "Иванов И.И.",
    "mark_details": [
      {
        "value": "5",
        "work_type": "Домашняя работа",
        "mood": "Отлично",
        "lesson_title": "Решение уравнений"
      }
    ],
    "classroom": "Корпус А Каб. 301, этаж 3",
    "lesson_id": "1001",
    "works": [5001],
    "lesson_number": 1,
    "lesson_status": "Проведён",
    "attendance": "Присутствовал",
    "is_important": True,
    "sent_date": "2025-05-20T14:00:00"
  }
]
```

#### Обработанный вывод (для периода)
```python
{
  "2025-05-21": [
    {
      "time": "08:30-09:15",
      "subject": "Математика",
      "homework": "Решить задачи 1-5 на стр. 45",
      "files": ["tasks.pdf (http://example.com/tasks.pdf)"],
      "title": "Решение уравнений",
      "teacher": "Иванов И.И.",
      "mark_details": [
        {
          "value": "5",
          "work_type": "Домашняя работа",
          "mood": "Отлично",
          "lesson_title": "Решение уравнений"
        }
      ],
      "classroom": "Корпус А Каб. 301, этаж 3",
      "lesson_id": "1001",
      "works": [5001],
      "lesson_number": 1,
      "lesson_status": "Проведён",
      "attendance": "Присутствовал",
      "is_important": True,
      "sent_date": "2025-05-20T14:00:00"
    }
  ],
  "2025-05-22": []
}
```

#### Примеры использования
1. **Вывод расписания на сегодня**:
   ```python
   from datetime import datetime

   today = datetime(2025, 5, 21)
   schedule = formatter.get_formatted_schedule(today)
   print("Расписание на сегодня:")
   for lesson in schedule:
       print(f"{lesson['time']} - {lesson['subject']}: {lesson['homework']}")
   ```

2. **Фильтрация важных заданий**:
   ```python
   from datetime import datetime, timedelta

   start_date = datetime(2025, 5, 21)
   end_date = start_date + timedelta(days=7)
   schedule = formatter.get_formatted_schedule(start_date, end_date)
   print("Важные задания:")
   for date, lessons in schedule.items():
       for lesson in lessons:
           if lesson["is_important"]:
               print(f"{date} - {lesson['subject']}: {lesson['homework']}")
   ```

3. **Экспорт в JSON**:
   ```python
   import json
   from datetime import datetime

   schedule = formatter.get_formatted_schedule(datetime(2025, 5, 21))
   with open("schedule.json", "w", encoding="utf-8") as f:
       json.dump(schedule, f, ensure_ascii=False, indent=2)
   ```

#### Нюансы
- **Кэширование**: Использует `_schedule_cache`. Очистите через `clear_schedule_cache()`.
- **Ошибки**:
  - `ValueError`: Если `end_date` раньше `start_date`.
  - Сетевые ошибки возвращают пустую структуру.
- **Ограничения**:
  - Зависит от `_subject_cache`, `_teacher_cache`.
  - Пустое расписание возвращает пустую структуру.
- **Рекомендации**:
  - Включайте `debug_mode=True` для диагностики.
  - Учитывайте лимиты API для больших периодов.

---

### 2. `get_last_marks`

#### Назначение
Возвращает последние оценки ученика с фильтрацией по предмету, включая предмет, тип работы, тему урока и распределение оценок в классе.

#### Синтаксис
```python
result = formatter.get_last_marks(count=5, subject_id=None)
```

#### Входные параметры
- **count** (`int`, по умолчанию `5`): Количество оценок.
  - **Описание**: Ограничивает число записей.
  - **Ограничения**: Положительное целое.
  - **Пример**: `3`.
- **subject_id** (`Optional[int]`, по умолчанию `None`): ID предмета.
  - **Описание**: Фильтр по предмету. Если `None`, все предметы.
  - **Ограничения**: Должен быть в `_subject_cache`.
  - **Пример**: `101` ("Математика").

#### Выходные данные
- **Тип**: `List[Dict[str, any]]`
- **Структура элемента**:
  - `subject` (`str`): Название предмета.
  - `work_type` (`str`): Тип работы.
  - `lesson_title` (`str`): Тема урока.
  - `mark` (`str`): Оценка.
  - `class_distribution` (`dict`): Распределение оценок `{оценка: количество}`.
  - `date` (`str`): Дата оценки (`DD.MM.YYYY`).

#### Обработанный вывод
```python
[
  {
    "subject": "Математика",
    "work_type": "Домашняя работа",
    "lesson_title": "Решение уравнений",
    "mark": "5",
    "class_distribution": {"5": 10, "4": 8, "3": 2},
    "date": "18.05.2025"
  },
  {
    "subject": "Русский язык",
    "work_type": "Контрольная работа",
    "lesson_title": "Синтаксис",
    "mark": "4",
    "class_distribution": {"5": 5, "4": 10, "3": 5},
    "date": "17.05.2025"
  }
]
```

#### Примеры использования
1. **Вывод последних оценок**:
   ```python
   marks = formatter.get_last_marks(count=3)
   print("Последние оценки:")
   for mark in marks:
       print(f"{mark['date']} - {mark['subject']}: {mark['mark']} ({mark['work_type']})")
   ```

2. **Фильтрация по предмету**:
   ```python
   math_marks = formatter.get_last_marks(count=5, subject_id=101)
   print("Оценки по математике:")
   for mark in math_marks:
       print(f"{mark['date']} - {mark['mark']} ({mark['lesson_title']})")
   ```

3. **Визуализация распределения**:
   ```python
   import matplotlib.pyplot as plt

   marks = formatter.get_last_marks(count=1)
   if marks:
       dist = marks[0]["class_distribution"]
       plt.bar(dist.keys(), dist.values())
       plt.title(f"Распределение оценок по {marks[0]['subject']}")
       plt.xlabel("Оценка")
       plt.ylabel("Количество")
       plt.savefig("mark_distribution.png")
   ```

#### Нюансы
- **Период**: Оценки за последние 90 дней.
- **Фильтрация**: Некорректный `subject_id` отключает фильтр.
- **Ошибки**:
  - Сетевые ошибки возвращают пустой список.
  - Ошибки гистограммы дают пустое `class_distribution`.
- **Ограничения**:
  - Зависит от `_lesson_cache`, `_work_types_cache`.
- **Рекомендации**:
  - Проверяйте `_subject_cache` для `subject_id`.
  - Используйте для мониторинга успеваемости.

---

### 3. `get_formatted_marks`

#### Назначение
Возвращает оценки за период, сгруппированные по предметам, с деталями: дата урока, дата оценки, тип работы, настроение, тема урока.

#### Синтаксис
```python
result = formatter.get_formatted_marks(start_date, end_date=None)
```

#### Входные параметры
- **start_date** (`datetime`): Начальная дата.
  - **Описание**: Начало периода.
  - **Ограничения**: Валидная `datetime`.
  - **Пример**: `datetime(2025, 5, 1)`.
- **end_date** (`Optional[datetime]`, по умолчанию `None`): Конечная дата.
  - **Описание**: Если `None`, используется `start_date`.
  - **Ограничения**: Не раньше `start_date`.
  - **Пример**: `datetime(2025, 5, 31)`.

#### Выходные данные
- **Тип**: `Dict[str, List[Dict[str, str]]]`
- **Структура**:
  - Ключи: названия предметов.
  - Значения: списки оценок:
    - `lesson_date` (`str`): Дата урока (`DD.MM.YYYY`).
    - `mark_date` (`str`): Дата оценки (`DD.MM.YYYY`).
    - `value` (`str`): Оценка.
    - `work_type` (`str`): Тип работы.
    - `mood` (`str`): Настроение.
    - `lesson_title` (`str`): Тема урока.

#### Обработанный вывод
```python
{
  "Математика": [
    {
      "lesson_date": "19.05.2025",
      "mark_date": "19.05.2025",
      "value": "5",
      "work_type": "Домашняя работа",
      "mood": "Отлично",
      "lesson_title": "Решение уравнений"
    }
  ],
  "Русский язык": []
}
```

#### Примеры использования
1. **Вывод оценок за день**:
   ```python
   from datetime import datetime

   start_date = datetime(2025, 5, 21)
   marks = formatter.get_formatted_marks(start_date)
   print("Оценки за день:")
   for subject, grades in marks.items():
       for grade in grades:
           print(f"{subject}: {grade['value']} ({grade['work_type']})")
   ```

2. **Средний балл за период**:
   ```python
   from datetime import datetime
   from statistics import mean

   start_date = datetime(2025, 5, 1)
   end_date = datetime(2025, 5, 31)
   marks = formatter.get_formatted_marks(start_date, end_date)
   for subject, grades in marks.items():
       numeric_grades = [int(g["value"]) for g in grades if g["value"].isdigit()]
       avg = mean(numeric_grades) if numeric_grades else "Нет оценок"
       print(f"{subject}: Средний балл = {avg}")
   ```

3. **Экспорт в CSV**:
   ```python
   import csv
   from datetime import datetime

   start_date = datetime(2025, 5, 1)
   marks = formatter.get_formatted_marks(start_date)
   with open("marks.csv", "w", encoding="utf-8", newline="") as f:
       writer = csv.DictWriter(f, fieldnames=["subject", "lesson_date", "mark_date", "value", "work_type", "lesson_title"])
       writer.writeheader()
       for subject, grades in marks.items():
           for grade in grades:
               writer.writerow({"subject": subject, **grade})
   ```

#### Нюансы
- **Фильтрация**: Оценки по дате урока.
- **Ошибки**:
  - `ValueError`: Если `end_date` раньше `start_date`.
  - Сетевые ошибки возвращают пустой словарь.
- **Ограничения**:
  - Зависит от `_subject_cache`, расписания.
  - Пустое расписание — пустой результат.
- **Рекомендации**:
  - Используйте небольшие периоды.
  - Проверяйте логи.

---

### 4. `get_formatted_final_marks`

#### Назначение
Получает итоговые оценки за четверть по предметам с уроками, включая список оценок и средний балл.

#### Синтаксис
```python
result = formatter.get_formatted_final_marks(study_year=None, quarter)
```

#### Входные параметры
- **study_year** (`Optional[int]`, по умолчанию `None`): Учебный год.
  - **Описание**: Год периода (например, 2025 для 2024-2025). Если `None`, выбирается текущий год.
  - **Ограничения**: Положительное целое.
  - **Пример**: `2025`.
- **quarter** (`int`): Номер четверти.
  - **Описание**: Четверть (1-4).
  - **Ограничения**: 1-4, иначе `ValueError`.
  - **Пример**: `3`.

#### Выходные данные
- **Тип**: `List[Dict[str, any]]`
- **Структура элемента**:
  - `название предмета` (`str`): Название предмета.
  - `оценки` (`list`): Список оценок.
  - `средний балл` (`str`): Средний балл (до 1 знака) или "Нет оценок"/"Нет данных".

#### Обработанный вывод
```python
[
  {
    "название предмета": "Математика",
    "оценки": ["5", "4", "5"],
    "средний балл": "4.7"
  },
  {
    "название предмета": "Русский язык",
    "оценки": [],
    "средний балл": "Нет оценок"
  }
]
```

#### Примеры использования
1. **Вывод итоговых оценок**:
   ```python
   marks = formatter.get_formatted_final_marks(study_year=2025, quarter=3)
   print("Итоговые оценки:")
   for subject in marks:
       print(f"{subject['название предмета']}: {subject['средний балл']}")
   ```

2. **Фильтрация предметов с оценками**:
   ```python
   marks = formatter.get_formatted_final_marks(study_year=2025, quarter=3)
   print("Предметы с оценками:")
   for subject in marks:
       if subject["оценки"]:
           print(f"{subject['название предмета']}: {subject['оценки']}")
   ```

3. **График средних баллов**:
   ```python
   import matplotlib.pyplot as plt

   marks = formatter.get_formatted_final_marks(study_year=2025, quarter=3)
   subjects = [s["название предмета"] for s in marks]
   averages = [float(s["средний балл"]) if s["средний балл"].replace(".", "").isdigit() else 0 for s in marks]
   plt.bar(subjects, averages)
   plt.title("Средние баллы за четверть")
   plt.xlabel("Предмет")
   plt.ylabel("Средний балл")
   plt.savefig("final_marks.png")
   ```

#### Нюансы
- **Фильтрация**: Только предметы с уроками.
- **Ошибки**:
  - `ValueError`: Если `quarter` не 1-4.
  - Сетевые ошибки возвращают пустой список.
- **Ограничения**:
  - Зависит от `_get_quarter_period_id`.
  - Средний балл для числовых оценок.
- **Рекомендации**:
  - Проверяйте логи.
  - Используйте для итогового анализа.

---

### 5. `get_group_teachers`

#### Назначение
Возвращает список учителей группы за период с информацией о предметах, контактах и должности.

#### Синтаксис
```python
result = formatter.get_group_teachers(start_date=None, end_date=None)
```

#### Входные параметры
- **start_date** (`Optional[datetime]`, по умолчанию `None`): Начальная дата.
  - **Описание**: Если `None`, текущая дата минус 7 дней.
  - **Ограничения**: Валидная `datetime`, если указана.
  - **Пример**: `datetime(2025, 5, 1)`.
- **end_date** (`Optional[datetime]`, по умолчанию `None`): Конечная дата.
  - **Описание**: Если `None`, текущая дата плюс 30 дней.
  - **Ограничения**: Не раньше `start_date`.
  - **Пример**: `datetime(2025, 5, 31)`.

#### Выходные данные
- **Тип**: `List[Dict[str, str]]`
- **Структура элемента**:
  - `id` (`str`): ID учителя.
  - `fullName` (`str`): Полное имя.
  - `shortName` (`str`): Краткое имя.
  - `subjects` (`str`): Предметы.
  - `email` (`str`): Email.
  - `position` (`str`): Должность.

#### Обработанный вывод
```python
[
  {
    "id": "201",
    "fullName": "Иванов Иван Иванович",
    "shortName": "Иванов И.И.",
    "subjects": "Математика",
    "email": "ivanov@example.com",
    "position": "Учитель"
  },
  {
    "id": "202",
    "fullName": "Петрова Анна Алексеевна",
    "shortName": "Петрова А.А.",
    "subjects": "Русский язык",
    "email": "",
    "position": "Учитель"
  }
]
```

#### Примеры использования
1. **Вывод учителей**:
   ```python
   from datetime import datetime

   teachers = formatter.get_group_teachers()
   print("Учителя группы:")
   for teacher in teachers:
       print(f"{teacher['fullName']} ({teacher['subjects']})")
   ```

2. **Фильтрация по предмету**:
   ```python
   from datetime import datetime

   start_date = datetime(2025, 5, 1)
   end_date = datetime(2025, 5, 31)
   teachers = formatter.get_group_teachers(start_date, end_date)
   math_teachers = [t for t in teachers if "Математика" in t["subjects"]]
   print("Учителя математики:")
   for teacher in math_teachers:
       print(f"{teacher['shortName']}: {teacher['email']}")
   ```

3. **Экспорт контактов**:
   ```python
   import json
   from datetime import datetime

   teachers = formatter.get_group_teachers(datetime(2025, 5, 1), datetime(2025, 5, 31))
   with open("teachers.json", "w", encoding="utf-8") as f:
       json.dump(teachers, f, ensure_ascii=False, indent=2)
   ```

#### Нюансы
- **Кэширование**: Использует `_teacher_cache`.
- **Ошибки**:
  - `ValueError`: Если `end_date` раньше `start_date`.
  - Сетевые ошибки возвращают пустой список.
- **Ограничения**:
  - Только учителя, привязанные к урокам.
  - Требуется `_teacher_cache`.
- **Рекомендации**:
  - Проверяйте логи.
  - Используйте для анализа преподавателей.

---

### 6. `get_class_ranking`

#### Назначение
Формирует рейтинг учеников класса по средней оценке за четверть.

#### Синтаксис
```python
result = formatter.get_class_ranking(study_year=None, quarter)
```

#### Входные параметры
- **study_year** (`Optional[int]`, по умолчанию `None`): Учебный год.
  - **Описание**: Год периода (например, 2025 для 2024-2025). Если `None`, выбирается текущий год.
  - **Ограничения**: Положительное целое.
  - **Пример**: `2025`.
- **quarter** (`int`): Номер четверти.
  - **Описание**: Четверть (1-4).
  - **Ограничения**: 1-4.
  - **Пример**: `3`.

#### Выходные данные
- **Тип**: `List[Dict]`
- **Структура элемента**:
  - `name` (`str`): Имя ученика.
  - `avg_grade` (`float`): Средний балл (до 2 знаков).
  - `marks_count` (`int`): Количество оценок.

#### Обработанный вывод
```python
[
  {
    "name": "Иванов Иван",
    "avg_grade": 4.5,
    "marks_count": 20
  },
  {
    "name": "Петров Пётр",
    "avg_grade": 4.0,
    "marks_count": 18
  }
]
```

#### Примеры использования
1. **Вывод рейтинга**:
   ```python
   ranking = formatter.get_class_ranking(study_year=2025, quarter=3)
   print("Рейтинг класса:")
   for student in ranking:
       print(f"{student['name']}: {student['avg_grade']} (оценок: {student['marks_count']})")
   ```

2. **Топ-3 ученика**:
   ```python
   ranking = formatter.get_class_ranking(study_year=2025, quarter=3)
   top_3 = sorted(ranking, key=lambda x: x["avg_grade"], reverse=True)[:3]
   print("Топ-3 ученика:")
   for student in top_3:
       print(f"{student['name']}: {student['avg_grade']}")
   ```

3. **Экспорт рейтинга**:
   ```python
   import csv

   ranking = formatter.get_class_ranking(study_year=2025, quarter=3)
   with open("ranking.csv", "w", encoding="utf-8", newline="") as f:
       writer = csv.DictWriter(f, fieldnames=["name", "avg_grade", "marks_count"])
       writer.writeheader()
       writer.writerows(ranking)
   ```

#### Нюансы
- **Фильтрация**: Только числовые оценки.
- **Ошибки**:
  - `ValueError`: Если `quarter` не 1-4.
  - Сетевые ошибки пропускаются.
- **Ограничения**:
  - Зависит от `_student_cache`, `_get_quarter_period_id`.
  - Нет оценок — `avg_grade` равен 0.
- **Рекомендации**:
  - Проверяйте `_student_cache`.
  - Используйте для анализа успеваемости.

---

### 7. `get_subject_stats`

#### Назначение
Возвращает гистограмму оценок по предмету за четверть для группы.

#### Синтаксис
```python
result = formatter.get_subject_stats(study_year=None, quarter, subject_id)
```

#### Входные параметры
- **study_year** (`Optional[int]`, по умолчанию `None`): Учебный год.
  - **Описание**: Год периода (например, 2025 для 2024-2025). Если `None`, выбирается текущий год.
  - **Ограничения**: Положительное целое.
  - **Пример**: `2025`.
- **quarter** (`int`): Номер четверти.
  - **Описание**: Четверть (1-4).
  - **Ограничения**: 1-4.
  - **Пример**: `3`.
- **subject_id** (`int`): ID предмета.
  - **Описание**: Идентификатор предмета.
  - **Ограничения**: В `_subject_cache`.
  - **Пример**: `101`.

#### Выходные данные
- **Тип**: `Dict[str, int]`
- **Структура**: Ключи — оценки, значения — количество.

#### Обработанный вывод
```python
{
  "5": 10,
  "4": 8,
  "3": 2
}
```

#### Примеры использования
1. **Вывод статистики**:
   ```python
   stats = formatter.get_subject_stats(study_year=2025, quarter=3, subject_id=101)
   print("Статистика по математике:")
   for grade, count in stats.items():
       print(f"Оценка {grade}: {count} раз")
   ```

2. **Визуализация гистограммы**:
   ```python
   import matplotlib.pyplot as plt

   stats = formatter.get_subject_stats(study_year=2025, quarter=3, subject_id=101)
   plt.bar(stats.keys(), stats.values())
   plt.title("Распределение оценок по математике")
   plt.xlabel("Оценка")
   plt.ylabel("Количество")
   plt.savefig("subject_stats.png")
   ```

3. **Сравнение предметов**:
   ```python
   subjects = {101: "Математика", 102: "Русский язык"}
   for subject_id, name in subjects.items():
       stats = formatter.get_subject_stats(study_year=2025, quarter=3, subject_id=subject_id)
       total = sum(stats.values())
       print(f"{name}: Всего оценок = {total}")
   ```

#### Нюансы
- **Ошибки**:
  - `ValueError`: Если `quarter` не 1-4.
  - Сетевые ошибки возвращают пустой словарь.
- **Ограничения**:
  - Зависит от `_get_quarter_period_id`.
  - Требуется валидный `subject_id`.
- **Рекомендации**:
  - Проверяйте `_subject_cache`.
  - Используйте для анализа оценок.

---

### 8. `get_subject_ranking`

#### Назначение
Формирует рейтинг учеников по среднему баллу за четверть по предмету.

#### Синтаксис
```python
result = formatter.get_subject_ranking(study_year=None, quarter, subject_id)
```

#### Входные параметры
- **study_year** (`Optional[int]`, по умолчанию `None`): Учебный год.
  - **Описание**: Год периода (например, 2025 для 2024-2025). Если `None`, выбирается текущий год.
  - **Ограничения**: Положительное целое.
  - **Пример**: `2025`.
- **quarter** (`int`): Номер четверти.
  - **Описание**: Четверть (1-4).
  - **Ограничения**: 1-4.
  - **Пример**: `3`.
- **subject_id** (`int`): ID предмета.
  - **Описание**: Идентификатор предмета.
  - **Ограничения**: В `_subject_cache`.
  - **Пример**: `101`.

#### Выходные данные
- **Тип**: `List[Dict]`
- **Структура элемента**:
  - `name` (`str`): Имя ученика.
  - `avg_grade` (`float`): Средний балл (до 2 знаков).
  - `marks_count` (`int`): Количество оценок.

#### Обработанный вывод
```python
[
  {
    "name": "Иванов Иван",
    "avg_grade": 4.5,
    "marks_count": 5
  },
  {
    "name": "Петров Пётр",
    "avg_grade": 4.0,
    "marks_count": 4
  }
]
```

#### Примеры использования
1. **Вывод рейтинга**:
   ```python
   ranking = formatter.get_subject_ranking(study_year=2025, quarter=3, subject_id=101)
   print("Рейтинг по математике:")
   for student in ranking:
       print(f"{student['name']}: {student['avg_grade']}")
   ```

2. **Топ-5 учеников**:
   ```python
   ranking = formatter.get_subject_ranking(study_year=2025, quarter=3, subject_id=101)
   top_5 = sorted(ranking, key=lambda x: x["avg_grade"], reverse=True)[:5]
   print("Топ-5 по математике:")
   for student in top_5:
       print(f"{student['name']}: {student['avg_grade']}")
   ```

3. **Экспорт рейтинга**:
   ```python
   import json

   ranking = formatter.get_subject_ranking(study_year=2025, quarter=3, subject_id=101)
   with open("subject_ranking.json", "w", encoding="utf-8") as f:
       json.dump(ranking, f, ensure_ascii=False, indent=2)
   ```

#### Нюансы
- **Кэш**: Если `_student_cache` пуст, загружает данные.
- **Ошибки**:
  - `ValueError`: Если `quarter` не 1-4.
  - Сетевые ошибки пропускаются.
- **Ограничения**:
  - Требуется валидный `subject_id`.
  - Нет оценок — `avg_grade` равен 0.
- **Рекомендации**:
  - Проверяйте `_subject_cache`, `_student_cache`.
  - Используйте для анализа успеваемости.

---

### 9. `get_upcoming_tests`

#### Назначение
Возвращает список предстоящих тестов, включая контрольные работы, с датой, предметом, типом работы, весом и описанием.

#### Синтаксис
```python
result = formatter.get_upcoming_tests()
```

#### Входные параметры
- Нет параметров.

#### Выходные данные
- **Тип**: `List[Dict[str, any]]`
- **Структура элемента**:
  - `date` (`str`): Дата теста (`DD.MM.YYYY`).
  - `subject` (`str`): Название предмета.
  - `work_type` (`str`): Тип работы (например, "Контрольная", "Тест").
  - `weight` (`int`): Вес работы.
  - `description` (`str`): Описание теста.

#### Обработанный вывод
```python
[
  {
    "date": "25.05.2025",
    "subject": "Математика",
    "work_type": "Контрольная",
    "weight": 2,
    "description": "Контрольная по геометрии"
  },
  {
    "date": "27.05.2025",
    "subject": "Физика",
    "work_type": "Тест",
    "weight": 1,
    "description": "Тест по механике"
  }
]
```

#### Примеры использования
1. **Вывод тестов**:
   ```python
   tests = formatter.get_upcoming_tests()
   print("Предстоящие тесты:")
   for test in tests:
       print(f"{test['date']} - {test['subject']}: {test['description']}")
   ```

2. **Фильтрация контрольных работ**:
   ```python
   tests = formatter.get_upcoming_tests()
   print("Контрольные работы:")
   for test in tests:
       if test["work_type"] == "Контрольная":
           print(f"{test['date']} - {test['subject']}: {test['description']} (вес {test['weight']})")
   ```

3. **Экспорт тестов**:
   ```python
   import json

   tests = formatter.get_upcoming_tests()
   with open("tests.json", "w", encoding="utf-8") as f:
       json.dump(tests, f, ensure_ascii=False, indent=2)
   ```

#### Нюансы
- **Период**: Тесты за ближайшие 30 дней.
- **Ошибки**:
  - Сетевые ошибки возвращают пустой список и логируются.
- **Ограничения**:
  - Зависит от `_lesson_cache`, `_subject_cache`.
  - Только работы, помеченные как тесты или контрольные.
- **Рекомендации**:
  - Проверяйте логи в `bot.log`.
  - Используйте для планирования подготовки.

---

### 10. `analyze_data`

#### Назначение
Выполняет ИИ-анализ данных (расписания, оценок, рейтинга) с использованием DeepSeek через OpenRouter, предоставляя рекомендации.

#### Синтаксис
```python
result = formatter.analyze_data(type, start_date=None, end_date=None, quarter=None, study_year=None)
```

#### Входные параметры
- **type** (`str`): Тип анализа.
  - **Описание**: `weeks` (расписание), `marks` (оценки), `ranking` (рейтинг).
  - **Ограничения**: Должен быть в `prompts.json`.
  - **Пример**: `"marks"`.
- **start_date** (`Optional[datetime]`, по умолчанию `None`): Начальная дата (для `weeks`, `marks`).
  - **Пример**: `datetime(2025, 5, 1)`.
- **end_date** (`Optional[datetime]`, по умолчанию `None`): Конечная дата (для `weeks`, `marks`).
  - **Пример**: `datetime(2025, 5, 31)`.
- **quarter** (`Optional[int]`, по умолчанию `None`): Номер четверти (для `ranking`).
  - **Пример**: `3`.
- **study_year** (`Optional[int]`, по умолчанию `None`): Учебный год (для `ranking`).
  - **Пример**: `2025`.

#### Выходные данные
- **Тип**: `str`
- **Описание**: Человекочитаемый результат анализа.

#### Обработанный вывод
```python
"Ваши оценки за май 2025 показывают сильные результаты по математике (средний балл 4.8), но по литературе есть пробелы (средний балл 3.5). Рекомендуется уделить больше времени анализу текстов."
```

#### Примеры использования
1. **Анализ оценок**:
   ```python
   from datetime import datetime

   result = formatter.analyze_data(type="marks", start_date=datetime(2025, 5, 1), end_date=datetime(2025, 5, 31))
   print("Анализ оценок:")
   print(result)
   ```

2. **Анализ расписания**:
   ```python
   from datetime import datetime

   result = formatter.analyze_data(type="weeks", start_date=datetime(2025, 5, 21), end_date=datetime(2025, 5, 28))
   print("Анализ расписания:")
   print(result)
   ```

3. **Анализ рейтинга**:
   ```python
   result = formatter.analyze_data(type="ranking", quarter=3, study_year=2025)
   print("Анализ рейтинга:")
   print(result)
   ```

#### Нюансы
- **Зависимости**: Требует `prompts.json` и `OPENROUTER_API_KEY`.
- **Ошибки**:
  - Сетевые ошибки возвращают сообщение об ошибке и логируются.
  - Отсутствие промпта вызывает `ValueError`.
- **Ограничения**:
  - Зависит от внешнего API OpenRouter.
  - Увеличивает задержки из-за сетевых запросов.
- **Рекомендации**:
  - Проверяйте наличие `prompts.json` и API-ключа.
  - Используйте для стратегического планирования.

---

## Внутренние методы класса

Ниже описаны внутренние методы, начинающиеся с `_`, которые используются основными методами для выполнения запросов к API, обработки данных и управления кэшем. Эти методы не предназначены для прямого вызова разработчиком, но их понимание полезно для отладки и расширения функциональности.

### 1. `_get_schedule`

#### Назначение
Запрашивает данные расписания за указанный период через API Дневник.ру и сохраняет их в `_schedule_cache`.

#### Синтаксис
```python
result = formatter._get_schedule(start_date, end_date)
```

#### Входные параметры
- **start_date** (`datetime`): Начальная дата.
  - **Описание**: Дата начала периода.
  - **Ограничения**: Валидная `datetime`.
  - **Пример**: `datetime(2025, 5, 21)`.
- **end_date** (`datetime`): Конечная дата.
  - **Описание**: Дата окончания периода.
  - **Ограничения**: Не раньше `start_date`.
  - **Пример**: `datetime(2025, 5, 28)`.

#### Выходные данные
- **Тип**: `Dict[str, Dict]`
- **Описание**: Словарь, где ключи — даты в формате `YYYY-MM-DD`, а значения — словари с данными уроков, предметов, учителей, домашних заданий, оценок и посещаемости.

#### Контекст использования
- Вызывается методом `get_formatted_schedule` для получения данных перед их форматированием.
- Использует API-запрос для загрузки расписания, если данные отсутствуют в `_schedule_cache`.
- Логирует запросы и ошибки в `debug_mode`.

#### Нюансы
- **Кэширование**: Сохраняет данные в `_schedule_cache` для повторного использования.
- **Ошибки**:
  - Сетевые ошибки возвращают пустой словарь с логированием.
  - Некорректные даты вызывают `ValueError`.
- **Ограничения**: Зависит от структуры API и токена.
- **Рекомендации**: Используйте `debug_mode=True` для проверки сырых данных.

---

### 2. `_get_marks`

#### Назначение
Запрашивает данные об оценках за указанный период через API и кэширует их.

#### Синтаксис
```python
result = formatter._get_marks(start_date, end_date)
```

#### Входные параметры
- **start_date** (`datetime`): Начальная дата.
  - **Описание**: Дата начала периода.
  - **Ограничения**: Валидная `datetime`.
  - **Пример**: `datetime(2025, 5, 1)`.
- **end_date** (`datetime`): Конечная дата.
  - **Описание**: Дата окончания периода.
  - **Ограничения**: Не раньше `start_date`.
  - **Пример**: `datetime(2025, 5, 31)`.

#### Выходные данные
- **Тип**: `List[Dict]`
- **Описание**: Список словарей, содержащих информацию об оценках: ID урока, работы, значение, дата, тип работы, настроение.

#### Контекст использования
- Используется методами `get_last_marks`, `get_formatted_marks` для получения данных об оценках.
- Выполняет API-запрос, если данные отсутствуют в кэше.
- Логирует запросы и ошибки.

#### Нюансы
- **Кэширование**: Сохраняет данные в `_marks_cache`.
- **Ошибки**:
  - Сетевые ошибки возвращают пустой список.
  - Некорректные даты вызывают `ValueError`.
- **Ограничения**: Зависит от `_lesson_cache` для связи оценок с уроками.
- **Рекомендации**: Проверяйте логи для диагностики.

---

### 3. `_get_quarter_period_id`

#### Назначение
Определяет ID периода для указанной четверти и учебного года.

#### Синтаксис
```python
result = formatter._get_quarter_period_id(study_year, quarter)
```

#### Входные параметры
- **study_year** (`Optional[int]`, по умолчанию `None`): Учебный год.
  - **Описание**: Год периода (например, 2025 для 2024-2025). Если `None`, выбирается текущий год.
  - **Ограничения**: Положительное целое.
  - **Пример**: `2025`.
- **quarter** (`int`): Номер четверти.
  - **Описание**: Четверть (1-4).
  - **Ограничения**: 1-4.
  - **Пример**: `3`.

#### Выходные данные
- **Тип**: `str`
- **Описание**: ID периода четверти (например, "2024-2025-Q3").

#### Контекст использования
- Используется методами `get_formatted_final_marks`, `get_class_ranking`, `get_subject_stats`, `get_subject_ranking` для определения периода.
- Запрашивает данные о периодах через API, если кэш пуст.
- Логирует ошибки.

#### Нюансы
- **Кэширование**: Сохраняет данные в `_period_cache`.
- **Ошибки**:
  - `ValueError`: Если `quarter` не 1-4.
  - Сетевые ошибки возвращают `None`.
- **Ограничения**: Зависит от API и структуры периодов.
- **Рекомендации**: Проверяйте логи при пустом результате.

---

### 4. `_load_caches`

#### Назначение
Инициализирует кэши (`_subject_cache`, `_student_cache`, `_teacher_cache`, `_work_types_cache`) при создании объекта класса.

#### Синтаксис
```python
formatter._load_caches()
```

#### Входные параметры
- Нет параметров.

#### Выходные данные
- **Тип**: `None`
- **Описание**: Заполняет внутренние кэши данными из API.

#### Контекст использования
- Вызывается автоматически при инициализации `DnevnikFormatter`.
- Загружает данные о предметах, учениках, учителях и типах работ.
- Логирует процесс загрузки.

#### Нюансы
- **Ошибки**:
  - Сетевые ошибки логируются, но не прерывают инициализацию.
  - Пустые кэши могут повлиять на методы.
- **Ограничения**: Зависит от токена и API.
- **Рекомендации**: Проверяйте логи для проверки загрузки.

---

### 5. `_parse_date`

#### Назначение
Парсит строку даты из API в объект `datetime`.

#### Синтаксис
```python
result = formatter._parse_date(date_str)
```

#### Входные параметры
- **date_str** (`str`): Строка даты.
  - **Описание**: Дата в формате API (например, "2025-05-21T00:00:00" или "2025-05-21T00:00:00.000000").
  - **Ограничения**: Должна быть валидной.
  - **Пример**: `"2025-05-21T14:00:00"`.

#### Выходные данные
- **Тип**: `datetime`
- **Описание**: Объект `datetime`, представляющий дату.

#### Контекст использования
- Используется всеми методами, работающими с датами, для обработки строк дат из API.
- Поддерживает два формата: `%Y-%m-%dT%H:%M:%S` и `%Y-%m-%dT%H:%M:%S.%f`.

#### Нюансы
- **Ошибки**: Некорректные строки возвращают `None` с логированием.
- **Ограничения**: Ограничено поддерживаемыми форматами.
- **Рекомендации**: Проверяйте логи при проблемах с датами.

---

### 6. `_format_lesson`

#### Назначение
Форматирует данные урока в структурированный вид для метода `get_formatted_schedule`.

#### Синтаксис
```python
result = formatter._format_lesson(lesson_data, date)
```

#### Входные параметры
- **lesson_data** (`Dict`): Данные урока.
  - **Описание**: Словарь с информацией об уроке (ID, предмет, учитель, время, домашнее задание, оценки).
  - **Пример**: `{"id": 1001, "subject_id": 101, "hours": "08:30-09:15", ...}`.
- **date** (`str`): Дата урока.
  - **Описание**: Дата в формате `YYYY-MM-DD`.
  - **Пример**: `"2025-05-21"`.

#### Выходные данные
- **Тип**: `Dict[str, any]`
- **Описание**: Форматированный словарь урока, соответствующий структуре `get_formatted_schedule`.

#### Контекст использования
- Вызывается в `get_formatted_schedule` для преобразования сырых данных в конечный формат.
- Использует `_subject_cache`, `_teacher_cache`, `_work_types_cache`.

#### Нюансы
- **Ошибки**: Отсутствие данных в кэшах пропускается с логированием.
- **Ограничения**: Зависит от корректности входных данных.
- **Рекомендации**: Проверяйте кэши перед вызовом.

---

### 7. `_get_histogram`

#### Назначение
Запрашивает гистограмму оценок для работы через API.

#### Синтаксис
```python
result = formatter._get_histogram(work_id)
```

#### Входные параметры
- **work_id** (`int`): ID работы.
  - **Описание**: Идентификатор работы, для которой нужна гистограмма.
  - **Ограничения**: Должен быть валидным.
  - **Пример**: `5001`.

#### Выходные данные
- **Тип**: `Dict[str, int]`
- **Описание**: Словарь, где ключи — оценки, значения — их количество.

#### Контекст использования
- Используется в `get_last_marks`, `get_subject_stats` для получения распределения оценок.
- Логирует запросы и ошибки.

#### Нюансы
- **Ошибки**: Сетевые ошибки возвращают пустой словарь.
- **Ограничения**: Зависит от API.
- **Рекомендации**: Проверяйте логи.

---

## Общие рекомендации

### Обработка ошибок
- **Сетевые ошибки**: Все методы возвращают пустые структуры (`[]`, `{}`) при сбоях API и логируют ошибки в `bot.log`.
- **Параметры**:
  - Проверяйте `quarter` (1-4), `subject_id` (в `_subject_cache`), даты (`end_date` не раньше `start_date`).
  - Некорректные параметры вызывают `ValueError`.
- **Логи**: Используйте `debug_mode=True` для диагностики, проверяйте `bot.log` (формат: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`).

### Оптимизация
- **Кэширование**: Используйте `_schedule_cache`, `_subject_cache`, `_teacher_cache`, `_work_types_cache` для минимизации запросов. Очищайте через `clear_schedule_cache()` при необходимости.
- **Лимиты API**: Разбивайте большие периоды на меньшие для избежания ограничений:
  ```python
  from datetime import datetime, timedelta

  def get_schedule_chunks(formatter, start_date, end_date, chunk_days=7):
      result = {}
      current = start_date
      while current <= end_date:
          chunk_end = min(current + timedelta(days=chunk_days - 1), end_date)
          chunk = formatter.get_formatted_schedule(current, chunk_end)
          result.update(chunk)
          current = chunk_end + timedelta(days=1)
      return result
  ```
- **Обновления**: Перезагружайте кэши при смене учебного года или группы.
- **ИИ-анализ**: Используйте `analyze_data` для стратегического планирования, но учитывайте задержки из-за внешнего API.

### Ограничения
- **Зависимость от API**: Требуется стабильный доступ к Дневник.ру.
- **Кэширование**: Устаревшие кэши могут дать некорректные результаты.
- **Язык**: Названия предметов и работ на русском.
- **ИИ-анализ**: Зависит от OpenRouter, требует `prompts.json` и `OPENROUTER_API_KEY`.
- **Контрольные работы**: Данные о тестах ограничены ближайшими 30 днями.

### Пример интеграции
Создание отчета для Telegram-бота:
```python
from DnevnikFormatter import DnevnikFormatter
from datetime import datetime, timedelta
import json

# Инициализация
token = "FDSf234refd23fdf232"
formatter = DnevnikFormatter(token=token, debug_mode=True)

try:
    # Расписание на неделю
    start_date = datetime(2025, 5, 21)
    end_date = start_date + timedelta(days=7)
    schedule = formatter.get_formatted_schedule(start_date, end_date)
    response = "📅 Расписание:\n"
    for date, lessons in schedule.items():
        response += f"\n{date}:\n"
        for lesson in lessons:
            response += f"• {lesson['time']} - {lesson['subject']}: {lesson['homework']}\n"

    # Предстоящие тесты
    tests = formatter.get_upcoming_tests()
    response += "\n📝 Контрольные работы:\n"
    for test in tests:
        if test["work_type"] == "Контрольная":
            response += f"• {test['date']} - {test['subject']}: {test['description']}\n"

    # ИИ-анализ оценок
    analysis = formatter.analyze_data(type="marks", start_date=start_date, end_date=end_date)
    response += f"\n🤖 ИИ-анализ:\n{analysis}"

    # Экспорт
    with open("report.json", "w", encoding="utf-8") as f:
        json.dump({"schedule": schedule, "tests": tests, "analysis": analysis}, f, ensure_ascii=False, indent=2)
    print(response[:4000])

except ValueError as e:
    print(f"Ошибка параметров: {e}")
except Exception as e:
    print(f"Ошибка API: {e}")
```

### Визуализация
График тестов по предметам:
```python
import matplotlib.pyplot as plt
from datetime import datetime

tests = formatter.get_upcoming_tests()
subjects = [test["subject"] for test in tests]
plt.hist(subjects, bins=len(set(subjects)))
plt.title("Предстоящие тесты по предметам")
plt.xlabel("Предмет")
plt.ylabel("Количество тестов")
plt.savefig("tests_per_subject.png")
```

## Заключение
`DnevnikFormatter` упрощает работу с данными Дневник.ру, предоставляя структурированные результаты для расписания, оценок, тестов и рейтингов. Новые функции, такие как `get_upcoming_tests` и `analyze_data`, позволяют планировать подготовку к контрольным работам и получать рекомендации от ИИ. Используйте примеры кода и внутренние методы для отладки и расширения. Для диагностики включайте `debug_mode=True` и проверяйте `bot.log`.

Для доработок или вопросов обратитесь к разработчику: [Telegram](https://t.me/Sirop1).
