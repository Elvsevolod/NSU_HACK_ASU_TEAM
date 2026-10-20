# Первичные контракты

Контракты проверены чтением официальных Java21 API и Spring reference через Context7; приложения/JVM не запускались. Spring current reference7.0.9 не доказывает точную разрешённую транзитивную версию cart Boot4.0.6.

- Java21 Stream: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Stream.html
- Java21 Optional: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Optional.html
- Java21 Collection/List/HashSet: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Collection.html
- Throwable: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Throwable.html
- LocalDateTime: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/time/LocalDateTime.html
- Spring MVC exception specificity/arguments: https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-controller/ann-exceptionhandler.html
- RestTemplate request factory/PATCH: https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/web/client/RestTemplate.html
- OrderColumn contiguous positions: https://jakarta.ee/specifications/platform/9/apidocs/jakarta/persistence/ordercolumn

Case-insensitive SQL column lookup ограничен объявленными CREATE identifiers, а не угадыванием полей по домену. Version-specific full JDK/ORM behavior не заявлен.
