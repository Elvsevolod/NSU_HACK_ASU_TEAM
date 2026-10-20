# Границы №31

- Полная TT NL цепочка поиск→booking→payment не пройдена. Source Set<Ticket> equality/hash, последующие distance/list consumer операции и раннее unknown состояние S6 описаны в benchmark/tt-frontier.json. Изолированные payment пробы не заменяют producer.
- Default path limit4 и общий completion reserve сохранены; observed-union содержит приближения. G06 checker-only эксперимент не включён. Скрытого E/C/R/D oracle нет.
- Cart проверен в explicit application-after-authentication scope. JWT/security/startup, полная validation и неизвестные framework configurations не объявлены поддержанными. Полная dependency/JVM сборка не выполнялась. V3 oracle — postimplementation regression extension; cart не holdout.
- Stream поддержан только для описанных sequential standard JDK операций и доказанных source типов. Custom namesakes, opaque membership/order, unsupported overload/parallel/identity и callbacks с непредставимыми эффектами дают границы. Нет заявления о полном Java21/JDK/Boot support.
- ORM physical storage ограничен известными scalar/enum/foreign-key columns и проверенными unchanged существующими children. Новые/изменённые cascade children, orphan/removal/provider dirty checking не выдумываются. Null entity поле не превращается в известный пустой read.
- MVC advice ordering/scoped ambiguity, неразрешённые @Bean factories/profiles/environment/deployment и многие библиотеки остаются unsupported. Диагностика не подавляется ради pass; для formatter locale/codec completeness сохраняются явные ограничения.
- BigDecimal точен для поддержанных операций/SQL lexemes; unsupported rounding/precision остаётся boundary. Diagnostic cycles представлены $cycle_ref только в отчёте, исходный heap/wire не меняется.
- Piggy/cart required-edge oracle не даёт полного precision/IoU. Legacy старые edge lists сохраняют extras относительно source formatter/MVC, эти extras были и в №30. Маленькие synthetic точные oracle не заменяют новый реальный проект.
- G15 not_run: нет полного нового реального пакета source+готовый skeleton+context+explicit/NL scenarios+pre-result oracle. Конкретный missing-input список — benchmark/holdout-availability.json.
- Время/RSS измерены на одной машине Darwin/arm64/Python3.11.9; Windows/Linux runtime не запускались. Нормализация Linux KiB проверена fixture. Полное время и память выше parent30; SLA/статистический тренд не заявлены.
- Не запускались target Java/JVM, Maven/Gradle, Docker/сервисы, модели, DeepSeek, внешние LLM API. Анализатору нужен готовый skeleton; его построение с нуля вне задачи.
