-- VMC Chatbot MariaDB Database Schema

CREATE DATABASE IF NOT EXISTS vmc_chatbot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE vmc_chatbot;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    login_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    mobile VARCHAR(20) NOT NULL,
    area VARCHAR(100),
    ward_number VARCHAR(10),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_login_id (login_id),
    INDEX idx_mobile (mobile)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    state VARCHAR(50) DEFAULT 'login',
    current_category VARCHAR(50),
    current_sub_issue VARCHAR(100),
    login_id VARCHAR(50),
    complaint_id VARCHAR(50),
    property_id VARCHAR(50),
    image_url TEXT,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_phone_number (phone_number),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Complaints table
CREATE TABLE IF NOT EXISTS complaints (
    id INT AUTO_INCREMENT PRIMARY KEY,
    complaint_id VARCHAR(50) UNIQUE NOT NULL,
    user_id INT NOT NULL,
    login_id VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL,
    sub_issue VARCHAR(100),
    description TEXT,
    image_url TEXT,
    status ENUM('pending', 'resolved', 'in_progress') DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_complaint_id (complaint_id),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Property Tax table
CREATE TABLE IF NOT EXISTS property_tax (
    id INT AUTO_INCREMENT PRIMARY KEY,
    property_id VARCHAR(50) UNIQUE NOT NULL,
    owner_name VARCHAR(100) NOT NULL,
    address TEXT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    status ENUM('paid', 'due', 'pending') NOT NULL,
    year INT NOT NULL,
    receipt_no VARCHAR(50),
    bill_no VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_property_id (property_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert sample property tax data
INSERT INTO property_tax (property_id, owner_name, address, amount, status, year, receipt_no, bill_no) VALUES
('PROP-001', 'John Doe', '123 Main Street, Ward 1', 15000.00, 'paid', 2025, 'REC-2025-001', 'BILL-2025-001'),
('PROP-002', 'Jane Smith', '456 Oak Avenue, Ward 2', 20000.00, 'due', 2025, NULL, 'BILL-2025-002'),
('PROP-003', 'Bob Johnson', '789 Pine Road, Ward 3', 18000.00, 'pending', 2025, NULL, 'BILL-2025-003')
ON DUPLICATE KEY UPDATE property_id=property_id;
