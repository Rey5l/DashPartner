import matplotlib
matplotlib.use('Agg')  # Используем backend без GUI
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from pathlib import Path
import os

# Настройка шрифтов для поддержки кириллицы
plt.rcParams['font.family'] = 'DejaVu Sans'


def generate_statistics_chart(data: list[tuple], period_days: int, chart_type: str = "users") -> str:
    """
    Генерирует график статистики за указанный период

    Args:
        data: Список кортежей (дата, значение)
        period_days: Период в днях (10, 20, 30)
        chart_type: Тип графика (users, tasks, resources, contests)

    Returns:
        Путь к сгенерированному изображению
    """
    if not data:
        # Если нет данных, создаем пустой график
        data = [(datetime.now() - timedelta(days=i), 0) for i in range(period_days)]

    # Создаем фигуру и оси
    fig, ax = plt.subplots(figsize=(12, 6))

    # Извлекаем даты и значения
    dates = [item[0] if isinstance(item[0], datetime) else datetime.fromisoformat(str(item[0])) for item in data]
    values = [item[1] for item in data]

    # Строим график
    ax.plot(dates, values, marker='o', linestyle='-', linewidth=2, markersize=6, color='#2196F3')
    ax.fill_between(dates, values, alpha=0.3, color='#2196F3')

    # Настройка заголовка в зависимости от типа
    titles = {
        "users": f"Статистика пользователей за {period_days} дней",
        "tasks": f"Статистика заданий за {period_days} дней",
        "resources": f"Статистика ресурсов за {period_days} дней",
        "contests": f"Статистика конкурсов за {period_days} дней",
        "admin": f"Общая статистика за {period_days} дней"
    }
    ax.set_title(titles.get(chart_type, f"Статистика за {period_days} дней"), fontsize=16, fontweight='bold')

    # Настройка осей
    ax.set_xlabel('Дата', fontsize=12)
    ax.set_ylabel('Количество', fontsize=12)
    ax.grid(True, alpha=0.3, linestyle='--')

    # Форматирование дат на оси X
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, period_days // 10)))
    plt.xticks(rotation=45, ha='right')

    # Добавляем значения на график
    for i, (date, value) in enumerate(zip(dates, values)):
        if i % max(1, len(dates) // 10) == 0:  # Показываем каждое N-ое значение
            ax.annotate(f'{int(value)}',
                       xy=(date, value),
                       xytext=(0, 10),
                       textcoords='offset points',
                       ha='center',
                       fontsize=9,
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))

    # Улучшаем внешний вид
    plt.tight_layout()

    # Создаем директорию для графиков, если её нет
    charts_dir = Path("data/charts")
    charts_dir.mkdir(parents=True, exist_ok=True)

    # Генерируем уникальное имя файла
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{chart_type}_{period_days}d_{timestamp}.png"
    filepath = charts_dir / filename

    # Сохраняем график
    plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)

    return str(filepath)


def cleanup_old_charts(max_age_hours: int = 24):
    """
    Удаляет старые графики

    Args:
        max_age_hours: Максимальный возраст файлов в часах
    """
    charts_dir = Path("data/charts")
    if not charts_dir.exists():
        return

    now = datetime.now()
    for file in charts_dir.glob("*.png"):
        file_age = now - datetime.fromtimestamp(file.stat().st_mtime)
        if file_age.total_seconds() > max_age_hours * 3600:
            try:
                file.unlink()
            except Exception as e:
                print(f"Failed to delete old chart {file}: {e}")
