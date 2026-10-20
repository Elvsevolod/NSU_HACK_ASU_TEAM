USE `customers`;
CREATE TABLE `owners` (
 `id` varchar(80),
 `first_name` varchar(80),
 `last_name` varchar(80),
 `address` varchar(80),
 `city` varchar(80),
 `telephone` varchar(80)
) ENGINE=InnoDB;
INSERT INTO `owners` VALUES (1,'Joe','Smith','Main','York','12345');
CREATE TABLE `pets` (
 `key` varchar(80)
) ENGINE=InnoDB;
CREATE TABLE `types` (
 `key` varchar(80)
) ENGINE=InnoDB;
