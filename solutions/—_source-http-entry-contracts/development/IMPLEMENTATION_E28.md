# Проверенный снимок E28

Текущая правка завершена. E27 добавил source-native equipment/HTTP controls, отдельные static owners для двух пакетов и направление/throw lastIndexOf. В passive loss record появились source-proven read locations, callsite и конкретные request/provenance references. Текущий request после remote return больше не подменяется последним дочерним запросом.

В E28 generic opaque-List guard перехватывал stream() до создания ленивого native carrier. Последующий filter терял native lifecycle и попадал в opaque-call handler с потенциальным исполнением callback на неизвестном элементе. Пять строк передают stream/parallelStream обычному stream handler до opaque content guard. Terminal сохраняет явную boundary; callback и нормальный suffix не исполняются, возможные writes остаются в invalidation.

До исправления: benchmark/opaque-stream-boundary-before, два провала нового source fixture на E27. После: benchmark/opaque-stream-boundary-after; дополнительные null-consumer, Optional unknown, static join и write-filter witnesses в benchmark/readiness-edge-probes-after. Начальные fixture ошибки (внутренний __type__, opaque RequestBody и generic varargs cast) сохранены в отдельных captures; они не названы исправлениями движка.

Полный набор: benchmark/readiness-e28-full (2444); интеграции: benchmark/readiness-e28-integration (17). TT snapshot: development/stages/E28-opaque-stream-lifecycle; ответы и302 budget completions совпадают с E21/E25/E26/E27. Нового выигрыша в JSON нет. Парный CodeRank на E27 сохранён отдельно; на E28 модель повторно не проверялась и в default не включена.

По новой прямой команде пользователя приоритет меняется: короткие циклы от конкретной проблемы итогового графа до валидированного пакета и сайта. Тестовые счётчики не являются критерием успеха. Следующая задача: доказать путь вход→binding→HTTP/state/alternatives→export для одинаковых ответов E21/E25/E26 и сгруппировать все302 budget завершения по реальным причинам.

На сайт E28 пока не отправлен. Повтор одинакового submission запрещён новой командой пользователя. №32 и лучший пакет сохраняются; отдельные compilation/S0 training pilots не затрагиваются.
