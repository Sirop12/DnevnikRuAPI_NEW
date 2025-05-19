import os
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.text import Text
from rich import box
from dnevnik_formatter import DnevnikFormatter

console = Console()

def clear_screen():
    """Очищает консоль."""
    os.system('cls' if os.name == 'nt' else 'clear')

def display_menu():
    """Отображает главное меню."""
    clear_screen()
    console.print(Panel.fit(
        "[bold magenta]Дневник.ру: Демонстрация функционала[/bold magenta]\n"
        "Выберите опцию для просмотра данных:",
        border_style="cyan",
        box=box.ROUNDED
    ))
    console.print("[1] Расписание на день или период")
    console.print("[2] Последние оценки")
    console.print("[3] Оценки за период")
    console.print("[4] Итоговые оценки за четверть")
    console.print("[5] Список учителей группы")
    console.print("[6] Рейтинг класса")
    console.print("[7] Статистика по предмету")
    console.print("[8] Рейтинг по предмету")
    console.print("[9] Статистика класса")
    console.print("[0] Выход")
    return IntPrompt.ask("\nВведите номер опции", choices=[str(i) for i in range(10)], default=0)

def format_date_input(prompt: str) -> datetime:
    """Запрашивает дату у пользователя в формате DD.MM.YYYY."""
    while True:
        date_str = Prompt.ask(prompt, default=datetime.now().strftime("%d.%m.%Y"))
        try:
            return datetime.strptime(date_str, "%d.%m.%Y")
        except ValueError:
            console.print("[red]Неверный формат даты! Используйте DD.MM.YYYY[/red]")

def display_schedule(formatter: DnevnikFormatter):
    """Показывает расписание на день или период."""
    period = Prompt.ask("Показать расписание за [1] день или [2] период?", choices=["1", "2"], default="1")
    if period == "1":
        date = format_date_input("Введите дату (DD.MM.YYYY)")
        schedule = formatter.get_formatted_schedule(date)
        if not schedule:
            console.print(f"[yellow]Нет уроков на {date.strftime('%d.%m.%Y')}[/yellow]")
            return
        table = Table(title=f"Расписание на {date.strftime('%d.%m.%Y')}", box=box.MINIMAL, show_lines=True)
        table.add_column("Время", style="cyan", width=15)
        table.add_column("Предмет", style="green", width=20)
        table.add_column("Тема", style="white", width=30)
        table.add_column("Учитель", style="yellow", width=15)
        table.add_column("Кабинет", style="magenta", width=25)
        table.add_column("ДЗ", style="blue", width=30)
        table.add_column("Оценки", style="red", width=25)
        table.add_column("Статус", style="cyan", width=10)
        table.add_column("Посещ.", style="green", width=10)
        for lesson in schedule:
            marks = '; '.join(f"{m['value']} ({m['work_type']}, {m['mood']})" for m in lesson['mark_details'])
            marks_text = Text(marks or "Нет", style="bold red" if marks else "red")
            homework = lesson['homework']
            if lesson['is_important']:
                homework += " (Важное)"
            if lesson['sent_date']:
                sent_date = datetime.strptime(lesson['sent_date'], "%Y-%m-%dT%H:%M:%S.%f").strftime('%d.%m.%Y')
                homework += f" [{sent_date}]"
            table.add_row(
                lesson['time'],
                lesson['subject'],
                lesson['title'],
                lesson['teacher'],
                lesson['classroom'],
                homework,
                marks_text,
                lesson['lesson_status'],
                lesson['attendance']
            )
        console.print(table)
    else:
        start_date = format_date_input("Введите начальную дату (DD.MM.YYYY)")
        end_date = format_date_input("Введите конечную дату (DD.MM.YYYY)")
        schedule = formatter.get_formatted_schedule(start_date, end_date)
        console.print(f"[cyan]Получено {len(schedule)} дней расписания[/cyan]")
        for date_str, lessons in schedule.items():
            if not lessons:
                console.print(f"[yellow]Нет уроков на {date_str}[/yellow]")
                continue
            table = Table(title=f"Расписание на {date_str}", box=box.MINIMAL, show_lines=True)
            table.add_column("Время", style="cyan", width=15)
            table.add_column("Предмет", style="green", width=20)
            table.add_column("Тема", style="white", width=30)
            table.add_column("Учитель", style="yellow", width=15)
            table.add_column("Кабинет", style="magenta", width=25)
            table.add_column("ДЗ", style="blue", width=30)
            table.add_column("Оценки", style="red", width=25)
            table.add_column("Статус", style="cyan", width=10)
            table.add_column("Посещ.", style="green", width=10)
            for lesson in lessons:
                marks = '; '.join(f"{m['value']} ({m['work_type']}, {m['mood']})" for m in lesson['mark_details'])
                marks_text = Text(marks or "Нет", style="bold red" if marks else "red")
                homework = lesson['homework']
                if lesson['is_important']:
                    homework += " (Важное)"
                if lesson['sent_date']:
                    sent_date = datetime.strptime(lesson['sent_date'], "%Y-%m-%dT%H:%M:%S.%f").strftime('%d.%m.%Y')
                    homework += f" [{sent_date}]"
                table.add_row(
                    lesson['time'],
                    lesson['subject'],
                    lesson['title'],
                    lesson['teacher'],
                    lesson['classroom'],
                    homework,
                    marks_text,
                    lesson['lesson_status'],
                    lesson['attendance']
                )
            console.print(table)

def display_last_marks(formatter: DnevnikFormatter):
    """Показывает последние оценки."""
    count = IntPrompt.ask("Сколько последних оценок показать?", default=5)
    marks = formatter.get_last_marks(count)
    table = Table(title="Последние оценки", box=box.MINIMAL, show_lines=True)
    table.add_column("Дата", style="cyan")
    table.add_column("Предмет", style="green")
    table.add_column("Тип работы", style="yellow")
    table.add_column("Тема урока", style="yellow")
    table.add_column("Оценка", style="red")
    table.add_column("Распределение в классе", style="blue")
    for mark in marks:
        distribution = ", ".join(f"{k}: {v}" for k, v in mark['class_distribution'].items()) or "Нет данных"
        mark_value = Text(mark['mark'], style="bold red" if mark['mark'].isdigit() and int(mark['mark']) >= 4 else "red")
        table.add_row(
            mark['date'],
            mark['subject'],
            mark['work_type'],
            mark['lesson_title'],
            mark_value,
            distribution
        )
    console.print(table)

def display_marks_period(formatter: DnevnikFormatter):
    """Показывает оценки за период."""
    start_date = format_date_input("Введите начальную дату (DD.MM.YYYY)")
    end_date = format_date_input("Введите конечную дату (DD.MM.YYYY)")
    marks = formatter.get_formatted_marks(start_date, end_date)
    if not marks:
        console.print("[yellow]Нет оценок за указанный период[/yellow]")
        return
    for subject, mark_list in marks.items():
        table = Table(title=f"Оценки по предмету: {subject}", box=box.MINIMAL, show_lines=True)
        table.add_column("Дата урока", style="cyan", width=12)
        table.add_column("Дата оценки", style="yellow", width=12)
        table.add_column("Оценка", style="red", width=10)
        table.add_column("Тип работы", style="blue", width=20)
        table.add_column("Настроение", style="blue", width=12)
        table.add_column("Тема урока", style="white", width=30)
        for mark in mark_list:
            mark_value = Text(mark['value'], style="bold red" if mark['value'].isdigit() and int(mark['value']) >= 4 else "red")
            table.add_row(
                mark['lesson_date'],
                mark['mark_date'],
                mark_value,
                mark['work_type'],
                mark['mood'],
                mark['lesson_title']
            )
        console.print(table)

def display_final_marks(formatter: DnevnikFormatter):
    """Показывает итоговые оценки за четверть."""
    year = IntPrompt.ask("Введите учебный год (например, 2025)", default=2025)
    quarter = IntPrompt.ask("Введите номер четверти (1-4)", choices=["1", "2", "3", "4"], default=4)
    marks = formatter.get_formatted_final_marks(year, quarter)
    if not marks:
        console.print("[yellow]Нет итоговых оценок[/yellow]")
        return
    table = Table(title=f"Итоговые оценки за {quarter}-ю четверть {year}", box=box.MINIMAL, show_lines=True)
    table.add_column("Предмет", style="green", width=25)
    table.add_column("Оценки", style="red", width=20)
    table.add_column("Средний балл", style="yellow", width=15)
    for mark in marks:
        grades = ", ".join(map(str, mark['оценки'])) or "Нет оценок"
        avg = Text(mark['средний балл'], style="bold yellow" if mark['средний балл'] != "Нет оценок" and float(mark['средний балл']) >= 4 else "yellow")
        table.add_row(
            mark['название предмета'],
            grades,
            avg
        )
    console.print(table)

def display_teachers(formatter: DnevnikFormatter):
    """Показывает список учителей группы."""
    start_date = format_date_input("Введите начальную дату (DD.MM.YYYY)")
    end_date = format_date_input("Введите конечную дату (DD.MM.YYYY)")
    teachers = formatter.get_group_teachers(start_date, end_date)
    if not teachers:
        console.print("[yellow]Нет данных об учителях[/yellow]")
        return
    table = Table(title="Учителя группы", box=box.MINIMAL, show_lines=True)
    table.add_column("ФИО", style="green", width=25)
    table.add_column("Короткое имя", style="cyan", width=15)
    table.add_column("Предметы", style="yellow", width=20)
    table.add_column("Должность", style="magenta", width=15)
    table.add_column("Email", style="blue", width=20)
    for teacher in teachers:
        table.add_row(
            teacher['fullName'],
            teacher['shortName'],
            teacher['subjects'],
            teacher['position'],
            teacher['email']
        )
    console.print(table)

def display_class_ranking(formatter: DnevnikFormatter):
    """Показывает рейтинг учеников класса."""
    year = IntPrompt.ask("Введите учебный год (например, 2025)", default=2025)
    quarter = IntPrompt.ask("Введите номер четверти (1-4)", choices=["1", "2", "3", "4"], default=4)
    ranking = formatter.get_class_ranking(year, quarter)
    if not ranking:
        console.print("[yellow]Нет данных для рейтинга[/yellow]")
        return
    table = Table(title=f"Рейтинг класса за {quarter}-ю четверть {year}", box=box.MINIMAL, show_lines=True)
    table.add_column("Место", style="cyan", width=8)
    table.add_column("Имя", style="green", width=20)
    table.add_column("Средний балл", style="yellow", width=15)
    table.add_column("Количество оценок", style="blue", width=15)
    for i, student in enumerate(ranking, 1):
        avg_grade = Text(str(student['avg_grade']), style="bold yellow" if student['avg_grade'] >= 4 else "yellow")
        table.add_row(
            str(i),
            student['name'],
            avg_grade,
            str(student['marks_count'])
        )
    console.print(table)

def display_subject_stats(formatter: DnevnikFormatter):
    """Показывает статистику по предмету."""
    year = IntPrompt.ask("Введите учебный год (например, 2025)", default=2025)
    quarter = IntPrompt.ask("Введите номер четверти (1-4)", choices=["1", "2", "3", "4"], default=4)
    console.print("\nДоступные предметы:")
    for sid, name in formatter._subject_cache.items():
        console.print(f"[{sid}] {name}")
    subject_id = IntPrompt.ask("Введите ID предмета")
    stats = formatter.get_subject_stats(year, quarter, subject_id)
    if not stats:
        console.print("[yellow]Нет статистики по предмету[/yellow]")
        return
    table = Table(title=f"Статистика по предмету (ID: {subject_id}) за {quarter}-ю четверть {year}", box=box.MINIMAL, show_lines=True)
    table.add_column("Оценка", style="red", width=10)
    table.add_column("Количество", style="blue", width=15)
    for grade, count in stats.items():
        table.add_row(
            Text(grade, style="bold red" if grade.isdigit() and int(grade) >= 4 else "red"),
            str(count)
        )
    console.print(table)

def display_subject_ranking(formatter: DnevnikFormatter):
    """Показывает рейтинг по предмету."""
    year = IntPrompt.ask("Введите учебный год (например, 2025)", default=2025)
    quarter = IntPrompt.ask("Введите номер четверти (1-4)", choices=["1", "2", "3", "4"], default=4)
    console.print("\nДоступные предметы:")
    for sid, name in formatter._subject_cache.items():
        console.print(f"[{sid}] {name}")
    subject_id = IntPrompt.ask("Введите ID предмета")
    ranking = formatter.get_subject_ranking(year, quarter, subject_id)
    if not ranking:
        console.print("[yellow]Нет данных для рейтинга[/yellow]")
        return
    table = Table(title=f"Рейтинг по предмету (ID: {subject_id}) за {quarter}-ю четверть {year}", box=box.MINIMAL, show_lines=True)
    table.add_column("Место", style="cyan", width=8)
    table.add_column("Имя", style="green", width=20)
    table.add_column("Средний балл", style="yellow", width=15)
    table.add_column("Количество оценок", style="blue", width=15)
    for i, student in enumerate(ranking, 1):
        avg_grade = Text(str(student['avg_grade']), style="bold yellow" if student['avg_grade'] >= 4 else "yellow")
        table.add_row(
            str(i),
            student['name'],
            avg_grade,
            str(student['marks_count'])
        )
    console.print(table)

def display_class_stats(formatter: DnevnikFormatter):
    """Показывает статистику класса."""
    year = IntPrompt.ask("Введите учебный год (например, 2025)", default=2025)
    quarter = IntPrompt.ask("Введите номер четверти (1-4)", choices=["1", "2", "3", "4"], default=4)
    stats = formatter.get_class_stats(year, quarter)
    if not stats:
        console.print("[yellow]Нет статистики по классу[/yellow]")
        return
    table = Table(title=f"Статистика класса за {quarter}-ю четверть {year}", box=box.MINIMAL, show_lines=True)
    table.add_column("Метрика", style="cyan", width=20)
    table.add_column("Значение", style="yellow", width=20)
    table.add_row("Всего оценок", str(stats.get('total_marks', 0)))
    table.add_row("Средний балл класса", str(stats.get('average_class_grade', 0)))
    console.print(table)
    if stats.get('grade_distribution'):
        dist_table = Table(title="Распределение оценок", box=box.MINIMAL, show_lines=True)
        dist_table.add_column("Оценка", style="red", width=10)
        dist_table.add_column("Процент", style="blue", width=15)
        for grade, percentage in stats['grade_distribution'].items():
            dist_table.add_row(
                Text(grade, style="bold red" if grade.isdigit() and int(grade) >= 4 else "red"),
                f"{percentage:.2f}%"
            )
        console.print(dist_table)

def main():
    """Основная функция программы."""
    token = Prompt.ask("Введите токен API Дневник.ру", password=0)
    try:
        formatter = DnevnikFormatter(token=token, debug_mode=True)
    except Exception as e:
        console.print(f"[red]Ошибка инициализации: {e}[/red]")
        return

    while True:
        choice = display_menu()
        if choice == 0:
            console.print("[bold green]До свидания![/bold green]")
            break
        try:
            if choice == 1:
                display_schedule(formatter)
            elif choice == 2:
                display_last_marks(formatter)
            elif choice == 3:
                display_marks_period(formatter)
            elif choice == 4:
                display_final_marks(formatter)
            elif choice == 5:
                display_teachers(formatter)
            elif choice == 6:
                display_class_ranking(formatter)
            elif choice == 7:
                display_subject_stats(formatter)
            elif choice == 8:
                display_subject_ranking(formatter)
            elif choice == 9:
                display_class_stats(formatter)
            else:
                console.print("[red]Неверный выбор, попробуйте снова.[/red]")
        except Exception as e:
            console.print(f"[red]Произошла ошибка: {e}[/red]")
        Prompt.ask("\nНажмите Enter для продолжения...")

if __name__ == "__main__":
    main()
