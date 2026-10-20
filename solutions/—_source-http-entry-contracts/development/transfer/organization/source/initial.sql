USE `organization-service`;
CREATE TABLE `organization` (
  `id` VARCHAR(40),
  `name` VARCHAR(100),
  `address` VARCHAR(100)
) ENGINE=InnoDB;
USE `department-service`;
CREATE TABLE `department` (
  `id` VARCHAR(40),
  `organization_id` VARCHAR(40),
  `name` VARCHAR(100)
) ENGINE=InnoDB;
USE `employee-service`;
CREATE TABLE `employee` (
  `id` VARCHAR(100),
  `organization_id` VARCHAR(100),
  `department_id` VARCHAR(100),
  `name` VARCHAR(100),
  `age` INT,
  `position` VARCHAR(100)
) ENGINE=InnoDB;
