> Историческое описание генератора. Неподтверждённые реализации и команды не означают готовность. Проверенный запуск: [README.md](../README.md); результаты и пробелы: [AUDIT.md](AUDIT.md).

# Бэкапы и восстановление

## Резервное копирование БД
```bash
docker exec -t kontur_db pg_dumpall -c -U kontur > dump_`date +%Y-%m-%d`.sql
```

## Восстановление БД
```bash
cat dump_`date +%Y-%m-%d`.sql | docker exec -i kontur_db psql -U kontur
```

## Резервное копирование файлов (MinIO)
Настроить синхронизацию бакетов через `mc mirror`.
