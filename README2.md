# Полная документация к классу `DnevnikFormatterAsync`

## Общее описание

`DnevnikFormatterAsync` — это асинхронный Python-класс для обработки данных, получаемых через API Дневник.ру, предназначенный для разработчиков, интегрирующих информацию об учебном процессе в свои приложения, такие как Telegram-боты или веб-сервисы. Класс предоставляет структурированные данные о расписании, оценках, учителях, тестах и статистике класса, оптимизируя запросы через кэширование и упрощая асинхронное взаимодействие с API.

### Основные возможности
- Получение расписания уроков за день или период с деталями (время, предмет, домашние задания, тесты).
- Извлечение последних оценок с фильтрацией по предмету и распределением по классу.
- Формирование оценок за период, сгруппированных по предметам.
- Получение итоговых оценок за четверть с вычислением среднего балла.
- Список учителей группы с информацией о предметах и контактах.
- Формирование рейтингов учеников класса или по предмету.
- Статистика по предметам и классу (распределение оценок, средний балл).
- Получение списка предстоящих тестов с описанием и весом.

### Требования
- **Python**: Версия 3.8 или выше (рекомендуется 3.10+ для лучшей поддержки асинхронности).
- **Библиотеки**:
  - `pydnevnikruapi==2.1.3` — для асинхронной работы с API Дневник.ру.
  - `aiofiles==24.1.0` — для асинхронного чтения файлов (например, `prompts.json`).
  - `python-dateutil==2.9.0.post0` — для работы с датами.
  - `openai==1.47.1` — для AI-анализа через DeepSeek (опционально).
  - Встроенные модули: `asyncio`, `datetime`, `json`, `typing`, `collections`, `logging`.
- **Токен API**: Действующий токен авторизации от Дневник.ру.
- **Файл `prompts.json`**: Для AI-анализа (опционально, если используется `analyze_data`).
- **Переменная окружения `OPENROUTER_API_KEY`**: Для доступа к OpenRouter (опционально).
- **Доступ к интернету**: Для выполнения запросов к API.

### Установка и настройка
1. Установите Python (рекомендуется 3.10+).
2. Установите необходимые библиотеки:
   ```bash
   pip install pydnevnikruapi==2.1.3 aiofiles==24.1.0 python-dateutil==2.9.0.post0 openai==1.47.1
   ```
3. Получите токен API:
   - Зарегистрируйтесь на платформе Дневник.ру.
   - Обратитесь к документации `pydnevnikruapi` или поддержке Дневник.ру для получения токена (например, `XNI7zDmpyIUfpHXWurdK8QDbAqmwLaqg`).
4. (Опционально) Настройте AI-анализ:
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
   from DnevnikFormatterAsync import DnevnikFormatter
   from datetime import datetime
   ```

### Инициализация класса
Класс инициализируется с токеном API и параметром отладки. Инициализация асинхронная и требует вызова метода `initialize`.

#### Синтаксис
```python
formatter = DnevnikFormatter(token, debug_mode=True)
await formatter.initialize()
```

#### Параметры
- **token** (`str`): Токен авторизации API.
  - **Пример**: `"XNI7zDmpyIUfpHXWurdK8QDbAqmwLaqg"`.
  - **Ограничения**: Должен быть действительным, иначе вызывается `ValueError`.
- **debug_mode** (`bool`, по умолчанию `True`): Включает отладочные сообщения.
  - **Описание**: Выводит логи запросов, ошибок и состояния кэшей в `bot.log` и консоль.
  - **Пример**: `False` для продакшена.

#### Пример инициализации
```python
import asyncio
from DnevnikFormatterAsync import DnevnikFormatter
from datetime import datetime

async def main():
    # Инициализация
    token = "XNI7zDmpyIUfpHXWurdK8QDbAqmwLaqg"
    formatter = DnevnikFormatter(token=token, debug_mode=True)
    await formatter.initialize()

    # Проверка
    print(f"ID пользователя: {formatter.person_id}")

if __name__ == "__main__":
    asyncio.run(main())
```

#### Нюансы
- **Кэширование**: При вызове `initialize` загружаются кэши (`_subject_cache`, `_teacher_cache`).
- **Ошибки**:
  - `ValueError`: Недействительный токен или отсутствие API-ключа OpenRouter (если требуется).
  - Сетевые ошибки API логируются и перебрасываются.
- **Отладка**: `debug_mode=True` выводит подробные логи, полезные для диагностики.
- **Асинхронность**: Все методы используют `async/await`, требуя асинхронного контекста.

---

## Основные методы класса

Ниже описаны девять основных асинхронных методов с обработанным выводом и примерами использования. Все методы возвращают структурированные данные и безопасно обрабатывают ошибки, возвращая пустые структуры при сбоях.

### 1. `get_formatted_schedule`

#### Назначение
Получает расписание уроков за одну дату или период с деталями: время, предмет, домашнее задание, учитель, тесты, место проведения.

#### Синтаксис
```python
result = await formatter.get_formatted_schedule(start_date, end_date=None)
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
  - `time` (`str`): Время урока (например, `08:30–09:15`).
  - `subject` (`str`): Название предмета.
  - `homework` (`str`): Домашнее задание.
  - `files` (`list`): Файлы задания (имя и URL).
  - `title` (`str`): Тема урока.
  - `teacher` (`str`): Имя учителя.
  - `works` (`list`): Тесты/работы (`work: str`, `weight: int`).
  - `place` (`str`): Место проведения (кабинет).
  - `lesson_id` (`str`): ID урока.
  - `lesson_number` (`int`): Номер урока.
  - `lesson_status` (`str`): Статус урока.
  - `attendance` (`str`): Посещаемость.
  - `is_important` (`bool`): Важность задания.
  - `sent_date` (`str`): Дата отправки задания (`DD.MM.YYYY HH:MM`).

#### Обработанный вывод (для одной даты)
```python
[
  {
    "time": "08:30–09:15",
    "subject": "Математика",
    "homework": "Решить задачи 1-5 на стр. 45",
    "files": ["tasks.pdf (http://dnevnik.ru/tasks.pdf)"],
    "title": "Решение уравнений",
    "teacher": "Иванов И.И.",
    "works": [
      {
        "work": "Контрольная по уравнениям",
        "weight": 2
      }
    ],
    "place": "Кабинет 301",
    "lesson_id": "1001",
    "lesson_number": 1,
    "lesson_status": "Проведён",
    "attendance": "Присутствовал",
    "is_important": True,
    "sent_date": "20.05.2025 14:00"
  }
]
```

#### Обработанный вывод (для периода)
```python
{
  "21.05.2025": [
    {
      "time": "08:30–09:15",
      "subject": "Математика",
      "homework": "Решить задачи 1-5 на стр. 45",
      "files": ["tasks.pdf (http://dnevnik.ru/tasks.pdf)"],
      "title": "Решение уравнений",
      "teacher": "Иванов И.И.",
      "works": [
        {
          "work": "Контрольная по уравнениям",
          "weight": 2
        }
      ],
      "place": "Кабинет 301",
      "lesson_id": "1001",
      "lesson_number": 1,
      "lesson_status": "Проведён",
      "attendance": "Присутствовал",
      "is_important": True,
      "sent_date": "20.05.2025 14:00"
    }
  ],
  "22.05.2025": []
}
```

#### Примеры использования
1. **Вывод расписания на сегодня**:
   ```python
   import asyncio
   from datetime import datetime

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       today = datetime(2025, 5, 21)
       schedule = await formatter.get_formatted_schedule(today)
       print("Расписание на сегодня:")
       for lesson in schedule:
           print(f"{lesson['time']} - {lesson['subject']}: {lesson['homework']}")

   asyncio.run(main())
   ```

2. **Фильтрация тестов**:
   ```python
   import asyncio
   from datetime import datetime, timedelta

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       start_date = datetime(2025, 5, 21)
       end_date = start_date + timedelta(days=7)
       schedule = await formatter.get_formatted_schedule(start_date, end_date)
       print("Предстоящие тесты:")
       for date, lessons in schedule.items():
           for lesson in lessons:
               if lesson["works"]:
                   for work in lesson["works"]:
                       print(f"{date} - {lesson['subject']}: {work['work']} (вес {work['weight']})")

   asyncio.run(main())
   ```

3. **Экспорт в JSON**:
   ```python
   import asyncio
   import json
   from datetime import datetime

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       schedule = await formatter.get_formatted_schedule(datetime(2025, 5, 21))
       with open("schedule.json", "w", encoding="utf-8") as f:
           json.dump(schedule, f, ensure_ascii=False, indent=2)

   asyncio.run(main())
   ```

#### Нюансы
- **Кэширование**: Использует `_lesson_cache`. Очистите через `_clear_lesson_cache`.
- **Ошибки**:
  - `ValueError`: Если `end_date` раньше `start_date`.
  - Сетевые ошибки возвращают пустую структуру и логируются в `bot.log`.
- **Ограничения**:
  - Зависит от `_subject_cache`, `_teacher_cache`.
  - Пустое расписание возвращает пустую структуру.
- **Рекомендации**:
  - Включайте `debug_mode=True` для диагностики.
  - Разбивайте большие периоды для избежания лимитов API.

---

### 2. `get_last_marks`

#### Назначение
Возвращает последние оценки ученика с фильтрацией по предмету, включая предмет, тип работы, тему урока и распределение оценок в классе.

#### Синтаксис
```python
result = await formatter.get_last_marks(count=5, subject_id=None)
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
  - `mark` (`str`): Оценка (например, `5`, `Н`).
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
   import asyncio

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       marks = await formatter.get_last_marks(count=3)
       print("Последние оценки:")
       for mark in marks:
           print(f"{mark['date']} - {mark['subject']}: {mark['mark']} ({mark['work_type']})")

   asyncio.run(main())
   ```

2. **Фильтрация по предмету**:
   ```python
   import asyncio

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       math_marks = await formatter.get_last_marks(count=5, subject_id=101)
       print("Оценки по математике:")
       for mark in math_marks:
           print(f"{mark['date']} - {mark['mark']} ({mark['lesson_title']})")

   asyncio.run(main())
   ```

3. **Визуализация распределения**:
   ```python
   import asyncio
   import matplotlib.pyplot as plt

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       marks = await formatter.get_last_marks(count=1)
       if marks:
           dist = marks[0]["class_distribution"]
           plt.bar(dist.keys(), dist.values())
           plt.title(f"Распределение оценок по {marks[0]['subject']}")
           plt.xlabel("Оценка")
           plt.ylabel("Количество")
           plt.savefig("mark_distribution.png")

   asyncio.run(main())
   ```

#### Нюансы
- **Период**: Оценки за последние 90 дней (настраивается в API).
- **Фильтрация**: Некорректный `subject_id` отключает фильтр.
- **Ошибки**:
  - Сетевые ошибки возвращают пустой список и логируются.
  - Ошибки гистограммы дают пустое `class_distribution`.
- **Ограничения**:
  - Зависит от `_lesson_cache`.
- **Рекомендации**:
  - Проверяйте `_subject_cache` для `subject_id`.
  - Используйте для мониторинга успеваемости.

---

### 3. `get_formatted_marks`

#### Назначение
Возвращает оценки за период, сгруппированные по предметам, с деталями: дата урока, дата оценки, тип работы, настроение, тема урока.

#### Синтаксис
```python
result = await formatter.get_formatted_marks(start_date, end_date=None)
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
   import asyncio
   from datetime import datetime

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       start_date = datetime(2025, 5, 21)
       marks = await formatter.get_formatted_marks(start_date)
       print("Оценки за день:")
       for subject, grades in marks.items():
           for grade in grades:
               print(f"{subject}: {grade['value']} ({grade['work_type']})")

   asyncio.run(main())
   ```

2. **Средний балл за период**:
   ```python
   import asyncio
   from datetime import datetime
   from statistics import mean

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       start_date = datetime(2025, 5, 1)
       end_date = datetime(2025, 5, 31)
       marks = await formatter.get_formatted_marks(start_date, end_date)
       for subject, grades in marks.items():
           numeric_grades = [int(g["value"]) for g in grades if g["value"].isdigit()]
           avg = mean(numeric_grades) if numeric_grades else "Нет оценок"
           print(f"{subject}: Средний балл = {avg}")

   asyncio.run(main())
   ```

3. **Экспорт в CSV**:
   ```python
   import asyncio
   import csv
   from datetime import datetime

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       start_date = datetime(2025, 5, 1)
       marks = await formatter.get_formatted_marks(start_date)
       with open("marks.csv", "w", encoding="utf-8", newline="") as f:
           writer = csv.DictWriter(f, fieldnames=["subject", "lesson_date", "mark_date", "value", "work_type", "lesson_title"])
           writer.writeheader()
           for subject, grades in marks.items():
               for grade in grades:
                   writer.writerow({"subject": subject, **grade})

   asyncio.run(main())
   ```

#### Нюансы
- **Фильтрация**: Оценки по дате урока.
- **Ошибки**:
  - `ValueError`: Если `end_date` раньше `start_date`.
  - Сетевые ошибки возвращают пустой словарь и логируются.
- **Ограничения**:
  - Зависит от `_subject_cache`, `_lesson_cache`.
  - Пустое расписание — пустой результат.
- **Рекомендации**:
  - Используйте небольшие периоды.
  - Проверяйте логи в `bot.log`.

---

### 4. `get_formatted_final_marks`

#### Назначение
Получает итоговые оценки за четверть по предметам, включая список оценок и средний балл.

#### Синтаксис
```python
result = await formatter.get_formatted_final_marks(quarter, study_year=None)
```

#### Входные параметры
- **quarter** (`int`): Номер четверти.
  - **Описание**: Четверть (1–4).
  - **Ограничения**: 1–4, иначе `ValueError`.
  - **Пример**: `3`.
- **study_year** (`Optional[int]`, по умолчанию `None`): Учебный год.
  - **Описание**: Год периода (например, 2025). Если `None`, текущий год.
  - **Ограничения**: Положительное целое.
  - **Пример**: `2025`.

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
   import asyncio

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       marks = await formatter.get_formatted_final_marks(quarter=3, study_year=2025)
       print("Итоговые оценки:")
       for subject in marks:
           print(f"{subject['название предмета']}: {subject['средний балл']}")

   asyncio.run(main())
   ```

2. **Фильтрация предметов с оценками**:
   ```python
   import asyncio

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       marks = await formatter.get_formatted_final_marks(quarter=3, study_year=2025)
       print("Предметы с оценками:")
       for subject in marks:
           if subject["оценки"]:
               print(f"{subject['название предмета']}: {subject['оценки']}")

   asyncio.run(main())
   ```

3. **График средних баллов**:
   ```python
   import asyncio
   import matplotlib.pyplot as plt

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       marks = await formatter.get_formatted_final_marks(quarter=3, study_year=2025)
       subjects = [s["название предмета"] for s in marks]
       averages = [float(s["средний балл"]) if s["средний балл"].replace(".", "").isdigit() else 0 for s in marks]
       plt.bar(subjects, averages)
       plt.title("Средние баллы за 3-ю четверть")
       plt.xlabel("Предмет")
       plt.ylabel("Средний балл")
       plt.savefig("final_marks.png")

   asyncio.run(main())
   ```

#### Нюансы
- **Фильтрация**: Только предметы с уроками.
- **Ошибки**:
  - `ValueError`: Если `quarter` не 1–4.
  - Сетевые ошибки возвращают пустой список и логируются.
- **Ограничения**:
  - Зависит от `_get_period_id`.
  - Средний балл только для числовых оценок.
- **Рекомендации**:
  - Проверяйте логи в `bot.log`.
  - Используйте для итогового анализа.

---

### 5. `get_group_teachers`

#### Назначение
Возвращает список учителей группы с информацией о предметах, контактах и должности.

#### Синтаксис
```python
result = await formatter.get_group_teachers()
```

#### Входные параметры
- Нет параметров. (В отличие от примера, метод упрощен, так как период не требуется для асинхронной версии.)

#### Выходные данные
- **Тип**: `List[Dict[str, str]]`
- **Структура элемента**:
  - `id` (`str`): ID учителя.
  - `fullName` (`str`): Полное имя.
  - `shortName` (`str`): Краткое имя.
  - `subjects` (`str`): Предметы (через запятую).
  - `email` (`str`): Email (или пустая строка).
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
   import asyncio

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       teachers = await formatter.get_group_teachers()
       print("Учителя группы:")
       for teacher in teachers:
           print(f"{teacher['fullName']} ({teacher['subjects']})")

   asyncio.run(main())
   ```

2. **Фильтрация по предмету**:
   ```python
   import asyncio

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       teachers = await formatter.get_group_teachers()
       math_teachers = [t for t in teachers if "Математика" in t["subjects"]]
       print("Учителя математики:")
       for teacher in math_teachers:
           print(f"{teacher['shortName']}: {teacher['email']}")

   asyncio.run(main())
   ```

3. **Экспорт контактов**:
   ```python
   import asyncio
   import json

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       teachers = await formatter.get_group_teachers()
       with open("teachers.json", "w", encoding="utf-8") as f:
           json.dump(teachers, f, ensure_ascii=False, indent=2)

   asyncio.run(main())
   ```

#### Нюансы
- **Кэширование**: Использует `_teacher_cache`.
- **Ошибки**:
  - Сетевые ошибки возвращают пустой список и логируются.
- **Ограничения**:
  - Только учителя, привязанные к группе пользователя.
  - Требуется `_teacher_cache`.
- **Рекомендации**:
  - Проверяйте логи в `bot.log`.
  - Используйте для анализа преподавателей.

---

### 6. `get_class_ranking`

#### Назначение
Формирует рейтинг учеников класса по средней оценке за четверть.

#### Синтаксис
```python
result = await formatter.get_class_ranking(quarter, study_year=None)
```

#### Входные параметры
- **quarter** (`int`): Номер четверти.
  - **Описание**: Четверть (1–4).
  - **Ограничения**: 1–4.
  - **Пример**: `3`.
- **study_year** (`Optional[int]`, по умолчанию `None`): Учебный год.
  - **Описание**: Год периода.
  - **Ограничения**: Положительное целое.
  - **Пример**: `2025`.

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
   import asyncio

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       ranking = await formatter.get_class_ranking(quarter=3, study_year=2025)
       print("Рейтинг класса:")
       for student in ranking:
           print(f"{student['name']}: {student['avg_grade']} (оценок: {student['marks_count']})")

   asyncio.run(main())
   ```

2. **Топ-3 ученика**:
   ```python
   import asyncio

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       ranking = await formatter.get_class_ranking(quarter=3, study_year=2025)
       top_3 = sorted(ranking, key=lambda x: x["avg_grade"], reverse=True)[:3]
       print("Топ-3 ученика:")
       for student in top_3:
           print(f"{student['name']}: {student['avg_grade']}")

   asyncio.run(main())
   ```

3. **Экспорт рейтинга**:
   ```python
   import asyncio
   import csv

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       ranking = await formatter.get_class_ranking(quarter=3, study_year=2025)
       with open("ranking.csv", "w", encoding="utf-8", newline="") as f:
           writer = csv.DictWriter(f, fieldnames=["name", "avg_grade", "marks_count"])
           writer.writeheader()
           writer.writerows(ranking)

   asyncio.run(main())
   ```

#### Нюансы
- **Фильтрация**: Только числовые оценки.
- **Ошибки**:
  - `ValueError`: Если `quarter` не 1–4.
  - Сетевые ошибки возвращают пустой список и логируются.
- **Ограничения**:
  - Зависит от `_get_period_id`.
  - Нет оценок — `avg_grade` равен 0.
- **Рекомендации**:
  - Проверяйте логи.
  - Используйте для анализа успеваемости.

---

### 7. `get_subject_stats`

#### Назначение
Возвращает гистограмму оценок по предмету за четверть для группы.

#### Синтаксис
```python
result = await formatter.get_subject_stats(quarter, subject_id, study_year=None)
```

#### Входные параметры
- **quarter** (`int`): Номер четверти.
  - **Описание**: Четверть (1–4).
  - **Ограничения**: 1–4.
  - **Пример**: `3`.
- **subject_id** (`int`): ID предмета.
  - **Описание**: Идентификатор предмета.
  - **Ограничения**: В `_subject_cache`.
  - **Пример**: `101`.
- **study_year** (`Optional[int]`, по умолчанию `None`): Учебный год.
  - **Описание**: Год периода.
  - **Ограничения**: Положительное целое.
  - **Пример**: `2025`.

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
   import asyncio

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       stats = await formatter.get_subject_stats(quarter=3, subject_id=101, study_year=2025)
       print("Статистика по математике:")
       for grade, count in stats.items():
           print(f"Оценка {grade}: {count} раз")

   asyncio.run(main())
   ```

2. **Визуализация гистограммы**:
   ```python
   import asyncio
   import matplotlib.pyplot as plt

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       stats = await formatter.get_subject_stats(quarter=3, subject_id=101, study_year=2025)
       plt.bar(stats.keys(), stats.values())
       plt.title("Распределение оценок по математике")
       plt.xlabel("Оценка")
       plt.ylabel("Количество")
       plt.savefig("subject_stats.png")

   asyncio.run(main())
   ```

3. **Сравнение предметов**:
   ```python
   import asyncio

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       subjects = {101: "Математика", 102: "Русский язык"}
       for subject_id, name in subjects.items():
           stats = await formatter.get_subject_stats(quarter=3, subject_id=subject_id, study_year=2025)
           total = sum(stats.values())
           print(f"{name}: Всего оценок = {total}")

   asyncio.run(main())
   ```

#### Нюансы
- **Ошибки**:
  - `ValueError`: Если `quarter` не 1–4.
  - Сетевые ошибки возвращают пустой словарь и логируются.
- **Ограничения**:
  - Зависит от `_get_period_id`, `_subject_cache`.
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
result = await formatter.get_subject_ranking(quarter, subject_id, study_year=None)
```

#### Входные параметры
- **quarter** (`int`): Номер четверти.
  - **Описание**: Четверть (1–4).
  - **Ограничения**: 1–4.
  - **Пример**: `3`.
- **subject_id** (`int`): ID предмета.
  - **Описание**: Идентификатор предмета.
  - **Ограничения**: В `_subject_cache`.
  - **Пример**: `101`.
- **study_year** (`Optional[int]`, по умолчанию `None`): Учебный год.
  - **Описание**: Год периода.
  - **Ограничения**: Положительное целое.
  - **Пример**: `2025`.

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
   import asyncio

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       ranking = await formatter.get_subject_ranking(quarter=3, subject_id=101, study_year=2025)
       print("Рейтинг по математике:")
       for student in ranking:
           print(f"{student['name']}: {student['avg_grade']}")

   asyncio.run(main())
   ```

2. **Топ-5 учеников**:
   ```python
   import asyncio

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       ranking = await formatter.get_subject_ranking(quarter=3, subject_id=101, study_year=2025)
       top_5 = sorted(ranking, key=lambda x: x["avg_grade"], reverse=True)[:5]
       print("Топ-5 по математике:")
       for student in top_5:
           print(f"{student['name']}: {student['avg_grade']}")

   asyncio.run(main())
   ```

3. **Экспорт рейтинга**:
   ```python
   import asyncio
   import json

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       ranking = await formatter.get_subject_ranking(quarter=3, subject_id=101, study_year=2025)
       with open("subject_ranking.json", "w", encoding="utf-8") as f:
           json.dump(ranking, f, ensure_ascii=False, indent=2)

   asyncio.run(main())
   ```

#### Нюансы
- **Ошибки**:
  - `ValueError`: Если `quarter` не 1–4.
  - Сетевые ошибки возвращают пустой список и логируются.
- **Ограничения**:
  - Требуется валидный `subject_id`.
  - Нет оценок — `avg_grade` равен 0.
- **Рекомендации**:
  - Проверяйте `_subject_cache`.
  - Используйте для анализа успеваемости.

---

### 9. `get_upcoming_tests`

#### Назначение
Возвращает список предстоящих тестов с датой, предметом, типом работы, весом и описанием.

#### Синтаксис
```python
result = await formatter.get_upcoming_tests()
```

#### Входные параметры
- Нет параметров.

#### Выходные данные
- **Тип**: `List[Dict[str, any]]`
- **Структура элемента**:
  - `date` (`str`): Дата теста (`DD.MM.YYYY`).
  - `subject` (`str`): Название предмета.
  - `work_type` (`str`): Тип работы.
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
   import asyncio

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       tests = await formatter.get_upcoming_tests()
       print("Предстоящие тесты:")
       for test in tests:
           print(f"{test['date']} - {test['subject']}: {test['description']}")

   asyncio.run(main())
   ```

2. **Фильтрация важных тестов**:
   ```python
   import asyncio

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       tests = await formatter.get_upcoming_tests()
       print("Важные тесты (вес > 1):")
       for test in tests:
           if test["weight"] > 1:
               print(f"{test['date']} - {test['subject']}: {test['description']}")

   asyncio.run(main())
   ```

3. **Экспорт тестов**:
   ```python
   import asyncio
   import json

   async def main():
       formatter = DnevnikFormatter(token="your_token", debug_mode=True)
       await formatter.initialize()
       tests = await formatter.get_upcoming_tests()
       with open("tests.json", "w", encoding="utf-8") as f:
           json.dump(tests, f, ensure_ascii=False, indent=2)

   asyncio.run(main())
   ```

#### Нюансы
- **Период**: Тесты за ближайшие 30 дней.
- **Ошибки**:
  - Сетевые ошибки возвращают пустой список и логируются.
- **Ограничения**:
  - Зависит от `_lesson_cache`, `_subject_cache`.
  - Только работы, помеченные как тесты.
- **Рекомендации**:
  - Проверяйте логи.
  - Используйте для планирования.

---

## Внутренние методы класса

Ниже описаны внутренние асинхронные методы, начинающиеся с `_`, которые используются основными методами для выполнения запросов к API, обработки данных и управления кэшем. Эти методы не предназначены для прямого вызова разработчиком, но их понимание полезно для отладки и расширения функциональности.

### 1. `_get_schedule`

#### Назначение
Запрашивает данные расписания за указанный период через API Дневник.ру и сохраняет их в `_lesson_cache`.

#### Синтаксис
```python
result = await formatter._get_schedule(start_date, end_date)
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
- **Описание**: Словарь, где ключи — даты в формате `YYYY-MM-DD`, а значения — словари с данными уроков, предметов, учителей, домашних заданий и работ.

#### Контекст использования
- Вызывается методом `get_formatted_schedule` для получения данных перед их форматированием.
- Использует API-запрос через `dnevnik_api.get_schedule`, если данные отсутствуют в `_lesson_cache`.
- Логирует запросы и ошибки в `bot.log`.

#### Нюансы
- **Кэширование**: Сохраняет данные в `_lesson_cache`.
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
result = await formatter._get_marks(start_date, end_date)
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
- Выполняет API-запрос через `dnevnik_api.get_marks`, если данные отсутствуют.
- Логирует запросы и ошибки.

#### Нюансы
- **Кэширование**: Не использует отдельный кэш, но зависит от `_lesson_cache`.
- **Ошибки**:
  - Сетевые ошибки возвращают пустой список.
  - Некорректные даты вызывают `ValueError`.
- **Ограничения**: Зависит от `_lesson_cache` для связи оценок с уроками.
- **Рекомендации**: Проверяйте логи для диагностики.

---

### 3. `_get_period_id`

#### Назначение
Определяет ID периода для указанной четверти и учебного года.

#### Синтаксис
```python
result = await formatter._get_period_id(study_year, quarter)
```

#### Входные параметры
- **study_year** (`int`): Учебный год.
  - **Описание**: Год периода.
  - **Ограничения**: Положительное целое.
  - **Пример**: `2025`.
- **quarter** (`int`): Номер четверти.
  - **Описание**: Четверть (1–4).
  - **Ограничения**: 1–4.
  - **Пример**: `3`.

#### Выходные данные
- **Тип**: `str`
- **Описание**: ID периода четверти (например, "2024-2025-Q3").

#### Контекст использования
- Используется методами `get_formatted_final_marks`, `get_class_ranking`, `get_subject_stats`, `get_subject_ranking` для определения периода.
- Запрашивает данные о периодах через `dnevnik_api.get_periods`, если кэш пуст.
- Логирует ошибки.

#### Нюансы
- **Кэширование**: Сохраняет данные в `_period_cache`.
- **Ошибки**:
  - `ValueError`: Если `quarter` не 1–4.
  - Сетевые ошибки возвращают `None`.
- **Ограничения**: Зависит от API и структуры периодов.
- **Рекомендации**: Проверяйте логи при пустом результате.

---

### 4. `_cache_subjects`

#### Назначение
Инициализирует кэш предметов (`_subject_cache`) при создании объекта класса.

#### Синтаксис
```python
await formatter._cache_subjects()
```

#### Входные параметры
- Нет параметров.

#### Выходные данные
- **Тип**: `None`
- **Описание**: Заполняет `_subject_cache` данными из API (ID предмета → название).

#### Контекст использования
- Вызывается в `initialize` для загрузки списка предметов.
- Запрашивает данные через `dnevnik_api.get_subjects`.
- Логирует процесс загрузки.

#### Нюансы
- **Ошибки**:
  - Сетевые ошибки логируются, но не прерывают инициализацию.
  - Пустой кэш может повлиять на методы.
- **Ограничения**: Зависит от токена и API.
- **Рекомендации**: Проверяйте логи для проверки загрузки.

---

### 5. `_cache_teachers`

#### Назначение
Инициализирует кэш учителей (`_teacher_cache`) при создании объекта класса.

#### Синтаксис
```python
await formatter._cache_teachers()
```

#### Входные параметры
- Нет параметров.

#### Выходные данные
- **Тип**: `None`
- **Описание**: Заполняет `_teacher_cache` данными из API (ID учителя → данные).

#### Контекст использования
- Вызывается в `initialize` для загрузки списка учителей.
- Запрашивает данные через `dnevnik_api.get_teachers`.
- Логирует процесс загрузки.

#### Нюансы
- **Ошибки**:
  - Сетевые ошибки логируются, но не прерывают инициализацию.
- **Ограничения**: Зависит от токена и API.
- **Рекомендации**: Проверяйте логи.

---

### 6. `_format_date`

#### Назначение
Форматирует объект `datetime` в строку `DD.MM.YYYY`.

#### Синтаксис
```python
result = formatter._format_date(dt)
```

#### Входные параметры
- **dt** (`datetime`): Дата.
  - **Описание**: Объект `datetime`.
  - **Пример**: `datetime(2025, 5, 21)`.

#### Выходные данные
- **Тип**: `str`
- **Описание**: Форматированная дата (например, "21.05.2025").

#### Контекст использования
- Используется всеми методами для форматирования дат в выходных данных.
- Не асинхронный, так как выполняет простое форматирование.

#### Нюансы
- **Ошибки**: Некорректный `dt` вызывает исключение.
- **Ограничения**: Формат фиксирован.
- **Рекомендации**: Используйте для единообразного вывода дат.

---

### 7. `_format_lesson`

#### Назначение
Форматирует данные урока в структурированный вид для метода `get_formatted_schedule`.

#### Синтаксис
```python
result = await formatter._format_lesson(lesson_data, date)
```

#### Входные параметры
- **lesson_data** (`Dict`): Данные урока.
  - **Описание**: Словарь с информацией об уроке (ID, предмет, учитель, время, домашнее задание, работы).
  - **Пример**: `{"id": 1001, "subject_id": 101, "hours": "08:30-09:15", ...}`.
- **date** (`str`): Дата урока.
  - **Описание**: Дата в формате `YYYY-MM-DD`.
  - **Пример**: `"2025-05-21"`.

#### Выходные данные
- **Тип**: `Dict[str, any]`
- **Описание**: Форматированный словарь урока, соответствующий структуре `get_formatted_schedule`.

#### Контекст использования
- Вызывается в `get_formatted_schedule` для преобразования сырых данных.
- Использует `_subject_cache`, `_teacher_cache`.

#### Нюансы
- **Ошибки**: Отсутствие данных в кэшах пропускается с логированием.
- **Ограничения**: Зависит от корректности входных данных.
- **Рекомендации**: Проверяйте кэши перед вызовом.

---

### 8. `_get_histogram`

#### Назначение
Запрашивает гистограмму оценок для работы через API.

#### Синтаксис
```python
result = await formatter._get_histogram(work_id)
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

## Дополнительный метод

### `analyze_data`

#### Назначение
Выполняет AI-анализ данных (расписания, оценок, рейтинга) с использованием DeepSeek через OpenRouter.

#### Синтаксис
```python
result = await formatter.analyze_data(type, start_date=None, end_date=None, quarter=None, study_year=None)
```

#### Входные параметры
- **type** (`str`): Тип анализа.
  - **Описание**: `weeks` (расписание), `marks` (оценки), `ranking` (рейтинг).
  - **Ограничения**: Должен быть в `prompts.json`.
  - **Пример**: `"marks"`.
- **start_date** (`Optional[datetime]`): Начальная дата (для `weeks`, `marks`).
  - **Пример**: `datetime(2025, 5, 1)`.
- **end_date** (`Optional[datetime]`): Конечная дата (для `weeks`, `marks`).
  - **Пример**: `datetime(2025, 5, 31)`.
- **quarter** (`Optional[int]`): Номер четверти (для `ranking`).
  - **Пример**: `3`.
- **study_year** (`Optional[int]`): Учебный год (для `ranking`).
  - **Пример**: `2025`.

#### Выходные данные
- **Тип**: `str`
- **Описание**: Человекочитаемый результат анализа.

#### Обработанный вывод
```python
"Ваши оценки за май 2025 показывают сильные результаты по математике (средний балл 4.8), но по литературе есть пробелы (средний балл 3.5). Рекомендуется уделить больше времени анализу текстов."
```

#### Пример использования
```python
import asyncio
from datetime import datetime

async def main():
    formatter = DnevnikFormatter(token="your_token", debug_mode=True)
    await formatter.initialize()
    result = await formatter.analyze_data(type="marks", start_date=datetime(2025, 5, 1), end_date=datetime(2025, 5, 31))
    print("Анализ оценок:")
    print(result)

asyncio.run(main())
```

#### Нюансы
- **Зависимости**: Требует `prompts.json` и `OPENROUTER_API_KEY`.
- **Ошибки**:
  - Сетевые ошибки возвращают сообщение об ошибке.
  - Отсутствие промпта вызывает исключение.
- **Ограничения**: Зависит от внешнего API OpenRouter.
- **Рекомендации**: Проверяйте логи и наличие API-ключа.

---

## Общие рекомендации

### Обработка ошибок
- **Сетевые ошибки**: Все методы возвращают пустые структуры (`[]`, `{}`) при сбоях API и логируют ошибки в `bot.log`.
- **Параметры**:
  - Проверяйте `quarter` (1–4), `subject_id` (в `_subject_cache`), даты (`end_date` не раньше `start_date`).
  - Некорректные параметры вызывают `ValueError`.
- **Логи**: Используйте `debug_mode=True` для диагностики, проверяйте `bot.log` (формат: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`).

### Оптимизация
- **Кэширование**: Используйте `_lesson_cache`, `_subject_cache`, `_teacher_cache` для минимизации запросов. Очищайте через `_clear_lesson_cache` при необходимости.
- **Лимиты API**: Разбивайте большие периоды (например, месяцы) на недели:
  ```python
  async def get_schedule_chunks(formatter, start_date, end_date, chunk_days=7):
      result = {}
      current = start_date
      while current <= end_date:
          chunk_end = min(current + timedelta(days=chunk_days - 1), end_date)
          chunk = await formatter.get_formatted_schedule(current, chunk_end)
          result.update(chunk)
          current = chunk_end + timedelta(days=1)
      return result
  ```
- **Обновления**: Перезагружайте кэши при смене учебного года или группы.

### Ограничения
- **Зависимость от API**: Требуется стабильный доступ к Дневник.ру.
- **Кэширование**: Устаревшие кэши могут дать некорректные результаты.
- **Язык**: Названия предметов и работ на русском.
- **AI-анализ**: Зависит от внешнего API OpenRouter, увеличивает задержки.

### Пример интеграции
Создание отчета в Telegram-боте:
```python
import asyncio
import json
from aiogram import Bot, Dispatcher
from DnevnikFormatterAsync import DnevnikFormatter
from datetime import datetime, timedelta

BOT_TOKEN = "your_bot_token"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_formatters = {}

@dp.message(commands=["report"])
async def cmd_report(message):
    user_id = message.from_user.id
    if user_id not in user_formatters:
        await message.answer("Установите токен с помощью /set_token")
        return
    formatter = user_formatters[user_id]
    start_date = datetime(2025, 5, 21)
    end_date = start_date + timedelta(days=7)
    try:
        # Расписание
        schedule = await formatter.get_formatted_schedule(start_date, end_date)
        response = "📅 Расписание:\n"
        for date, lessons in schedule.items():
            response += f"\n{date}:\n"
            for lesson in lessons:
                response += f"• {lesson['time']} - {lesson['subject']}: {lesson['homework']}\n"
        await message.answer(response[:4000])

        # Последние оценки
        marks = await formatter.get_last_marks(count=5)
        response = "📊 Последние оценки:\n"
        for mark in marks:
            response += f"• {mark['date']} - {mark['subject']}: {mark['mark']}\n"
        await message.answer(response[:4000])

        # Экспорт
        with open(f"report_{user_id}.json", "w", encoding="utf-8") as f:
            json.dump({"schedule": schedule, "marks": marks}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
```

### Визуализация
График оценок:
```python
import asyncio
import matplotlib.pyplot as plt
from datetime import datetime

async def main():
    formatter = DnevnikFormatter(token="your_token", debug_mode=True)
    await formatter.initialize()
    marks = await formatter.get_formatted_marks(datetime(2025, 5, 1), datetime(2025, 5, 31))
    subjects = list(marks.keys())
    counts = [len(grades) for grades in marks.values()]
    plt.bar(subjects, counts)
    plt.title("Количество оценок по предметам за май")
    plt.xlabel("Предмет")
    plt.ylabel("Оценок")
    plt.savefig("marks_per_subject.png")

asyncio.run(main())
```

## Заключение
`DnevnikFormatterAsync` упрощает асинхронную работу с данными Дневник.ру, предоставляя структурированные результаты для расписания, оценок, тестов и рейтингов. Используйте примеры кода и внутренние методы для отладки и расширения. Для диагностики включайте `debug_mode=True` и проверяйте `bot.log`. Для продакшена добавьте базу данных, ограничение запросов и мониторинг, как описано в рекомендациях.
