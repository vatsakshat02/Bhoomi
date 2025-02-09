from flask import Flask, request, jsonify
from flask_cors import CORS
import torch
import torchvision.transforms as transforms
from PIL import Image
import json
import openai
import API
import logging
import csv
import os
import requests
import math


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Allow all origins



logging.basicConfig(level=logging.DEBUG)

openai.api_key = API.OPENAIAPI_KEY
GOOGLE_MAPS_API_KEY= API.MAPS_KEY
model_path = 'crop_disease_model_refined.pth'
class_labels_path = 'class_labels.json'

# Set device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class CropDiseaseModel(torch.nn.Module):
    def __init__(self, num_classes):
        super(CropDiseaseModel, self).__init__()
        self.conv1 = torch.nn.Conv2d(3, 32, kernel_size=3, padding=1)
        self.conv2 = torch.nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.conv3 = torch.nn.Conv2d(64, 128, kernel_size=3, padding=1)
        self.pool = torch.nn.MaxPool2d(2, 2)
        self.fc1 = torch.nn.Linear(128 * 18 * 18, 512)
        self.fc2 = torch.nn.Linear(512, num_classes)
        self.dropout = torch.nn.Dropout(0.5)
        self.relu = torch.nn.ReLU()
        
    def forward(self, x):
        x = self.pool(self.relu(self.conv1(x)))
        x = self.pool(self.relu(self.conv2(x)))
        x = self.pool(self.relu(self.conv3(x)))
        x = x.view(x.size(0), -1)  # Flatten
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        return x

# Load class labels
try:
    with open(class_labels_path) as f:
        class_labels = json.load(f)
    app.logger.debug("Class labels loaded successfully.")
except Exception as e:
    app.logger.error(f"Error loading class labels: {str(e)}")
    class_labels = {}

# Instantiate the model and load the state dictionary
num_classes = len(class_labels)
model = CropDiseaseModel(num_classes).to(device)

try:
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()
    app.logger.debug("Model loaded successfully.")
except Exception as e:
    app.logger.error(f"Error loading model: {str(e)}")

# Preprocessing function for images
def prepare_image(image, target_size=(150, 150)):
    transform = transforms.Compose([
        transforms.Resize(target_size),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    image = image.convert('RGB')
    image = transform(image).unsqueeze(0)  
    return image.to(device)

def generate_insights(disease):
    """
    Generate concise insights and care tips for the identified disease using OpenAI's chat-based model.
    """
    try:
        prompt = (
            f"The plant has {disease}. "
            "Provide four concise one-line care tips for this disease, formatted with a bullet point and a brief explanation. "
            "Include details like temperature, moisture, etc., in each tip. If the plant is healthy or has health in the name just make sure to give the 4 to maintain health"
        )
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo", 
            messages=[
                {"role": "system", "content": "You are a helpful assistant specialized in agriculture."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )
        insights = response.choices[0].message['content'].strip()
        app.logger.debug(f"Generated insights: {insights}")
        return insights
    except openai.error.OpenAIError as e:
        app.logger.error(f"OpenAI API error: {str(e)}")
        return "OpenAI API error occurred."
    except Exception as e:
        app.logger.error(f"Error generating insights: {str(e)}")
        return "Error generating insights."

@app.route('/test', methods=['GET'])
def test():
    return jsonify({'message': 'Server is running'})

@app.route('/predict', methods=['POST'])
def predict():
    app.logger.debug("Starting prediction...")
    try:
        if 'images' not in request.files:
            app.logger.error('No images uploaded')
            return jsonify({'error': 'No images uploaded'}), 400

        files = request.files.getlist('images')
        app.logger.debug(f"Received {len(files)} files.")

        predictions_sum = torch.zeros(num_classes).to(device)

        for file in files:
            image = Image.open(file)
            processed_image = prepare_image(image)
            app.logger.debug(f"Image {file.filename} preprocessed successfully")

            with torch.no_grad():
                predictions = model(processed_image)
                predictions_sum += predictions.squeeze()

        # Average the predictions
        averaged_predictions = predictions_sum / len(files)
        predicted_class = torch.argmax(averaged_predictions).item()

        disease = class_labels.get(str(predicted_class), 'Unknown disease')
        if disease == 'Unknown disease':
            app.logger.error(f"Predicted class index {predicted_class} is out of range. Max index should be {len(class_labels) - 1}")

        app.logger.debug(f"Predicted disease: {disease}")

        insights = generate_insights(disease)
        app.logger.debug(f"Generated insights: {insights}")

        return jsonify({'disease': disease, 'insights': insights})
    except Exception as e:
        app.logger.error(f"Error during prediction: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/chatbot', methods=['POST'])
def chatbot():
    user_input = request.json.get('message')
    if not user_input:
        app.logger.error('No input provided')
        return jsonify({'error': 'No input provided'}), 400

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",  
            messages=[
                {"role": "system", "content": "You are a helpful assistant named Bhoomi specialized in agriculture in India."},
                {"role": "user", "content": user_input}
            ]
        )
        answer = response.choices[0].message['content']
        app.logger.debug(f"Chatbot response: {answer}")
        return jsonify({'response': answer})
    except openai.error.OpenAIError as e:
        app.logger.error(f"OpenAI API error: {str(e)}")
        return jsonify({'error': 'OpenAI API error occurred.'}), 500
    except Exception as e:
        app.logger.error(f"Error generating chatbot response: {str(e)}")
        return jsonify({'error': 'Error generating chatbot response.'}), 500
@app.route('/book', methods=['POST'])
def book():
    app.logger.debug("Received booking request")
    try:
        data = request.json
        name = data.get('name')
        address = data.get('address')
        phone_number = data.get('phone_number')
        booking_type = data.get('booking_type', 'Unknown')  # Default to 'Unknown' if not provided

        if not name or not address or not phone_number:
            app.logger.error('Missing required fields')
            return jsonify({'error': 'Name, address, and phone number are required'}), 400

        csv_file = 'bookings.csv'
        file_exists = os.path.isfile(csv_file)

        with open(csv_file, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(['Name', 'Address', 'Phone Number', 'Booking Type'])  # Updated header
            writer.writerow([name, address, phone_number, booking_type])  # Include booking type

        app.logger.debug(f"Booking saved: {name}, {address}, {phone_number}, {booking_type}")
        return jsonify({'message': 'Booking successful'})
    
    except Exception as e:
        app.logger.error(f"Error processing booking: {str(e)}")
        return jsonify({'error': 'Error processing booking'}), 500

@app.route('/register', methods=['POST'])
def register():
    app.logger.debug("Received registration data")
    try:
        data = request.json
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

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def find_transport_services(lat, lng):
    """
    Find nearby transport services using Google Maps Places API.
    """
    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lng}&radius=50000&type=taxi_stand|bus_station|moving_company&key={GOOGLE_MAPS_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('results', [])
    else:
        app.logger.error(f"Error fetching transport services: {response.text}")
        return []


def get_transport_recommendations(lat, lng):
    transport_services = find_transport_services(lat, lng)
    if not transport_services:
        return {"recommendations": [], "summary": "No transport services found nearby."}

    transport_with_distances = []
    for service in transport_services:
        service_lat = service.get('geometry', {}).get('location', {}).get('lat')
        service_lng = service.get('geometry', {}).get('location', {}).get('lng')
        if service_lat and service_lng:
            distance = haversine(lat, lng, service_lat, service_lng)
            service['distance'] = round(distance, 2)
            transport_with_distances.append(service)

    prompt = "Given the following transport services..."
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        answer = response.choices[0].message['content'].strip()
        return {"recommendations": transport_with_distances, "summary": answer}
    except openai.error.OpenAIError as e:
        app.logger.error(f"OpenAI API error: {str(e)}")
        return {"recommendations": [], "summary": "OpenAI API error occurred."}

# Other routes and functions remain unchanged...

@app.route('/transport', methods=['POST'])
def transport():
    data = request.json
    lat = data.get('latitude')
    lng = data.get('longitude')

    if not lat or not lng:
        return jsonify({'error': 'Latitude and longitude are required'}), 400

    recommendations = get_transport_recommendations(lat, lng)
    return jsonify(recommendations)

@app.route('/api/warehouses', methods=['POST'])
def warehouses():
    data = request.json
    lat = data.get('latitude')
    lng = data.get('longitude')

    if not lat or not lng:
        return jsonify({'error': 'Latitude and longitude are required'}), 400

    recommendations = get_warehouse_recommendations(lat, lng)
    return jsonify(recommendations)


def find_warehouse_services(lat, lng):
    """
    Find nearby warehouse and food storage services using Google Maps Places API.
    """
    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lng}&radius=200000&type=storage&keyword=warehouse%7Cstorage%7Cfood%20storage&key={GOOGLE_MAPS_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('results', [])
    else:
        app.logger.error(f"Error fetching warehouse services: {response.text}")
        return []


def get_warehouse_recommendations(lat, lng):
    """
    Get warehouse recommendations using Google Maps API and OpenAI for analysis.
    """
    warehouse_services = find_warehouse_services(lat, lng)
    if not warehouse_services:
        return {"recommendations": [], "summary": "No warehouse services found nearby."}

    warehouse_with_distances = []
    for service in warehouse_services:
        service_lat = service.get('geometry', {}).get('location', {}).get('lat')
        service_lng = service.get('geometry', {}).get('location', {}).get('lng')
        if service_lat and service_lng:
            distance = haversine(lat, lng, service_lat, service_lng)
            service['distance'] = round(distance, 2)  # Distance in km rounded to 2 decimal places
            warehouse_with_distances.append(service)

    # Build a prompt for OpenAI to evaluate services
    prompt = "Given the following warehouse services with their names, ratings, distances, and prices, provide the best recommendations:\n\n"
    for service in warehouse_with_distances:
        name = service.get('name', 'Unknown service')
        rating = service.get('rating', 'No rating available')
        distance = service.get('distance', 'N/A')
        price = service.get('price_level', 'N/A')
        prompt += f"- Name: {name}, Rating: {rating}, Distance: {distance} km, Price: {price}\n"

    prompt += "\nPlease provide a summary and the best option."

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are an assistant specialized in warehouse recommendations."},
                {"role": "user", "content": prompt}
            ]
        )
        answer = response.choices[0].message['content'].strip()
        app.logger.debug(f"Generated warehouse recommendations: {answer}")
        return {"recommendations": warehouse_with_distances, "summary": answer}
    except openai.error.OpenAIError as e:
        app.logger.error(f"OpenAI API error: {str(e)}")
        return {"recommendations": [], "summary": "OpenAI API error occurred."}

def find_mandi_services(lat, lng):
    """
    Find nearby mandi (market) services using Google Maps Places API.
    """
    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lng}&radius=200000&type=market&keyword=mandi%7Cagriculture%20market%7Cfarmer%20market&key={GOOGLE_MAPS_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('results', [])
    else:
        app.logger.error(f"Error fetching mandi services: {response.text}")
        return []


def get_mandi_recommendations(lat, lng):
    """
    Get mandi recommendations using Google Maps API and OpenAI for analysis.
    """
    mandi_services = find_mandi_services(lat, lng)
    if not mandi_services:
        return {"recommendations": [], "summary": "No mandi services found nearby."}

    mandi_with_distances = []
    for service in mandi_services:
        service_lat = service.get('geometry', {}).get('location', {}).get('lat')
        service_lng = service.get('geometry', {}).get('location', {}).get('lng')
        if service_lat and service_lng:
            distance = haversine(lat, lng, service_lat, service_lng)
            service['distance'] = round(distance, 2)  # Distance in km rounded to 2 decimal places
            mandi_with_distances.append(service)

    # Build a prompt for OpenAI to evaluate services
    prompt = "Given the following mandi (market) services with their names, ratings, distances, and prices, provide the best recommendations:\n\n"
    for service in mandi_with_distances:
        name = service.get('name', 'Unknown service')
        rating = service.get('rating', 'No rating available')
        distance = service.get('distance', 'N/A')
        price = service.get('price_level', 'N/A')
        prompt += f"- Name: {name}, Rating: {rating}, Distance: {distance} km, Price: {price}\n"

    prompt += "\nPlease provide a summary and the best option."

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are an assistant specialized in agricultural market recommendations."},
                {"role": "user", "content": prompt}
            ]
        )
        answer = response.choices[0].message['content'].strip()
        app.logger.debug(f"Generated mandi recommendations: {answer}")
        return {"recommendations": mandi_with_distances, "summary": answer}
    except openai.error.OpenAIError as e:
        app.logger.error(f"OpenAI API error: {str(e)}")
        return {"recommendations": [], "summary": "OpenAI API error occurred."}


@app.route('/mandis', methods=['POST'])
def mandis():
    """
    API endpoint to get mandi recommendations.
    """
    data = request.json
    lat = data.get('latitude')
    lng = data.get('longitude')

    if not lat or not lng:
        return jsonify({'error': 'Latitude and longitude are required'}), 400

    recommendations = get_mandi_recommendations(lat, lng)
    return jsonify(recommendations)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)