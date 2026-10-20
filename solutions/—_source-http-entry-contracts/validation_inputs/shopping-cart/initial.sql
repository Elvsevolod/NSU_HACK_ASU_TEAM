USE `payment-service`;
CREATE TABLE `payments` (
 `id` bigint,
 `order_id` bigint,
 `customer_id` bigint,
 `amount` decimal(10,2),
 `payment_method` varchar(30),
 `status` varchar(30),
 `created_at` timestamp
) ENGINE=InnoDB;
INSERT INTO `payments` VALUES (21,11,7,12.50,'CREDIT_CARD','APPROVED','2026-10-17 12:00:00'),(23,11,7,12.50,'CREDIT_CARD','REJECTED','2026-10-17 11:00:00'),(22,12,7,25.00,'DEBIT_CARD','APPROVED','2026-10-17 13:00:00');
USE `order-service`;
CREATE TABLE `orders` (
 `id` bigint,
 `customer_id` bigint,
 `customer_name` varchar(80),
 `customer_email` varchar(80),
 `status` varchar(30),
 `created_at` timestamp
) ENGINE=InnoDB;
INSERT INTO `orders` VALUES (11,7,'Ari','ari@example.test','PAID','2026-10-17 10:00:00'),(12,7,'Ari','ari@example.test','PAID','2026-10-17 10:30:00');
CREATE TABLE `order_details` (
 `id` bigint,
 `order_id` bigint,
 `product_id` bigint,
 `product_name` varchar(80),
 `quantity` int,
 `unit_price` decimal(10,2)
) ENGINE=InnoDB;
INSERT INTO `order_details` VALUES (31,11,51,'Notebook',2,6.25),(32,12,52,'Lamp',1,25.00);
