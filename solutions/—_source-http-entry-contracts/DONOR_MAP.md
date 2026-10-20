# Проверка доноров

Использован существующий readonly inventory из внешней диагностики; полного повторного обхода всех архивов не делали. Донор — источник проверяемого механизма, не замена текущего ядра.

| Донор | Проверка на №33 | Решение |
| --- | --- | --- |
| №13 `polygraph/spring_config.py` | Прочитан модуль: local/source priorities, placeholders, per-module profiles, ordered supplied propertySources, external environment. Новый before — 10 failed / 1 passed; after — 11/11 плюс 25 HTTP/framework controls. | Идеи перенесены в `analyzer/source_configuration.py` через текущие config_entry facts. PyYAML/javaproperties и старый IR не копировались. Полный Environment adapter не объявлен. |
| №13 pure JS | TT current probe: admin callback выбран; client request блокирует production guard. Explicit login без supplied clock останавливается до успешного callback. | Доказанного первого дефекта pure JS здесь нет. Перенос UTF‑16/coercion/JSON-omission механизмов отложен до минимального контрпримера. Guard не обходили. |
| №20 request-component binding | `Engine.bind_request`, Request/RequestInputs и tests request_components/http_request_boundary/row_request_binding присутствуют; полный набор проходит. | Повторный wholesale перенос не нужен. Новые headers добавлены в explicit request parser, нижний binder сохранён. |
| №23 lvalue evaluation | `Engine.lvalue`, `lvalue_valid`, `lvalue_read`, `lvalue_write`, tests lvalue_evaluation присутствуют и проходят. | Сохранено; отдельного отсутствующего механизма не обнаружено. |
| Прочие старые варианты | Их названия/число отсутствующих файлов не доказывают потерю функции в новом IR. | Backlog до source-backed зависимости; массовое копирование не выполнялось. |

Новые runtime-изменения — в [точном патче](development/review33-final/parent32-to33.patch). Before/after команды, code hashes и stdout/stderr: `benchmark/scoped-config-before`, `benchmark/scoped-config-after`, `benchmark/repository-shapes-before-02`, `benchmark/repository-shapes-after`, `benchmark/computed-base64-before-02`, `benchmark/computed-base64-after`. Исторические неуспешные попытки сохранены отдельно.

[Spring Boot configuration docs](https://github.com/spring-projects/spring-boot/blob/main/documentation/spring-boot-docs/src/docs/antora/modules/reference/pages/features/external-config.adoc) проверены через Context7. Из них использованы profile-specific priority, last-wins profiles и `${name:default}`; поддержка всех остальных возможностей из документа не заявляется.
