# Документация: Автоматическая проверка заданий через вебхуки

## Описание
Система автоматической проверки выполнения заданий в чатах использует вебхуки от внешних сервисов (Flyer, TGrass) для мгновенного начисления наград пользователям.

## Архитектура

### Компоненты системы

1. **Webhook Server** (`webhook_server.py`)
   - FastAPI сервер для приёма вебхуков
   - Обрабатывает события от Flyer и TGrass
   - Проверяет подписи запросов (HMAC SHA256)

2. **Bot Bridge** (`services/webhook_bot_bridge.py`)
   - Связующий модуль между вебхук-сервером и ботом
   - Отправляет уведомления пользователям
   - Обрабатывает события выполнения/отмены заданий

3. **Database Service** (`services/database_service.py`)
   - Метод `reward_specific_task()` - начисление награды за задание
   - Работа с таблицами `task_assignments` и `task_rewards`

## Как это работает

### Процесс выполнения задания

1. **Пользователь получает задание**
   - Бот показывает список заданий в чате
   - Задание сохраняется в таблицу `task_assignments`

2. **Пользователь подписывается на канал**
   - Внешний сервис (Flyer/TGrass) отслеживает подписку
   - Сервис отправляет вебхук на наш сервер

3. **Вебхук обрабатывается**
   - Webhook server получает событие `sub_completed`
   - Проверяется подпись запроса (если настроена)
   - Вызывается `database.reward_specific_task()`

4. **Начисление награды**
   - Проверяется, что задание существует и не выполнено
   - Создаётся запись в `task_rewards`
   - Обновляется статус в `task_assignments`
   - Владельцу чата начисляется награда

5. **Уведомление пользователя**
   - Бот отправляет сообщение о выполнении задания
   - Показывается сумма награды

### Процесс отписки

1. **Пользователь отписывается от канала**
   - Внешний сервис обнаруживает отписку
   - Отправляет вебхук с событием `new_status: abort` или `status: unsubscribed`

2. **Обработка отписки**
   - Webhook server получает событие
   - Вызывается `handle_task_abort()`
   - Пользователю отправляется предупреждение

3. **Возможные действия**
   - Списание награды (TODO: не реализовано)
   - Блокировка пользователя при повторных нарушениях
   - Кнопка "🔄 Проверить подписку" для повторной проверки

## Endpoints

### Flyer Webhook
**URL:** `POST /flyer_webhook`

**Формат запроса:**
```json
{
  "type": "sub_completed",
  "data": {
    "user_id": 123456789,
    "chat_id": -1001234567890,
    "task_id": "flyer_task_123"
  }
}
```

**Типы событий:**
- `test` - тестовый запрос
- `sub_completed` - подписка выполнена
- `new_status` - изменение статуса (отписка)

### TGrass Webhook
**URL:** `POST /tgrass_webhook`

**Формат запроса:**
```json
{
  "tg_user_id": 123456789,
  "offer_link": "https://t.me/channel",
  "status": "subscribed"
}
```

**Статусы:**
- `subscribed` - пользователь подписался
- `unsubscribed` - пользователь отписался

## Настройка

### Переменные окружения (.env)

```env
# Webhook сервер
WEBHOOK_HOST=0.0.0.0
WEBHOOK_PORT=8000

# Секретные ключи для проверки подписи
FLYER_SECRET=your_flyer_secret_key
TGRASS_SECRET=your_tgrass_secret_key

# Токен бота
API_TOKEN=your_bot_token
```

### Запуск webhook сервера

```bash
python webhook_server.py
```

Или через uvicorn:
```bash
uvicorn webhook_server:app --host 0.0.0.0 --port 8000
```

### Настройка вебхуков в сервисах

**Flyer:**
1. Зайдите в настройки Flyer API
2. Укажите URL: `https://your-domain.com/flyer_webhook`
3. Добавьте секретный ключ в `.env`

**TGrass:**
1. Зайдите в настройки TGrass
2. Укажите URL: `https://your-domain.com/tgrass_webhook`
3. Добавьте секретный ключ в `.env`

## Безопасность

### Проверка подписи
Вебхуки проверяются с помощью HMAC SHA256:
```python
expected_signature = hmac.new(
    secret.encode(),
    payload,
    hashlib.sha256
).hexdigest()
```

### Режим разработки
Если секретный ключ не настроен, проверка подписи пропускается (только для разработки!).

## Таблицы базы данных

### task_assignments
Хранит назначенные задания пользователям:
```sql
CREATE TABLE task_assignments (
    chat_id INTEGER,
    member_user_id INTEGER,
    task_source TEXT,
    task_key TEXT,
    task_title TEXT,
    assigned_at TEXT,
    completed_at TEXT,
    rewarded_at TEXT,
    PRIMARY KEY (chat_id, member_user_id, task_source, task_key)
);
```

### task_rewards
Хранит начисленные награды:
```sql
CREATE TABLE task_rewards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_user_id INTEGER,
    chat_id INTEGER,
    member_user_id INTEGER,
    task_source TEXT,
    task_key TEXT,
    task_title TEXT,
    amount REAL,
    created_at TEXT,
    UNIQUE(chat_id, member_user_id, task_source, task_key)
);
```

## Логирование

Все события логируются:
```
2026-05-10 17:37:00 - INFO - Received Flyer webhook: {...}
2026-05-10 17:37:01 - INFO - ✅ Rewarded user 123456789 for Flyer task flyer_task_123
2026-05-10 17:37:02 - WARNING - ⚠️ User 123456789 unsubscribed from task flyer_task_123
```

## Мониторинг

### Health Check
**URL:** `GET /health`

**Ответ:**
```json
{
  "status": "healthy"
}
```

### Информация о сервисе
**URL:** `GET /`

**Ответ:**
```json
{
  "service": "DashPartner Webhook Server",
  "status": "running",
  "endpoints": {
    "flyer": "/flyer_webhook",
    "tgrass": "/tgrass_webhook",
    "health": "/health"
  }
}
```

## Преимущества автоматической проверки

1. **Мгновенное начисление** - награда приходит сразу после подписки
2. **Снижение нагрузки** - не нужно постоянно опрашивать API
3. **Точность** - события приходят напрямую от сервисов
4. **Масштабируемость** - вебхуки обрабатываются асинхронно
5. **Контроль отписок** - автоматическое обнаружение и предупреждение

## Troubleshooting

### Вебхуки не приходят
1. Проверьте, что webhook сервер запущен
2. Проверьте доступность URL извне (используйте ngrok для локальной разработки)
3. Проверьте логи сервера

### Награды не начисляются
1. Проверьте, что задание существует в `task_assignments`
2. Проверьте, что задание не было выполнено ранее
3. Проверьте логи: `database.reward_specific_task()` должен вернуть `True`

### Ошибки подписи
1. Проверьте, что секретный ключ совпадает с настройками в сервисе
2. Проверьте формат подписи (должен быть hex)

## TODO / Улучшения

- [ ] Реализовать списание награды при отписке
- [ ] Добавить систему штрафов за повторные отписки
- [ ] Улучшить логику получения chat_id для TGrass
- [ ] Добавить retry механизм для неудачных уведомлений
- [ ] Добавить метрики и мониторинг (Prometheus)
- [ ] Добавить rate limiting для защиты от DDoS
