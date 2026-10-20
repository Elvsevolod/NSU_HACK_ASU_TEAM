USE `account`;
CREATE TABLE `accounts` (
 `name` varchar(80),
 `lastSeen` varchar(80),
 `incomes` varchar(80),
 `expenses` varchar(80),
 `saving` varchar(80),
 `note` varchar(80)
) ENGINE=InnoDB;
INSERT INTO `accounts` VALUES ('demo',NULL,NULL,NULL,NULL,'seed');
