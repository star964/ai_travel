CREATE DATABASE IF NOT EXISTS ai_travel
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE ai_travel;

CREATE TABLE IF NOT EXISTS travel_records (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '攻略记录ID',
    destination VARCHAR(100) NOT NULL COMMENT '旅游目的地',
    days INT NOT NULL COMMENT '旅行天数',
    budget VARCHAR(100) NOT NULL COMMENT '旅游预算',
    preference VARCHAR(255) NOT NULL COMMENT '旅行偏好',
    travel_plan LONGTEXT NOT NULL COMMENT 'AI生成的旅游攻略',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    PRIMARY KEY (id),
    INDEX idx_destination (destination),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='AI旅游攻略记录表';
