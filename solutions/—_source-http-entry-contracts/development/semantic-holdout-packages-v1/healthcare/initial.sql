-- Independent relational snapshot; no target database is executed.
USE `hospital_db`;
CREATE TABLE `doctors` (
  `id` TEXT,
  `name` TEXT,
  `specialization` TEXT,
  `experience` TEXT,
  `phone` TEXT
) ENGINE=InnoDB;
INSERT INTO `doctors` VALUES (7,'Dr Vale','Cardiology',12,'701');
USE `hospital_db`;
CREATE TABLE `patients` (
  `id` TEXT,
  `name` TEXT,
  `age` TEXT,
  `gender` TEXT,
  `department` TEXT,
  `phone` TEXT
) ENGINE=InnoDB;
INSERT INTO `patients` VALUES (11,'Seed Patient',45,'F','General','702');
