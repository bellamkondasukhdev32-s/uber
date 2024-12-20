from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

import random

# Flask app configuration
app = Flask(__name__)
app.secret_key = 'your_secret_key'  

# MySQL configuration
db = pymysql.connect(
    host="localhost",
    user="root",
    password="admin",
    database="uber_app"
)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        phone = request.form['phone']
        user_type = request.form['user_type']  

        cursor = db.cursor()
        try:
            
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            if user:
                flash('Email is already registered. Please use a different email.', 'danger')
            else:
                
                query = "INSERT INTO users (name, email, password, phone, user_type) VALUES (%s, %s, %s, %s, %s)"
                cursor.execute(query, (name, email, password, phone, user_type))
                db.commit()
                flash('Registration successful! Please login.', 'success')

                
                if user_type == 'driver':
                    return redirect(url_for('add_vehicle'))  

                return redirect(url_for('login'))  
        except Exception as e:
            db.rollback()
            flash(f'Error: {str(e)}', 'danger')
            print(f"Error inserting user: {str(e)}")  
        finally:
            cursor.close()
    return render_template('register.html')

@app.route('/add_vehicle', methods=['GET', 'POST'])
def add_vehicle():
    if 'user_id' not in session or session.get('user_type') != 'driver':
        flash('Please log in as a driver to add a vehicle.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        
        vehicle_type = request.form['vehicle_type']
        license_plate = request.form['license_plate']
        capacity = request.form['capacity']
        supported_ride_types = request.form['supported_ride_types']
        price_per_day = request.form['price_per_day']  

        driver_id = session['user_id']

        cursor = db.cursor()
        try:
            
            cursor.execute("""
                INSERT INTO vehicles (driver_id, vehicle_type, license_plate, capacity, supported_ride_types, price_per_day)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (driver_id, vehicle_type, license_plate, capacity, supported_ride_types, price_per_day))
            db.commit()
            flash('Vehicle added successfully!', 'success')
            return redirect(url_for('dashboard'))  
        except Exception as e:
            db.rollback()
            flash(f'Error: {str(e)}', 'danger')
        finally:
            cursor.close()

    return render_template('add_vehicle.html')  


# User login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()

        if user:
            
            if check_password_hash(user[3], password):  
                session['user_id'] = user[0]  
                session['user_type'] = user[5]  
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid password.', 'danger')
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login to access this page.', 'danger')
        return redirect(url_for('login'))

    cursor = db.cursor(pymysql.cursors.DictCursor)

    if session['user_type'] == 'driver':
        
        cursor.execute("SELECT * FROM rides WHERE driver_id = %s AND ride_status IN ('requested', 'accepted', 'started', 'completed')", (session['user_id'],))
        rides = cursor.fetchall()
        cursor.close()
        return render_template('dashboard_driver.html', rides=rides)

    elif session['user_type'] == 'rider':
        
        cursor.execute("SELECT * FROM rides WHERE rider_id = %s", (session['user_id'],))
        rides = cursor.fetchall()

        
        for ride in rides:
            cursor.execute("SELECT * FROM ratings WHERE ride_id = %s AND rider_id = %s", (ride['ride_id'], session['user_id']))
            ride['rating'] = cursor.fetchone()  

        cursor.close()
        return render_template('dashboard_rider.html', rides=rides)
    
    flash('Invalid user type.', 'danger')
    return redirect(url_for('login'))



@app.route('/accept_ride/<int:ride_id>', methods=['POST'])
def accept_ride(ride_id):
    cursor = db.cursor()
    try:
        
        cursor.execute("UPDATE rides SET ride_status = 'accepted' WHERE ride_id = %s", (ride_id,))
        db.commit()
        flash('Ride accepted successfully.', 'success')

        
        cursor.execute("SELECT rider_id FROM rides WHERE ride_id = %s", (ride_id,))
        rider_id = cursor.fetchone()[0]
        flash(f"Rider has been notified. Ride assigned to you.", 'success')

    except Exception as e:
        db.rollback()
        flash(f'Error accepting ride: {str(e)}', 'danger')
    finally:
        cursor.close()
    return redirect(url_for('dashboard'))

@app.route('/start_ride/<int:ride_id>', methods=['POST'])
def start_ride(ride_id):
    cursor = db.cursor()
    try:
        
        cursor.execute("UPDATE rides SET ride_status = 'started' WHERE ride_id = %s", (ride_id,))
        db.commit()

        
        cursor.execute("SELECT ride_status FROM rides WHERE ride_id = %s", (ride_id,))
        updated_status = cursor.fetchone()[0]
        print(f"Updated ride status for ride {ride_id}: {updated_status}")

        flash('Ride started successfully.', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Error starting ride: {str(e)}', 'danger')
    finally:
        cursor.close()

    return redirect(url_for('dashboard'))


@app.route('/complete_ride/<int:ride_id>', methods=['POST'])
def complete_ride(ride_id):
    cursor = db.cursor()
    try:
        
        cursor.execute("UPDATE rides SET ride_status = 'completed' WHERE ride_id = %s", (ride_id,))
        db.commit()
        flash('Ride completed successfully.', 'success')

    except Exception as e:
        db.rollback()
        flash(f'Error completing ride: {str(e)}', 'danger')
    finally:
        cursor.close()
    return redirect(url_for('dashboard'))



@app.route('/request_ride', methods=['GET', 'POST'])
def request_ride():
    
    if 'user_id' not in session:
        flash('Please log in to request a ride.', 'danger')
        return redirect(url_for('login'))  

    if request.method == 'POST':
        rider_id = session['user_id']
        pickup_location = request.form['pickup_location']
        dropoff_location = request.form['dropoff_location']
        ride_type = request.form['ride_type']  
        vehicle_type = request.form['vehicle_type']  

        
        geolocator = Nominatim(user_agent="uber_app", timeout=60)

        try:
            
            pickup_location_coords = geolocator.geocode(pickup_location)
            if not pickup_location_coords:
                flash('Pickup location could not be found. Please enter a valid address.', 'danger')
                return redirect(url_for('request_ride'))

            
            dropoff_location_coords = geolocator.geocode(dropoff_location)
            if not dropoff_location_coords:
                flash('Dropoff location could not be found. Please enter a valid address.', 'danger')
                return redirect(url_for('request_ride'))

            
            pickup_coords = (pickup_location_coords.latitude, pickup_location_coords.longitude)
            dropoff_coords = (dropoff_location_coords.latitude, dropoff_location_coords.longitude)

            
            distance = geodesic(pickup_coords, dropoff_coords).km  
            base_fare = distance * 1.5  
            shared_fare = base_fare * 0.8  

           
            estimated_time = round(distance / 40 * 60)  

            cursor = db.cursor()
            try:
                
                cursor.execute(
                    "INSERT INTO rides (rider_id, pickup_location, dropoff_location, ride_type, fare, estimated_time, ride_status, vehicle_type) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (rider_id, pickup_location, dropoff_location, ride_type, base_fare if ride_type == 'solo' else shared_fare, estimated_time, 'requested', vehicle_type)
                )
                db.commit()

                
                cursor.execute("SELECT user_id, name, phone FROM users WHERE user_type = 'driver'")
                available_drivers = cursor.fetchall()

                if available_drivers:
                    
                    assigned_driver = random.choice(available_drivers)
                    driver_name = assigned_driver[1]
                    driver_phone = assigned_driver[2]

                    
                    cursor.execute("UPDATE rides SET driver_id = %s, ride_status = 'accepted' WHERE rider_id = %s AND ride_status = 'requested'", (assigned_driver[0], rider_id))
                    db.commit()

                    flash(f'Ride assigned to: {driver_name} (Phone: {driver_phone})', 'success')
                    return render_template('confirm_ride.html', driver_name=driver_name, fare=base_fare if ride_type == 'solo' else shared_fare, pickup_location=pickup_location, dropoff_location=dropoff_location, estimated_time=estimated_time, driver_phone=driver_phone)

                else:
                    flash('No available drivers at the moment. Please try again later.', 'danger')

            except Exception as e:
                db.rollback()
                flash(f'Error: {str(e)}', 'danger')
                print(f"Error requesting ride: {str(e)}")  
            finally:
                cursor.close()

        except GeocoderTimedOut:
            flash('Geocoding service timed out. Please try again later.', 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')

        return redirect(url_for('dashboard'))

    return render_template('request_ride.html')





# Confirm ride route
@app.route('/confirm_ride', methods=['POST'])
def confirm_ride():
    if request.method == 'POST':
        
        if 'driver_id' not in request.form:
            flash('Driver ID is missing.', 'danger')
            return redirect(url_for('dashboard'))

        rider_id = session['user_id']
        driver_id = request.form['driver_id']  
        fare = request.form['fare']
        pickup_location = request.form['pickup_location']
        dropoff_location = request.form['dropoff_location']
        estimated_time = request.form['estimated_time']

        cursor = db.cursor()
        try:
            
            cursor.execute(
                "UPDATE rides SET driver_id = %s, ride_status = 'accepted' WHERE rider_id = %s AND pickup_location = %s AND dropoff_location = %s",
                (driver_id, rider_id, pickup_location, dropoff_location)
            )
            db.commit()
            flash(f'Ride confirmed with driver: {driver_id}', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.rollback()
            flash(f'Error: {str(e)}', 'danger')
        finally:
            cursor.close()

    return redirect(url_for('dashboard'))


# Cancel ride route
@app.route('/cancel_ride/<int:ride_id>', methods=['POST'])
def cancel_ride(ride_id):
    cursor = db.cursor()
    try:
        cursor.execute("UPDATE rides SET ride_status = %s WHERE ride_id = %s", ('cancelled', ride_id))
        db.commit()
        flash('Ride has been cancelled.', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cursor.close()
    return redirect(url_for('dashboard'))
@app.route('/shared-rides')
def shared_rides():
    
    return render_template('shared_rides.html')

@app.route('/payment/<int:ride_id>', methods=['GET', 'POST'])
def payment(ride_id):
    if request.method == 'POST':
        payment_method = request.form['payment_method']  
        
        cursor = db.cursor()
        try:
            
            cursor.execute(
                "INSERT INTO payments (ride_id, rider_id, amount, payment_method, payment_status) VALUES (%s, %s, %s, %s, %s)",
                (ride_id, session['user_id'], request.form['amount'], payment_method, 'pending')
            )
            db.commit()
            
            
            return redirect(url_for('rating', ride_id=ride_id))

        except Exception as e:
            db.rollback()
            flash(f'Error: {str(e)}', 'danger')
        finally:
            cursor.close()
    
    
    return render_template('payment.html', ride_id=ride_id)


@app.route('/mark_payment/<int:ride_id>', methods=['POST'])
def mark_payment(ride_id):
    cursor = db.cursor()
    try:
        
        cursor.execute("SELECT ride_id, rider_id FROM rides WHERE ride_id = %s", (ride_id,))
        ride = cursor.fetchone()
        
        if not ride:
            flash('Invalid ride ID.', 'danger')
            return redirect(url_for('dashboard'))
        
        
        cursor.execute("UPDATE rides SET payment_received = 1 WHERE ride_id = %s", (ride_id,))
        db.commit()

        
        cursor.execute("SELECT * FROM payments WHERE ride_id = %s", (ride_id,))
        payment = cursor.fetchone()

        if payment:
            
            cursor.execute("UPDATE payments SET payment_status = 'completed' WHERE ride_id = %s", (ride_id,))
        else:
            
            cursor.execute("INSERT INTO payments (ride_id, rider_id, amount, payment_status) VALUES (%s, %s, %s, 'completed')",
                           (ride_id, ride['rider_id'], ride['fare']))
        
        db.commit()
        flash('Payment marked as received and updated.', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cursor.close()
    
    
    return redirect(url_for('dashboard'))



@app.route('/rating/<int:ride_id>', methods=['GET', 'POST'])
def rating(ride_id):
    if request.method == 'POST':
        rating = request.form['rating']
        comment = request.form['comment']
        
        
        print(f"Received Rating: {rating}, Comment: {comment}")
        
        cursor = db.cursor()
        try:
            
            cursor.execute(
                "INSERT INTO ratings (ride_id, rider_id, rating, comment) VALUES (%s, %s, %s, %s)",
                (ride_id, session['user_id'], rating, comment)
            )
            db.commit()
            flash('Thank you for your feedback!', 'success')
            return redirect(url_for('dashboard'))  
        except Exception as e:
            db.rollback()
            flash(f'Error: {str(e)}', 'danger')
        finally:
            cursor.close()

    
    cursor = db.cursor()
    cursor.execute("SELECT * FROM rides WHERE ride_id = %s", (ride_id,))
    ride = cursor.fetchone()
    cursor.close()

    
    print(f"Ride Data: {ride}")
    
    return render_template('rating.html', ride=ride)

from flask import render_template, request, redirect, url_for
import datetime

@app.route('/request_car_rental', methods=['GET', 'POST'])
def request_car_rental():
    
    if 'user_id' not in session:
        flash('Please log in to request a car rental.', 'danger')
        return redirect(url_for('login'))  

    if request.method == 'POST':
        print("Form data:", request.form)  
        try:
            vehicle_id = request.form['vehicle_id']  
            rental_start_date = request.form['rental_start_date']
            rental_end_date = request.form['rental_end_date']
            print("Vehicle ID:", vehicle_id)
            print("Rental Dates:", rental_start_date, rental_end_date)

            
            vehicle_id, vehicle_price = vehicle_id.split('-')
            vehicle_price = float(vehicle_price)  
            print(f"Vehicle ID: {vehicle_id}, Price per Day: {vehicle_price}")

            rental_start = datetime.datetime.strptime(rental_start_date, '%Y-%m-%d')
            rental_end = datetime.datetime.strptime(rental_end_date, '%Y-%m-%d')

            
            total_days = (rental_end - rental_start).days
            if total_days <= 0:
                flash('Rental duration must be at least 1 day.', 'danger')
                return redirect(url_for('request_car_rental'))

            total_cost = total_days * vehicle_price
            print(f"Total Rental Cost: £{total_cost:.2f}")

            
            cursor = db.cursor()
            cursor.execute("SELECT COUNT(*) FROM vehicles WHERE vehicle_id = %s", (vehicle_id,))
            vehicle_exists = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM users WHERE user_id = %s", (session['user_id'],))
            user_exists = cursor.fetchone()[0]

            if not vehicle_exists or not user_exists:
                flash('Invalid vehicle or user.', 'danger')
                return redirect(url_for('request_car_rental'))

            
            cursor.execute("""
                INSERT INTO car_rentals (renter_id, vehicle_id, rental_start_date, rental_end_date, total_cost)
                VALUES (%s, %s, %s, %s, %s)
            """, (session['user_id'], vehicle_id, rental_start_date, rental_end_date, total_cost))
            db.commit()
            cursor.close()

            print("Rental request inserted successfully.")
            flash('Car rental request submitted successfully.', 'success')
            return redirect(url_for('view_rentals'))  

        except ValueError as e:
            flash(f'Invalid input: {e}', 'danger')
            return redirect(url_for('request_car_rental'))

    
    cursor = db.cursor()
    cursor.execute("SELECT vehicle_id, vehicle_type, license_plate, price_per_day FROM vehicles")
    vehicles = cursor.fetchall()
    cursor.close()

    return render_template('request_car_rental.html', vehicles=vehicles)  

@app.route('/view_rentals')
def view_rentals():
    
    if 'user_id' not in session:
        flash('Please log in to view your rentals.', 'danger')
        return redirect(url_for('login'))  
    
    
    cursor = db.cursor()
    cursor.execute("""
        SELECT rental_id, vehicle_id, rental_start_date, rental_end_date, rental_status, total_cost 
        FROM car_rentals 
        WHERE renter_id = %s
    """, (session['user_id'],))
    rentals = cursor.fetchall()
    cursor.close()

    
    if not rentals:
        flash('You have no rental history.', 'info')

    
    return render_template('view_rentals.html', rentals=rentals)



# Logout route
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
