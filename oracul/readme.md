# 🎯 Python Price Generator для DEX

Компактный и универсальный генератор цен для децентрализованной биржи с поддержкой Router архитектуры.

## 🌟 Особенности

- **Router интеграция** - все обновления Oracle через Router контракт
- **Адаптивная волатильность** - автоматический расчет на основе цены токена
- **Volatile events** - случайные ценовые шоки для тестирования
- **Circuit breaker защита** - автоматический fallback при превышении лимитов
- **Real-time мониторинг** - живая статистика цен и изменений
- **Система pause/unpause** - автоматическая обработка экстренных остановок

## 📦 Установка

```bash
# Установить зависимости
pip install web3 eth-account

# Убедиться что контракты развернуты
npm run full-deploy
```

## 🚀 Быстрый старт

### Базовый запуск
```bash
python price_generator.py
```

### С параметрами командной строки
```bash
python price_generator.py --update-interval 3 --volatility 1.5 --config ./config/deployed-config.json
```

### Программное использование
```python
from price_generator import PriceGenerator

# Создание генератора
generator = PriceGenerator("./config/deployed-config.json")

# Настройка параметров
generator.configure(
    update_interval=5,
    volatility_multiplier=1.2,
    enable_volatile_events=True
)

# Инициализация и запуск
await generator.initialize()
await generator.start()
```

## ⚙️ Параметры конфигурации

### PriceConfig параметры

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `update_interval` | int | 5 | Интервал обновления цен (секунды) |
| `display_interval` | int | 1 | Интервал обновления дисплея (секунды) |
| `history_size` | int | 100 | Размер истории цен для статистики |
| `volatility_multiplier` | float | 1.0 | Множитель волатильности (1.0 = норма) |
| `enable_volatile_events` | bool | True | Включить случайные ценовые шоки |
| `volatile_event_probability` | float | 0.001 | Вероятность volatile event за цикл |
| `max_price_change` | float | 0.5 | Максимальное изменение цены за раз |
| `min_price` | float | 0.01 | Минимальная цена токена |

### Методы конфигурации

```python
# Изменение одного параметра
generator.configure(update_interval=3)

# Изменение нескольких параметров
generator.configure(
    update_interval=10,
    volatility_multiplier=2.0,
    enable_volatile_events=False
)

# Проверка текущих настроек
print(generator.price_config.update_interval)
```

## 🎮 Режимы работы

### 1. Консервативный режим
```python
generator.configure(
    update_interval=10,
    volatility_multiplier=0.5,
    enable_volatile_events=False,
    max_price_change=0.1
)
```
**Использование**: Стабильная торговля, минимальные колебания

### 2. Агрессивный режим  
```python
generator.configure(
    update_interval=2,
    volatility_multiplier=3.0,
    enable_volatile_events=True,
    volatile_event_probability=0.01
)
```
**Использование**: Тестирование системы безопасности

### 3. Тестовый режим
```python
generator.configure(
    update_interval=1,
    volatility_multiplier=5.0,
    enable_volatile_events=True,
    max_price_change=1.0
)
```
**Использование**: Стресс-тестирование, демонстрации

## 📊 Автоматическая волатильность

Система автоматически рассчитывает волатильность на основе цены токена:

| Цена токена | Базовая волатильность | Пример |
|-------------|----------------------|--------|
| ≥ $10,000 | 4% | Bitcoin, дорогие активы |
| ≥ $10 | 5% | Ethereum, крупные токены |
| ≤ $2 | 0.1% | Стейблкоины |
| Остальные | 3% | Обычные токены |

Финальная волатильность = `базовая × volatility_multiplier`

## 🚨 Volatile Events

Случайные ценовые шоки для тестирования системы:

```python
# Ручной запуск события
await generator.generate_volatile_event('ETH', multiplier=2.0)

# Настройка автоматических событий
generator.configure(
    enable_volatile_events=True,
    volatile_event_probability=0.005  # 0.5% шанс за цикл
)
```

### Типы событий
- **Pump**: Резкий рост цены на 10-50%
- **Dump**: Резкое падение на 10-50%
- **Circuit breaker trigger**: Превышение лимитов Oracle

## 📈 Мониторинг и статистика

### Консольный дисплей
```
================================================================================
 LIVE PRICE FEED via Router [🟢 OPERATIONAL]
================================================================================
Symbol    Price           Change%     24h Low     24h High
--------------------------------------------------------------------------------
ETH       $2,547.123456   +1.85%      $2,401.15   $2,601.89
CAPY      $1.001234       -0.12%      $0.998765   $1.004321
QUOK      $45,123.789000  +2.34%      $44,001.23  $46,789.01
--------------------------------------------------------------------------------
Last update: 15:42:31 | Updates: 1,247
Press Ctrl+C to stop
```

### Программный доступ к статистике
```python
# Получить статистику по токену
stats = generator.price_history['ETH'].get_stats()
print(f"ETH: ${stats['current']:.2f} ({stats['change']:+.2f}%)")

# Текущие цены всех токенов
for symbol, price in generator.current_prices.items():
    print(f"{symbol}: ${price:.6f}")
```

## 🔧 CLI параметры

```bash
python price_generator.py [OPTIONS]

OPTIONS:
  --config PATH              Путь к config файлу [./config/deployed-config.json]
  --rpc-url URL             RPC endpoint [http://localhost:8545]
  --private-key KEY         Приватный ключ keeper
  --update-interval INT     Интервал обновления в секундах [5]
  --volatility FLOAT        Множитель волатильности [1.0]
  --no-events              Отключить volatile events
  --quiet                  Минимальный вывод
  --verbose                Подробные логи
  --help                   Показать справку
```

### Примеры использования

```bash
# Быстрый режим с высокой волатильностью
python price_generator.py --update-interval 2 --volatility 2.0

# Консервативный режим без событий
python price_generator.py --update-interval 15 --volatility 0.3 --no-events

# Кастомный RPC и приватный ключ
python price_generator.py --rpc-url http://custom:8545 --private-key 0x123...

# Тихий режим для автоматизации
python price_generator.py --quiet --update-interval 10
```

## 🏗️ Архитектура

### Структура классов
```
PriceGenerator
├── PriceConfig          # Конфигурация параметров
├── TokenConfig         # Настройки токенов  
├── PriceHistory        # История и статистика
├── Web3 Integration    # Blockchain подключение
└── Router Proxy        # Oracle обновления
```

### Workflow
1. **Инициализация** - загрузка config, подключение к сети
2. **Генерация цен** - расчет новых цен с волатильностью
3. **Batch обновление** - отправка всех цен через Router
4. **Fallback** - индивидуальные обновления при ошибках
5. **Мониторинг** - отображение статистики и истории

## 🔒 Безопасность и обработка ошибок

### Автоматическая обработка
- **Circuit breaker** - переход на индивидуальные обновления
- **System pause** - ожидание разблокировки системы
- **Network errors** - retry логика с экспоненциальным backoff
- **Gas optimization** - динамическое управление газом

### Логирование
```python
# Уровни логирования
logging.INFO    # Обычные операции
logging.WARNING # Проблемы, но работа продолжается  
logging.ERROR   # Критические ошибки

# Примеры сообщений
INFO - ✅ Batch update successful: 5 prices
WARNING - ❌ ETH: Circuit breaker triggered  
ERROR - Failed to connect to RPC endpoint
```

## 🧪 Тестирование

### Unit тесты
```bash
python -m pytest test_price_generator.py -v
```

### Интеграционные тесты
```bash
# Тест с локальной сетью
python test_integration.py --network localhost

# Тест volatile events
python test_volatile_events.py --duration 60
```

### Стресс-тест
```python
# Максимальная нагрузка
generator.configure(
    update_interval=1,
    volatility_multiplier=10.0,
    volatile_event_probability=0.1
)
```

## 🔄 Интеграция с другими компонентами

### Keeper Service
```python
# Синхронизация с keeper
generator.configure(update_interval=5)  # Keeper проверяет каждые 5 сек
```

### Trading Demo
```python
# Для демонстраций
generator.configure(
    volatility_multiplier=2.0,
    enable_volatile_events=True
)
```

### Production
```python
# Продакшн настройки
generator.configure(
    update_interval=30,
    volatility_multiplier=0.8,
    enable_volatile_events=False
)
```

## 📝 API Reference

### PriceGenerator
```python
class PriceGenerator:
    def __init__(config_path: str)
    def configure(**kwargs)
    async def initialize(rpc_url: str, private_key: str)
    async def start()
    def stop()
    async def generate_volatile_event(symbol: str, multiplier: float)
```

### PriceHistory  
```python
class PriceHistory:
    def add(price: float, timestamp: float)
    def get_stats() -> Dict[str, float]
```

## 🐛 Troubleshooting

### Проблема: "Failed to connect to RPC"
```bash
# Проверить что Hardhat запущен
npx hardhat node

# Или указать другой RPC
python price_generator.py --rpc-url http://localhost:8545
```

### Проблема: "Price change too large"
```python
# Уменьшить волатильность
generator.configure(volatility_multiplier=0.5)

# Или отключить события
generator.configure(enable_volatile_events=False)
```

### Проблема: "System paused"
```bash
# Разблокировать систему
npm run unpause

# Генератор автоматически возобновит работу
```

### Проблема: "Transaction failed"
```python
# Проверить gas settings в коде
# Увеличить gas limit или gas price
```

## 🚀 Production Deployment

### Docker
```dockerfile
FROM python:3.9-slim
COPY price_generator.py .
COPY requirements.txt .
RUN pip install -r requirements.txt
CMD ["python", "price_generator.py", "--config", "/config/deployed-config.json"]
```

### Systemd Service
```ini
[Unit]
Description=DEX Price Generator
After=network.target

[Service]
Type=simple
User=dex
WorkingDirectory=/opt/dex
ExecStart=/usr/bin/python price_generator.py --config /etc/dex/config.json
Restart=always

[Install]
WantedBy=multi-user.target
```

### Monitoring
```bash
# Healthcheck endpoint
curl http://localhost:8080/health

# Metrics collection
python price_generator.py --metrics-port 9090
```

---

**🎯 Готов к использованию! Компактная, универсальная и мощная система генерации цен для DEX.**