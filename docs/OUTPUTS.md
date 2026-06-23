# Research Mode Outputs

[English](#english) | [Русский](#русский)

## English

Research Mode separates expected outputs, candidate artifacts, and delivered
outputs. This avoids guessing file roles from names, extensions, MIME strings,
or prose.

### Expected Outputs

Expected user-facing outputs live in `working_memory.output_contract.outputs[]`.

Example:

```json
{
  "outputs": [
    {
      "id": "report",
      "role": "primary_deliverable",
      "required": true,
      "media_type": "application/pdf"
    },
    {
      "id": "sources",
      "role": "supporting_deliverable",
      "required": true,
      "media_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    }
  ],
  "quality_checks": ["comparative_matrix"]
}
```

Rules:

- `id` is an explicit stable identifier chosen by the caller or worker.
- `role` is a small system role, not a file format.
- `required` defaults to true.
- `media_type` is an open string when explicitly supplied.
- absence of `media_type` means Research Mode should not validate media type.

### Candidate Artifacts

Candidate artifacts appear during finalization as
`finalization.candidate_artifacts`. They point to task-local files or
directories that can be reviewed.

```json
{
  "id": "report",
  "path": "workspace/outputs/report.pdf",
  "role": "primary_deliverable",
  "media_type": "application/pdf",
  "derived_from": "report_source",
  "visibility": "user_facing"
}
```

Validation checks explicit ids, roles, task-local paths, readability, non-empty
files, and declared relations. It does not infer a role from a filename,
extension, title, note, or list order.

### Delivery Outputs

Delivered or review-ready user-facing files are recorded in `delivery.outputs[]`.
Older integrations may still read `delivery.primary_file` and
`delivery.attachments`; those fields are compatibility mirrors.

```json
{
  "outputs": [
    {
      "id": "report",
      "path": "workspace/outputs/report.pdf",
      "role": "primary_deliverable",
      "media_type": "application/pdf"
    }
  ]
}
```

### Provenance Links

`source_for` and `derived_from` are explicit links between artifact ids.

- `derived_from`: this artifact was produced from another artifact.
- `source_for`: this artifact is a source for another artifact.

Research Mode does not infer these links from matching filenames, shared
extensions, similar text, or ordering.

### Legacy Fields

These fields remain readable for old states but should not be the main model for
new structured tasks:

- `--deliverable-kind`;
- `working_memory.output_contract.kind`;
- `finalization.primary_deliverable_kind`;
- `deliverable_decision`.

New tasks should prefer `output_contract.outputs[]` and `delivery.outputs[]`.

### Common Failure Reasons

- `missing_reviewable_artifact`: expected reviewable file is missing.
- `output_contract_format_mismatch`: candidate artifact does not match the
  explicit output contract.
- `delivery_artifact_handoff_failed`: review/finalization and delivery disagree
  about the user-facing artifact.
- `delivery_channel_addressing_failed`: a delivery adapter received an invalid
  or unsupported target shape.

See `TROUBLESHOOTING.md` for repair steps.

## Русский

Research Mode разделяет ожидаемые результаты, артефакты-кандидаты и доставленные
результаты. Это убирает угадывание роли файла по имени, расширению, MIME-строке
или произвольному тексту.

### Ожидаемые результаты

Ожидаемые пользовательские результаты хранятся в
`working_memory.output_contract.outputs[]`.

Пример:

```json
{
  "outputs": [
    {
      "id": "report",
      "role": "primary_deliverable",
      "required": true,
      "media_type": "application/pdf"
    },
    {
      "id": "sources",
      "role": "supporting_deliverable",
      "required": true,
      "media_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    }
  ],
  "quality_checks": ["comparative_matrix"]
}
```

Правила:

- `id` — явный стабильный идентификатор, выбранный вызывающей стороной или
  рабочей итерацией.
- `role` — небольшая системная роль, а не формат файла.
- `required` по умолчанию считается true.
- `media_type` — открытая строка, если она явно задана.
- отсутствие `media_type` означает, что Research Mode не должен проверять MIME.

### Артефакты-кандидаты

Артефакты-кандидаты появляются во время финальной проверки. Они указывают на
файлы или директории внутри задачи, которые можно показать на ревью.

```json
{
  "id": "report",
  "path": "workspace/outputs/report.pdf",
  "role": "primary_deliverable",
  "media_type": "application/pdf",
  "derived_from": "report_source",
  "visibility": "user_facing"
}
```

Проверка смотрит на явные id, роли, пути внутри задачи, читаемость, непустые
файлы и объявленные связи. Она не выводит роль из имени файла, расширения,
заголовка, заметки или порядка в списке.

### Доставленные результаты

Пользовательские файлы, доставленные или готовые к ревью, записываются в
`delivery.outputs[]`. Старые интеграции могут читать `delivery.primary_file` и
`delivery.attachments`; эти поля остаются зеркалом для совместимости.

```json
{
  "outputs": [
    {
      "id": "report",
      "path": "workspace/outputs/report.pdf",
      "role": "primary_deliverable",
      "media_type": "application/pdf"
    }
  ]
}
```

### Связи происхождения

`source_for` и `derived_from` — явные ссылки между id артефактов.

- `derived_from`: этот артефакт получен из другого артефакта.
- `source_for`: этот артефакт является источником для другого артефакта.

Research Mode не выводит эти связи из похожих имён файлов, общих расширений,
похожего текста или порядка в списке.

### Legacy-поля

Эти поля остаются читаемыми для старых состояний, но не должны быть основной
моделью для новых структурированных задач:

- `--deliverable-kind`;
- `working_memory.output_contract.kind`;
- `finalization.primary_deliverable_kind`;
- `deliverable_decision`.

В новых задачах лучше использовать `output_contract.outputs[]` и
`delivery.outputs[]`.

### Частые причины ошибок

- `missing_reviewable_artifact`: нет ожидаемого файла для ревью.
- `output_contract_format_mismatch`: артефакт-кандидат не совпадает с явным
  контрактом результата.
- `delivery_artifact_handoff_failed`: ревью/финальная проверка и доставка
  расходятся по пользовательскому артефакту.
- `delivery_channel_addressing_failed`: адаптер доставки получил неподдержанную
  форму цели.

Шаги восстановления описаны в `TROUBLESHOOTING.md`.
