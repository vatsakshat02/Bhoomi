from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import csv
import os

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.DEBUG)

@app.route('/test', methods=['GET'])
def test():
    return jsonify({'message': 'Server is running'})

@app.route('/register', methods=['POST'])
def register():
    app.logger.debug("Received registration data")
    try:
        data = request.json
        app.logger.debug(f"Received Data: {data}")

        name = data.get('name')
        phone_number = data.get('phone_number')
        email = data.get('email')
        state = data.get('state')

        if not name or not phone_number or not email or not state:
            app.logger.error('Missing required fields')
            return jsonify({'error': 'Name, phone number, email, and state are required'}), 400

        csv_file = 'registration_data.csv'
        file_exists = os.path.isfile(csv_file)

        with open(csv_file, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(['Name', 'Phone Number', 'Email', 'State'])
            writer.writerow([name, phone_number, email, state])

        app.logger.debug(f"Registration saved: {name}, {phone_number}, {email}, {state}")
        return jsonify({'message': 'Registration successful'})

    except Exception as e:
        app.logger.error(f"Error processing registration: {str(e)}")
        return jsonify({'error': 'Error processing registration'}), 500

@app.route('/check_phone', methods=['POST'])
def check_phone():
    app.logger.debug("Received phone number for verification")
    try:
        data = request.json
        phone_number = data.get('phone_number')

        if not phone_number:
            app.logger.error('Phone number not provided')
            return jsonify({'exists': False, 'error': 'Phone number not provided'}), 400

        csv_file = 'registration_data.csv'

        if not os.path.isfile(csv_file):
            return jsonify({'exists': False, 'error': 'No registration data available'}), 404

        with open(csv_file, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['Phone Number'] == phone_number:
                    app.logger.debug(f"Phone number {phone_number} exists in the records.")
                    return jsonify({'exists': True})

        app.logger.debug(f"Phone number {phone_number} does not exist in the records.")
        return jsonify({'exists': False, 'error': 'Phone number does not exist'}), 404

    except Exception as e:
        app.logger.error(f"Error checking phone number: {str(e)}")
        return jsonify({'exists': False, 'error': 'Error processing request'}), 500

@app.route('/get_user_data', methods=['POST'])
def get_user_data():
    app.logger.debug("Fetching user data")
    try:
        data = request.json
        phone_number = data.get('phone_number')

        if not phone_number:
            app.logger.error('Phone number not provided')
            return jsonify({'error': 'Phone number not provided'}), 400

        csv_file = 'registration_data.csv'

        if not os.path.isfile(csv_file):
            return jsonify({'error': 'No registration data available'}), 404

        with open(csv_file, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['Phone Number'] == phone_number:
                    app.logger.debug(f"User data found for {phone_number}")
                    return jsonify({
                        'name': row.get('Name', ''),
                        'phone_number': row.get('Phone Number', ''),
                        'email': row.get('Email', ''),
                        'state': row.get('State', '')
                    })

        app.logger.debug(f"No user data found for {phone_number}")
        return jsonify({'error': 'User not found'}), 404

    except Exception as e:
        app.logger.error(f"Error fetching user data: {str(e)}")
        return jsonify({'error': 'Error processing request'}), 500

@app.route('/book', methods=['POST'])
def book():
    app.logger.debug("Received booking request")
    try:
        data = request.json
        name = data.get('name')
        address = data.get('address')
        phone_number = data.get('phone_number')
        booking_type = data.get('booking_type', 'Unknown')

        if not name or not address or not phone_number:
            app.logger.error('Missing required fields')
            return jsonify({'error': 'Name, address, and phone number are required'}), 400

        csv_file = 'bookings.csv'
        file_exists = os.path.isfile(csv_file)

        with open(csv_file, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(['Name', 'Address', 'Phone Number', 'Booking Type'])
            writer.writerow([name, address, phone_number, booking_type])

        app.logger.debug(f"Booking saved: {name}, {address}, {phone_number}, {booking_type}")
        return jsonify({'message': 'Booking successful'})

    except Exception as e:
        app.logger.error(f"Error processing booking: {str(e)}")
        return jsonify({'error': 'Error processing booking'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)
