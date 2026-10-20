# PiggyMetrics oracle v3: семантика и проекция отражённых getter

Независимый source-only читатель: `/root/oracle_reader`, в ранее разрешённых пользователем границах проверки PiggyMetrics. DeepSeek и другие агенты не использованы. Код, тесты и файлы runtime outputs анализатора не читались; приложения/JVM не запускались. Из новой аналитики прочитаны замечание §3.7, §5 и план проекции §7. Первоначальное указание §10 было уточнено основным агентом: такого раздела в данном файле нет.

**Решение: v3 исправляет только проекцию эталона.** Ранее отражённые getter были семантически значимыми callbacks с проверяемыми результатами, но ошибочно попадали в экспортируемые executes. По `tt-challenge/REFERENCE.md:64` getter, вызванный библиотекой лишь через отражение, в ответ не включается. Метод, реально вызванный Java-кодом, сохраняется, даже если сериализатор отдельно вызывает тот же getter. Это правило основано на происхождении конкретного вызова, а не на префиксе имени метода.

Исправление проекции не доказывает, что эти callbacks были причиной какого-либо score. Для выбора ожиданий runtime outputs не использовались.

## Файлы и неизменность семантики

| Файл | SHA-256 |
|---|---|
| `piggymetrics-main.semantic-v2.json` | `499f635f5df70eafafc6ef0b424266949d62f5886a77b4af5c9e9f1cf82a9e8d` |
| `piggymetrics-additional.semantic-v2.json` | `5417ee09198c59c672589cbd1a448544259bb1c4c87f6dfea1dcb94519ebc63b` |
| `piggymetrics-main.oracle-v3.json` | `c36a495c36b9bcdf89b42fa3fbcad84b9e7dab94633faafc8fbd6c2aa2001a73` |
| `piggymetrics-additional.oracle-v3.json` | `fd2d53ef7e74b198aaefc1bffc23865bb3a9b65b5af6a7a348f44d295990e1a9` |

Первые два файла — точные побайтовые копии замороженных reviewed-v2. Оригиналы в `experiments/20261018-causal-execution-repair/real-journey/` не изменены. У v3 сохранены все исходные row-поля, кроме запрошенной замены `edges`; исходные root-поля, кроме номера версии и соответствующих rows, также сохранены. В частности, wire, identity, arguments, состояние, abstract unknown, результаты, статусы, defaults, условия окружения и неподдерживаемые границы не изменены.

В каждой строке v3:

- `semantic_edges` — **ровно прежний v2 edge contract**, с прежним отсутствием отражённых constructor edges. Это не обещание полного графа JVM.
- `edges` — проекция для формата организаторов.
- `reflection_edges` — отражённые getter roots, представленные в v2. Множество может пересекаться с `edges`: source Java и сериализатор способны вызвать один method ID. Это набор подавленных callback roots, а не обязательно разность множеств.
- `projection_difference.removed_edges` — только действительно удалённые из ответа IDs.
- `semantic_callbacks` — отдельные ожидаемые role/method/trigger/result/outcome, source symbol/body evidence и связь с receiver/value. Getter callback не становится необязательным из-за исключения его корня из ответа.
- `source_invocation_evidence` — независимо сопоставленные Java call sites для всех прежних source-to-source calls.

Для каждого из четырёх видов рёбер каждой строки проверено:

`union(edges, reflection_edges) == semantic_edges`.

В этих oracle reflected getter **calls отсутствуют**: v2 уже не создавал фиктивных source caller → getter связей для запуска сериализатором. Поэтому calls/remote/data во всех 11 строках неизменны. Восстановление v2 не должно добавлять constructor edges или любые прочие lifecycle события, которых в замороженном edge contract не было.

## Основания по сохранённому input Java

Источник проверки — `experiments/20261018-causal-execution-repair/real-journey/input/`, а не код извлечения/исполнения анализатора. Хеши всех 49 сохранённых Java-файлов приведены в manifest и v3. Все 50 source symbols main v2 и 56 symbols additional v2 сопоставлены с точными декларациями input; для файлов, имеющих hash в v2, совпадение проверено.

Ниже сокращённые paths Java относятся к `input/<module>/<module>/src/main/java/com/piggymetrics/<package>/`.

- `account/service/AccountServiceImpl.java:48–49,61`: Java сам вызывает `account.User.getUsername`. На шаге 1 достигается также строка 61; на шагах 5/6 отказ происходит раньше. Эти getter executes и source calls остаются.
- `AccountServiceImpl.java:67`: `account.Account.getName` вычисляется при конкатенации аргумента Logger. Вызов происходит независимо от включённости уровня логирования. На шаге 1 он остаётся и как executes, и как Java call; отдельный response getter root подавлен.
- `AccountServiceImpl.java:55`: `Currency.getDefault` — явно вызванный static source helper. Он сохраняется; исключение методов по одному имени `get*` было бы неверно.
- `auth/service/UserServiceImpl.java:27,30,35`: нормальное создание на шаге 1 реально вызывает auth `User.getUsername` и `getPassword`; строка 30 передаёт исходный пароль в encoder. Это не reflection-only getter.
- `auth/UserServiceImpl.java:27–28`: при конфликте шага 6 `getUsername` вызывается для lookup и для сообщения исключения существующего пользователя. `getPassword:30` на этом пути не достигнут. Account DTO getter `account.User.getPassword` нужен только Feign serialization, поэтому исключается из проекции шага 6. Различие account/auth FQN сохраняется.
- `account/AccountServiceImpl.java:81–84`: шаг 3 действительно вызывает `Account.getIncomes/getExpenses/getSaving/getNote` на входном update. Эти IDs остаются, хотя Feign encoder позже читает те же property names уже у сохранённого account. `getName/getLastSeen` и вложенные Saving getter на шаге 3 нужны лишь сериализации; source Java их не вызывает.
- `account/controller/AccountController.java:21–22` и `AccountServiceImpl.java:37–39`: обычный GET только передаёт name и читает repository. Getter Account/Saving/Item после этого вызваны сериализатором. Поэтому на шагах 2/4/7 и в additional partial-list случае их корни уходят из projected executes; callback значения, unknown fields, исходные позиции и порядок списка продолжают проверяться.

Проверены тела property getter: Account, Saving, User и Item возвращают собственные поля. В callback expectations не придуманы дополнительные Java helper calls, SQL или побочные эффекты. Пять Item getters по source строкам 26/34/42/50/58 по-прежнему семантически исполняются отдельно для двух non-null Item; десять Item callbacks не превращаются в десять экспортируемых executions.

## Изменения по шагам

Числа ниже — размеры per-step множеств executes, не оценка сайта и не размер объединённого сценарного графа.

| Профиль / шаг | v2 semantic executes | v3 projected executes | Причина |
|---|---:|---:|---|
| Main 1 | 32 | 21 | Удалены пять Account getter кроме Java-вызванного getName, пять Saving getter и account.User.getPassword |
| Main 2 | 13 | 2 | Шесть Account и пять Saving getter только response serialization |
| Main 3 | 33 | 26 | Удалены Account.getName/getLastSeen и пять Saving getter; четыре Java update getter сохранены |
| Main 4 | 13 | 2 | Getter только response serialization |
| Main 5 | 6 | 6 | Java getUsername, binding setters и source advice сохранены; отражённых getter нет |
| Main 6 | 11 | 10 | Удалён account.User.getPassword, нужный только Feign encoding; Java username getter сохранены |
| Main 7 | 13 | 2 | Getter только response serialization |
| Main 8 | 0 | 0 | Missing body отклонён до handler; getter нет |
| Additional invalid-saving-null | 1 | 1 | Source binding setter сохранён |
| Additional partly-known-real-list | 18 | 2 | Шесть Account, пять Saving и пять Item getter IDs — только отражённая serialization |
| Additional ambiguous-account-read | 0 | 0 | Request не выбран, исполнения нет; candidates не становятся union graph |

По main в сумме per-step удалены 52 getter executes; по additional — 16. Все 35 main source calls, два remote и девять data остаются. В partial-list всё ещё требуются 21 semantic serialization callback, включая десять Item callbacks с конкретными receiver positions и результатами. Список удалённых IDs для каждой строки хранится в manifest/v3.

## Границы, которые не расширялись

`REFERENCE:64` явно исключает отражённые **getter и constructors**, но не объявляет все library callbacks непроектируемыми. Поэтому прежние source setter roots сохранены. Source ControllerAdvice и Hystrix fallback тоже остаются: это бизнес-методы проекта, а не getter. Для них сохранены отдельные semantic callback role/outcome, без выдуманных source caller edges.

Из неявного создания DTO нельзя изобрести source constructor symbol. В используемых v2 maps declared DTO constructor IDs нет; отражённые constructor edges не добавлены ни в `semantic_edges`, ни в `reflection_edges`. `constructor_callback_uncertainty` явно фиксирует отсутствие доказанного source symbol/ожидания: это не утверждение, что объект появился без JVM construction. В частности, нельзя восстановить v2 простым добавлением всех lifecycle edges, если там обнаружатся constructors.

Существующие ограничения v2 сохранены: post-auth identities — предоставленные входы; выпуск OAuth/token verification не проверяется; часть framework error bodies не измеряется; отдельные случаи не доказывают полный NL grounding или переносимость. Данный source review подтверждает эталон проекции; он не является успешным прогоном анализатора и не закрывает общий implementation goal.
