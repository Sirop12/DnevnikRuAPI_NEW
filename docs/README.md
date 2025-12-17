# поддержка осуществляется только для версии DnevnikFormatterAsyncV2.py
# Документация по модулю DnevnikFormatter

![Static Badge](https://img.shields.io/badge/DnevnikRuAPI_NEW-Sirop12)
![GitHub top language](https://img.shields.io/github/languages/top/Sirop12/DnevnikRuAPI_NEW)
![GitHub Repo stars](https://img.shields.io/github/stars/Sirop12/DnevnikRuAPI_NEW)
![GitHub issues](https://img.shields.io/github/issues/Sirop12/DnevnikRuAPI_NEW)

[СВЯЗЬ](https://t.me/Sirop1)

[ПОЛУЧИТЬ ТОКЕН](https://androsovpavel.pythonanywhere.com/)



# DnevnikFormatter

`DnevnikFormatter` — Python-модуль для работы с API Дневник.ру, упрощающая доступ к данным о расписании, оценках и тестах. Включает синхронный модуль для простых скриптов и асинхронный для Telegram-ботов и веб-приложений.

## Примеры использования

### Синхронный модуль
```python
from DnevnikFormatter import DnevnikFormatter
formatter = DnevnikFormatter(token="your_token")
schedule = formatter.get_formatted_schedule("2025-05-21")
```

### Асинхронный модуль
```python
from DnevnikFormatterAsync import DnevnikFormatter
async def main():
    formatter = DnevnikFormatter(token="your_token")
    await formatter.initialize()
    schedule = await formatter.get_formatted_schedule("2025-05-21")
```

## Документация
- [Синхронный модуль (`DnevnikFormatter`)](./DnevnikFormatter.md)
- [Асинхронный модуль (`DnevnikFormatterAsync`)](./DnevnikFormatterAsync.md)
