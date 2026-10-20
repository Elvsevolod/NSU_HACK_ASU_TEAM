USE `order`;
CREATE TABLE `book_order` (
  `id` BIGINT,
  `user_id` BIGINT,
  `book_id` BIGINT,
  `book_isbn` VARCHAR(40),
  `book_name` VARCHAR(100),
  `book_reference_id` VARCHAR(60),
  `ordered_at` VARCHAR(40),
  `collected_at` VARCHAR(40),
  `collect_by` VARCHAR(40),
  `returned_at` VARCHAR(40),
  `return_by` VARCHAR(40),
  `late_fees` BIGINT
) ENGINE=InnoDB;
INSERT INTO `book_order` VALUES (100,7,11,'9780134685991','Existing Book','loaned-11','2026-10-01T12:00:00',NULL,'2026-10-22T12:00:00',NULL,'2026-11-19T12:00:00',NULL);
USE `order`;
CREATE TABLE `book_order_history` (
  `user_id` BIGINT,
  `book_id` BIGINT,
  `book_isbn` VARCHAR(40),
  `book_name` VARCHAR(100),
  `book_reference_id` VARCHAR(60),
  `ordered_at` VARCHAR(40),
  `collected_at` VARCHAR(40),
  `returned_at` VARCHAR(40),
  `late_fees` BIGINT,
  `order_id` BIGINT
) ENGINE=InnoDB;
USE `inventory`;
CREATE TABLE `inventory` (
  `book_id` BIGINT,
  `isbn` VARCHAR(40),
  `book_reference_id` VARCHAR(60),
  `category_id` INT,
  `available` BIT
) ENGINE=InnoDB;
INSERT INTO `inventory` VALUES (11,'9780134685991','loaned-11',1,0);
INSERT INTO `inventory` VALUES (21,'9780134685991','available-21',1,1);
INSERT INTO `inventory` VALUES (31,'9780134685991','copy-A',1,1);
INSERT INTO `inventory` VALUES (31,'9780134685991','copy-B',1,1);
