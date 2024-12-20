-- Create Database
CREATE DATABASE uber_app;

-- Use the database
USE uber_app;

-- Table for users (stores both riders and drivers)
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    phone VARCHAR(15),
    user_type ENUM('rider', 'driver') NOT NULL,
    license_number VARCHAR(50) UNIQUE, 
    rating DECIMAL(3, 2) DEFAULT 5.0,  
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for vehicles (drivers add their vehicles)
CREATE TABLE vehicles (
    vehicle_id INT AUTO_INCREMENT PRIMARY KEY,
    driver_id INT NOT NULL,
    vehicle_type ENUM('bike', 'cab', 'auto', 'rickshaw') NOT NULL,
    license_plate VARCHAR(50) NOT NULL UNIQUE,
    capacity INT NOT NULL,
    supported_ride_types ENUM('solo', 'shared') DEFAULT 'solo', 
    FOREIGN KEY (driver_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Table for rides
CREATE TABLE rides (
    ride_id INT AUTO_INCREMENT PRIMARY KEY,
    rider_id INT NOT NULL,
    driver_id INT,
    pickup_location VARCHAR(255) NOT NULL,
    dropoff_location VARCHAR(255) NOT NULL,
    ride_status ENUM('requested', 'accepted', 'started', 'completed', 'cancelled') DEFAULT 'requested',
    fare DECIMAL(10, 2),
    ride_type ENUM('solo', 'shared') DEFAULT 'solo',
    vehicle_type ENUM('bike', 'cab', 'auto', 'rickshaw') NOT NULL,  
    distance DECIMAL(10, 2),  -- Distance in km
    estimated_time INT, 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (rider_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (driver_id) REFERENCES users(user_id) ON DELETE SET NULL
);

-- Table for shared rides (links multiple riders to a single ride)
CREATE TABLE shared_rides (
    shared_ride_id INT AUTO_INCREMENT PRIMARY KEY,
    ride_id INT NOT NULL,
    rider_id INT NOT NULL,
    pickup_location VARCHAR(255) NOT NULL,
    dropoff_location VARCHAR(255) NOT NULL,
    fare DECIMAL(10, 2),
    FOREIGN KEY (ride_id) REFERENCES rides(ride_id) ON DELETE CASCADE,
    FOREIGN KEY (rider_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Table for payments
CREATE TABLE payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    ride_id INT NOT NULL,
    rider_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    payment_status ENUM('pending', 'completed') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ride_id) REFERENCES rides(ride_id) ON DELETE CASCADE,
    FOREIGN KEY (rider_id) REFERENCES users(user_id) ON DELETE CASCADE
);

ALTER TABLE rides ADD COLUMN payment_received INT DEFAULT 0;
ALTER TABLE rides
CHANGE COLUMN payment_received payment_received TINYINT(1) DEFAULT 0 COMMENT '0 = Not Received, 1 = Received';


-- Table for ratings (stores rider ratings and comments)
CREATE TABLE ratings (
    rating_id INT AUTO_INCREMENT PRIMARY KEY,
    ride_id INT NOT NULL,
    rider_id INT NOT NULL,
    rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),  
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ride_id) REFERENCES rides(ride_id) ON DELETE CASCADE,
    FOREIGN KEY (rider_id) REFERENCES users(user_id) ON DELETE CASCADE
);


-- Table for car rentals
CREATE TABLE car_rentals (
    rental_id INT AUTO_INCREMENT PRIMARY KEY,
    renter_id INT NOT NULL,
    vehicle_id INT NOT NULL,
    rental_start_date DATE NOT NULL,
    rental_end_date DATE NOT NULL,
    rental_status ENUM('requested', 'confirmed', 'completed', 'cancelled') DEFAULT 'requested',
    total_cost DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (renter_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id) ON DELETE CASCADE
);
ALTER TABLE vehicles ADD price_per_day DECIMAL(10, 2);
