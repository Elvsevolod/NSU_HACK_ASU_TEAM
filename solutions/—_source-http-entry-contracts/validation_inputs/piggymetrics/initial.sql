USE `account-service`;
CREATE TABLE `accounts` (
 `name` varchar(80),
 `last_seen` varchar(80),
 `incomes` varchar(80),
 `expenses` varchar(80),
 `saving` varchar(80),
 `note` varchar(80)
) ENGINE=InnoDB;
USE `auth-service`;
CREATE TABLE `users` (
 `username` varchar(80),
 `password` varchar(80)
) ENGINE=InnoDB;
INSERT INTO `users` VALUES ('occupied','initial-hash');
USE `statistics-service`;
CREATE TABLE `datapoints` (
 `id` varchar(80)
) ENGINE=InnoDB;
