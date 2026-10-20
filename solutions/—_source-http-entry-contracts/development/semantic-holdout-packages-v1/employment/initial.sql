-- Independent relational snapshot; no target database is executed.
USE `company`;
CREATE TABLE `company` (
  `id` TEXT,
  `name` TEXT,
  `description` TEXT,
  `rating` TEXT
) ENGINE=InnoDB;
INSERT INTO `company` VALUES (1,'North Works','Manufacturing',NULL);
USE `job`;
CREATE TABLE `job` (
  `id` TEXT,
  `title` TEXT,
  `description` TEXT,
  `minSalary` TEXT,
  `maxSalary` TEXT,
  `location` TEXT,
  `company` TEXT
) ENGINE=InnoDB;
INSERT INTO `job` VALUES (101,'Assembler','Build devices','40','60','North',1);
USE `review`;
CREATE TABLE `review` (
  `id` TEXT,
  `title` TEXT,
  `description` TEXT,
  `rating` TEXT,
  `companyId` TEXT
) ENGINE=InnoDB;
INSERT INTO `review` VALUES (201,'Original','Before',3.0,2);
