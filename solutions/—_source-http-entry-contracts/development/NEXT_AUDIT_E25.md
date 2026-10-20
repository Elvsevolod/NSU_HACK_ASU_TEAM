# Продолжение после E25

Последний goal turn — progress: реализованы E22 literal source constraint и E23 repeat intent; actual HTTP500 reproducer выявил R06 проблему обычного grounder; E24 исправил все response consumers, E25 исправил переносимость тестов и прошёл actual compact extraction. Активная цель не завершена.

Источник требований только обновлённый Downloads/solution_31_models_and_static_analysis_review.md, SHA4a1c9f985808aacd4e35816d028779586407c13bf74f938df14a71b859a29592. Параметры path_limit4/constraints/completion/observed-union не менять. DeepSeek запрещён человеком. Новых агентов без отдельного разрешения нет.

Текущее: core2418/checker159/integration17. Source snapshots E21–E25 и diffs request-history-review-e25 сохранены. Compact solution-e25.zip SHAab2a7038eb8432ce557fac89286117bc6504cf8ba92ff0273099426a920e3b28 actual replay прошёл, offline0, все8 TT answers SHA95927fa5eb50b7d9f26d13a1c9e224bb2b803a9a6b07aa1c42996beaa15c371d. Полный аналитический v5 физически неизменён, относится к E21, SHAe2d204f8e2a97a57a7ec38f0b01feb5781cc3720e733905ca1aaa90509e601c7. Не выдавать его за полный E25.

Следующий приоритет R06: проверить failed/latest collection и ordinal после нового response filter; отсутствие metadata отдельно от false/unknown coverage; сохранить известные клиентские параметры после failed response. Исходный actual500 probe development/repros/r06_failed_response_probe.py теперь проходит; before/after captures сохранены. Engine histories имеют outcome и exploration, helper response_available учитывает их; bare legacy fixture rows остаются явно предоставленными observations без выдуманного complete proof. agree_completed по-прежнему строгий.

Не менять положительные проверки только ради green: ошибка HTTP500 не даёт нового ID, но неудачный GET не стирает ID из более раннего завершённого ответа. В двух E18 тестах теперь проверяется точная ссылка/digest на этот исходный response. State/SQL effects при failed response не удалялись, shadow view только ограничивает client-history values.

Далее провести построчный readiness audit R01–R08 из разделов11/12.1/12.2, проверив реальные test bodies/code/captures, а не одни counts. В начале R06 exact gates требовали этого общего пути, старые helper-specific tests были недостаточны. Не объявлять complete без аудита всех обязательств; не расширять задачу до полного JVM/SQL/NL engine.

Если нужны дальнейшие NL repairs: employment English сохраняет4/9 state-chain checks; значения review201/999 записаны через имя source сущности без слова id, текущий binder их пропускает. healthcare English после E23 имеет8/10 state-chain плюсfresh1/refusals2; не выбираются compound doctor+patient handlers. Предпочтительны независимые before controls и source-derived route labels через существующий structured_literals.literal_value(labels=...), с проверкой конфликтов и запретом fallback на старый ID после неоднозначных literals. Для compound нужны source DTO shape/route/input facts; не добавлять бизнес-переводы или mappings.

Все4 модельных runtime и E20 CodeRank same/expanded измерены. Последний парный model review относится к E20, не переименовывать его E25. При финальном сравнении на новой семантике снова закрепить code/protocol и применить старые thresholds, использовать уже проверенный local Encoder/weights; не подбирать по уже наблюдавшимся test данным. Default model rejected. Source missing-route preflight сохраняет честную boundary, runtime classpath/resource inventory отсутствует; произвольный404/body не выдумывать.

После новых изменений нужен новый compact replay и актуальный полный аналитический пакет/receipt; защищённые parent32/tt-challenge/sample/runs и все прежние ZIP сохранить. Git/site не изменять без нового прямого поручения.
