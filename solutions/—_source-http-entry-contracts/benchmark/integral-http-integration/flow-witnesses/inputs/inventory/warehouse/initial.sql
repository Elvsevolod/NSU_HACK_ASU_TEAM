USE `warehouse`;
CREATE TABLE `products` (
 `id` varchar(80),
 `category` varchar(80),
 `revision` varchar(80),
 `quantity` varchar(80)
) ENGINE=InnoDB;
INSERT INTO `products` VALUES ('SKU7','hardware',4,8),('SKU8','office',5,9),('SKU9','hardware',6,10);
