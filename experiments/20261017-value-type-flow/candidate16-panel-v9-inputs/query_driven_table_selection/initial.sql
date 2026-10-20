USE `service`;
CREATE TABLE `parts` (
 `id` varchar(80),
 `quantity` varchar(80)
) ENGINE=InnoDB;
INSERT INTO `parts` VALUES ('one',2);
CREATE TABLE `audits` (
 `key` varchar(80)
) ENGINE=InnoDB;
