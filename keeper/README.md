# DEX Python Keeper

Автоматизированный keeper сервис на Python для мониторинга и исполнения ордеров/ликвидаций в децентрализованной бирже.

## Особенности

- 🔄 **Автоматическое исполнение** лимитных и стоп-лосс ордеров
- ⚡ **Ликвидация позиций** при достижении пороговых значений
- 📊 **Детальная диагностика** балансов, цен Oracle и состояния контрактов
- 🛡️ **Retry механизм** для надежности транзакций
- 🎛️ **Гибкая конфигурация** через файлы, CLI или переменные окружения
- 📝 **Полное логирование** всех операций
- 🚀 **Высокая производительность** с async/await архитектурой

## Установка

```bash
# Установить зависимости
pip install -r requirements.txt

# Проверить доступность контрактов (опционально)
python verify_deployment.py
```

## Варианты запуска

### 1. Стандартный режим (мониторинг + автоисполнение)
```bash
python main.py
```

### 2. С кастомными настройками
```bash
python main.py --order-interval 10 \
               --liquidation-threshold -80 \
               --log-level DEBUG \
               --rpc-url http://localhost:8545
```

### 3. Только мониторинг ордеров
```bash
python main.py --disable-liquidation
```

### 4. Только ликвидация позиций
```bash
python main.py --disable-orders
```

### 5. Тихий режим без диагностики
```bash
python main.py --disable-diagnostics --log-level WARNING
```

## Команды просмотра данных

### Статус keeper сервиса
```bash
python main.py --status
```
**Показывает**: адрес keeper, сеть, счетчики проверок, текущие настройки

### Все активные ордера
```bash
python main.py --orders
```
**Показывает**: список всех ордеров с типами, статусами и условиями исполнения

### Все открытые позиции
```bash
python main.py --positions
```
**Показывает**: позиции с PnL, кредитным плечом и статусом ликвидации

## Ручное управление

### Исполнить конкретный ордер
```bash
python main.py --execute-order 1
```

### Ликвидировать конкретную позицию
```bash
python main.py --liquidate-position 1
```

## Параметры конфигурации

### Основные параметры
- `--config` - путь к конфигурационному файлу (по умолчанию: `./config/deployed-config.json`)
- `--private-key` - приватный ключ keeper аккаунта
- `--rpc-url` - URL RPC провайдера
- `--log-level` - уровень логирования (`DEBUG`, `INFO`, `WARNING`, `ERROR`)

### Интервалы мониторинга
- `--order-interval` - интервал проверки ордеров в секундах (по умолчанию: 5)
- `--position-interval` - интервал проверки позиций в секундах (по умолчанию: 8)
- `--liquidation-threshold` - порог ликвидации в процентах (по умолчанию: -90%)

### Управление модулями
- `--disable-orders` - отключить автоисполнение ордеров
- `--disable-liquidation` - отключить автоликвидацию позиций
- `--disable-diagnostics` - отключить вывод диагностической информации

## Автоматические функции

### Мониторинг ордеров
- Проверяет условия исполнения каждые 5 секунд (настраивается)
- Автоматически исполняет ордера при выполнении условий
- Поддерживает лимитные ордера и стоп-лоссы
- Retry механизм при ошибках транзакций

### Мониторинг позиций
- Отслеживает PnL всех открытых позиций
- Автоматически ликвидирует позиции при достижении порога убытков
- Учитывает кредитное плечо и маржинальные требования

### Диагностика системы
- Балансы keeper и пулов для всех токенов
- Цены и валидность данных Oracle
- Статус контрактов и сетевое подключение
- Периодические отчеты о состоянии системы

## Источники конфигурации

### 1. Конфигурационные файлы (приоритет: высокий)
```json
// config/deployed-config.json - основная конфигурация
{
  "contracts": { ... },
  "tokens": { ... },
  "accounts": { "keeper": "0x..." }
}

// config/keeper-config.json - credentials
{
  "private_key": "0x...",
  "rpc_url": "http://localhost:8545"
}
```

### 2. Переменные окружения (приоритет: средний)
```bash
export KEEPER_PRIVATE_KEY="0x..."
export RPC_URL="http://localhost:8545"
```

### 3. CLI параметры (приоритет: наивысший)
```bash
python main.py --private-key "0x..." --rpc-url "http://localhost:8545"
```

## Программное использование

### Базовое использование
```python
from keeper_service import KeeperService

keeper = KeeperService("./config/deployed-config.json")
await keeper.start()
```

### Кастомная конфигурация
```python
keeper = KeeperService()
keeper.update_config(
    order_check_interval=10,
    liquidation_threshold=-80,
    enable_diagnostics=True,
    log_level="DEBUG"
)
await keeper.start()
```

### Получение данных
```python
# Статус системы
status = keeper.get_status()
print(f"Running: {status['running']}")

# Информация об ордерах
orders = keeper.get_all_orders()
for order in orders:
    print(f"Order {order['id']}: {order['order_type']} - {order['should_execute']}")

# Информация о позициях
positions = keeper.get_all_positions()
for position in positions:
    print(f"Position {position['id']}: PnL {position['pnl_ratio']:.2f}%")
```

### Ручное управление
```python
# Исполнить ордер
success = await keeper.manual_execute_order(1)

# Ликвидировать позицию
success = await keeper.manual_liquidate_position("0x...", 1)

# Принудительная диагностика
keeper.force_diagnostics()
```

## Расширение функциональности

### Кастомные стратегии
```python
class CustomKeeperService(KeeperService):
    async def _check_orders(self):
        # Базовая проверка
        await super()._check_orders()
        
        # Дополнительная логика
        await self._check_arbitrage_opportunities()
        await self._rebalance_portfolio()
    
    async def _check_arbitrage_opportunities(self):
        # Поиск арбитражных возможностей
        pass
```

### Интеграция с внешними системами
```python
class MonitoringKeeperService(KeeperService):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.webhook_url = "https://your-monitoring.com/webhook"
    
    async def _execute_order_with_retry(self, order_id: int) -> bool:
        success = await super()._execute_order_with_retry(order_id)
        
        # Отправка уведомления
        await self._send_notification(f"Order {order_id} executed: {success}")
        return success
```

## Логирование и мониторинг

### Типы логов
- **INFO**: Успешные операции, статусы, диагностика
- **WARNING**: Неожиданные ситуации, retry попытки
- **ERROR**: Ошибки исполнения, проблемы подключения
- **DEBUG**: Детальная информация о вызовах контрактов

### Файлы логов
- **Консоль**: Все логи в реальном времени
- **keeper.log**: Постоянное хранение всех событий

### Мониторинг метрик
```python
status = keeper.get_status()
metrics = {
    'orders_checked': status['order_check_counter'],
    'positions_checked': status['position_check_counter'],
    'uptime': time.time() - keeper.start_time,
    'last_successful_execution': keeper.last_execution_time
}
```

## Безопасность

### Управление ключами
- Приоритет: CLI параметры > env переменные > конфиг файлы
- Автоматический выбор правильного ключа для keeper аккаунта
- Поддержка hardware wallets через расширения

### Сетевая безопасность
- Проверка подключения к правильной сети
- Валидация адресов контрактов при загрузке
- Timeout и retry для сетевых вызовов

### Операционная безопасность
- Graceful shutdown по SIGINT/SIGTERM
- Валидация всех входных параметров
- Логирование всех критических операций

## Отладка и диагностика

### Проверка развертывания
```bash
python verify_deployment.py
```

### Тестирование контрактов
```bash
python test_contract_calls.py
```

### Отладочный режим
```bash
python main.py --log-level DEBUG --disable-diagnostics
```


## Производительность

### Оптимизации
- Async/await для неблокирующих операций
- Батчинг проверок ордеров (до 10 за раз)
- Кэширование ABI контрактов
- Интеллектуальные интервалы проверок

### Мониторинг производительности
- Время выполнения операций
- Газовые затраты на транзакции
- Частота успешных/неуспешных операций
- Нагрузка на RPC провайдера

## Совместимость

- **Python**: 3.8+
- **Web3.py**: 6.0+
- **Сети**: Ethereum, Polygon, BSC, Arbitrum, и другие EVM совместимые
- **RPC провайдеры**: Infura, Alchemy, локальные ноды
- **Интеграция**: Полная совместимость с JS версией keeper
