import csv
from pathlib import Path

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Импорт ингредиентов из CSV-файла'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            nargs='?',
            default='data/ingredients.csv',
            help='Путь к CSV-файлу',
        )

    def handle(self, *args, **options):
        file_path = Path(options['file_path'])

        if not file_path.exists():
            self.stdout.write(
                self.style.ERROR(
                    f'Файл не найден: {file_path}',
                ),
            )
            return

        ingredients = []

        with file_path.open(
            encoding='utf-8',
            newline='',
        ) as csv_file:
            reader = csv.reader(csv_file)

            for row in reader:
                if len(row) != 2:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Пропущена некорректная строка: {row}',
                        ),
                    )
                    continue

                name, measurement_unit = row

                ingredients.append(
                    Ingredient(
                        name=name.strip(),
                        measurement_unit=measurement_unit.strip(),
                    )
                )

        Ingredient.objects.bulk_create(
            ingredients,
            ignore_conflicts=True,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Импортировано ингредиентов: {len(ingredients)}',
            ),
        )
