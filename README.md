# Простой Telegram бот и CLI клиент с Yandex GPT

Упрощенная версия проекта, содержащая Telegram бот и CLI клиент с прямым обращением к Yandex GPT API.

## Структура проекта

```
├── bot/                    # Telegram бот
│   ├── bot.py             # Основной код бота
│   ├── settings.py        # Настройки бота
│   └── test_launch.sh     # Тестовый скрипт
├── yandex_gpt/            # Модуль для работы с Yandex GPT
│   ├── yandex_gpt.py      # API класс для Yandex GPT (с поддержкой streaming)
│   ├── settings.py        # Настройки Yandex GPT
│   └── private_key.pem    # Приватный ключ (добавить самостоятельно)
├── cli_client.py          # CLI клиент с realtime выводом
├── run_bot.py             # Скрипт запуска бота
├── run_cli.py             # Скрипт запуска CLI клиента
└── requirements.txt       # Python зависимости
```

## Настройка

1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

2. Создайте файл `.env` в корне проекта с переменными:
   ```
   TELEGRAM_TOKEN=your_telegram_bot_token_here
   SERVICE_ACCOUNT_ID=your_service_account_id
   KEY_ID=your_key_id
   FOLDER_ID=your_folder_id
   ```

3. Добавьте файл `yandex_gpt/private_key.pem` с приватным ключом от Yandex Cloud

## Запуск

### Telegram бот
```bash
python run_bot.py
```

### CLI клиент с realtime выводом
```bash
python run_cli.py
```

## Функциональность

### Telegram бот
- Простой Telegram бот
- Прямое обращение к Yandex GPT API без дополнительных промптов
- Автоматическое получение IAM токенов
- Обработка ошибок

### CLI клиент
- Интерактивный консольный интерфейс
- **Realtime вывод ответов GPT** - видите ответ по мере его генерации
- Поддержка streaming API
- Простые команды (exit для выхода)
