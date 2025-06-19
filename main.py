from flask import Flask, request, render_template, jsonify, session, redirect, url_for, flash, send_file
import numpy as np
import pandas as pd
import pickle
from flask_mysqldb import MySQL
import MySQLdb.cursors
from datetime import datetime, time, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a secure random string

# MySQL Configuration
app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Nithil@james7'
app.config['MYSQL_DB'] = 'sympto'

mysql = MySQL(app)
# chills,vomiting,high_fever,sweating,headache,nausea,diarrhoea,muscle_pain
# Load datasets (adjust paths as needed)
try:
    sym_des = pd.read_csv("C:\\Users\\nithi\\OneDrive\\Desktop\\Final\\Medicine-Recommendation-System-Personalized-Medical-Recommendation-System-with-Machine-Learning\\symtoms_df.csv")
    precautions = pd.read_csv("C:\\Users\\nithi\\OneDrive\\Desktop\\Final\\Medicine-Recommendation-System-Personalized-Medical-Recommendation-System-with-Machine-Learning\\precautions_df.csv")
    workout = pd.read_csv("C:\\Users\\nithi\\OneDrive\\Desktop\\Final\\Medicine-Recommendation-System-Personalized-Medical-Recommendation-System-with-Machine-Learning\\workout_df.csv")
    description = pd.read_csv("C:\\Users\\nithi\\OneDrive\\Desktop\\Final\\Medicine-Recommendation-System-Personalized-Medical-Recommendation-System-with-Machine-Learning\\description.csv")
    medications = pd.read_csv('C:\\Users\\nithi\\OneDrive\\Desktop\\Final\\Medicine-Recommendation-System-Personalized-Medical-Recommendation-System-with-Machine-Learning\\medications.csv')
    diets = pd.read_csv("C:\\Users\\nithi\\OneDrive\\Desktop\\Final\\Medicine-Recommendation-System-Personalized-Medical-Recommendation-System-with-Machine-Learning\\diets.csv")
except Exception as e:
    print(f"Error loading CSV files: {e}")
    exit(1)

# Load model
svc = pickle.load(open('C:\\Users\\nithi\\OneDrive\\Desktop\\Final\\Medicine-Recommendation-System-Personalized-Medical-Recommendation-System-with-Machine-Learning\\nithil_svc.pkl', 'rb'))

# Disease to Specialist Mapping
disease_specialist_map = {
    'Fungal infection': 'Dermatologist',
    'Allergy': 'Allergist',
    'GERD': 'Gastroenterologist',
    'Chronic cholestasis': 'Hepatologist',
    'Drug Reaction': 'Dermatologist',
    'Peptic ulcer diseae': 'Gastroenterologist',
    'AIDS': 'Infectious Disease Specialist',
    'Diabetes ': 'Endocrinologist',
    'Gastroenteritis': 'Gastroenterologist',
    'Bronchial Asthma': 'Pulmonologist',
    'Hypertension ': 'Cardiologist',
    'Migraine': 'Neurologist',
    'Cervical spondylosis': 'Orthopedic Surgeon',
    'Paralysis (brain hemorrhage)': 'Neurologist',
    'Jaundice': 'Hepatologist',
    'Malaria': 'Infectious Disease Specialist',
    'Chicken pox': 'Infectious Disease Specialist',
    'Dengue': 'Infectious Disease Specialist',
    'Typhoid': 'Infectious Disease Specialist',
    'hepatitis A': 'Hepatologist',
    'Hepatitis B': 'Hepatologist',
    'Hepatitis C': 'Hepatologist',
    'Hepatitis D': 'Hepatologist',
    'Hepatitis E': 'Hepatologist',
    'Alcoholic hepatitis': 'Hepatologist',
    'Tuberculosis': 'Pulmonologist',
    'Common Cold': 'General Practitioner',
    'Pneumonia': 'Pulmonologist',
    'Dimorphic hemmorhoids(piles)': 'Gastroenterologist',
    'Heart attack': 'Cardiologist',
    'Varicose veins': 'Vascular Surgeon',
    'Hypothyroidism': 'Endocrinologist',
    'Hyperthyroidism': 'Endocrinologist',
    'Hypoglycemia': 'Endocrinologist',
    'Osteoarthristis': 'Orthopedic Surgeon',
    'Arthritis': 'Rheumatologist',
    '(vertigo) Paroymsal  Positional Vertigo': 'Neurologist',
    'Acne': 'Dermatologist',
    'Urinary tract infection': 'Urologist',
    'Psoriasis': 'Dermatologist',
    'Impetigo': 'Dermatologist'
}

# Helper function to fetch disease details
def helper(dis):
    desc = description[description['Disease'] == dis]['Description']
    desc = " ".join(desc) if not desc.empty else "No description available"

    pre_df = precautions[precautions['Disease'] == dis][['Precaution_1', 'Precaution_2', 'Precaution_3', 'Precaution_4']]
    pre = pre_df.iloc[0].tolist() if not pre_df.empty else ["No precautions available"]

    med_series = medications[medications['Disease'] == dis]['Medication']
    med = med_series.tolist() if not med_series.empty else ["No medications available"]

    die_series = diets[diets['Disease'] == dis]['Diet']
    die = die_series.tolist() if not die_series.empty else ["No diet recommendations available"]

    wrkout_series = workout[workout['disease'] == dis]['workout']
    wrkout = wrkout_series.tolist() if not wrkout_series.empty else ["No workouts available"]

    return desc, pre, med, die, wrkout

# Function to fetch all doctors
def get_all_doctors():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM doctor_details')
    doctors = cursor.fetchall()
    cursor.close()
    return doctors

# Function to fetch recommended doctors based on disease
def get_recommended_doctors(disease):
    specialist = disease_specialist_map.get(disease, 'General Practitioner')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM doctor_details WHERE specialist = %s', (specialist,))
    doctors = cursor.fetchall()
    cursor.close()
    return doctors if doctors else None

# Function to fetch doctor details by ID
def get_doctor_by_id(doctor_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM doctor_details WHERE doctor_id = %s', (doctor_id,))
    doctor = cursor.fetchone()
    cursor.close()
    return doctor

# Function to fetch user's appointments
def get_user_appointments(user_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT a.*, d.doctor_name, d.specialist, d.hospital_name, d.place, d.pincode, d.contact_number 
        FROM appointments a 
        JOIN doctor_details d ON a.doctor_id = d.doctor_id 
        WHERE a.user_id = %s 
        ORDER BY a.appointment_date, a.visit_time
    ''', (user_id,))
    appointments = cursor.fetchall()
    cursor.close()
    
    # Convert timedelta to time object for visit_time
    for appointment in appointments:
        if isinstance(appointment['visit_time'], timedelta):
            total_seconds = appointment['visit_time'].total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            appointment['visit_time'] = time(hours, minutes)
    return appointments

# Symptom dictionary and disease list
symptoms_dict = {
    'itching': 0, 'skin_rash': 1, 'nodal_skin_eruptions': 2, 'continuous_sneezing': 3, 'shivering': 4, 'chills': 5, 
    'joint_pain': 6, 'stomach_pain': 7, 'acidity': 8, 'ulcers_on_tongue': 9, 'muscle_wasting': 10, 'vomiting': 11, 
    'burning_micturition': 12, 'spotting_ urination': 13, 'fatigue': 14, 'weight_gain': 15, 'anxiety': 16, 
    'cold_hands_and_feets': 17, 'mood_swings': 18, 'weight_loss': 19, 'restlessness': 20, 'lethargy': 21, 
    'patches_in_throat': 22, 'irregular_sugar_level': 23, 'cough': 24, 'high_fever': 25, 'sunken_eyes': 26, 
    'breathlessness': 27, 'sweating': 28, 'dehydration': 29, 'indigestion': 30, 'headache': 31, 'yellowish_skin': 32, 
    'dark_urine': 33, 'nausea': 34, 'loss_of_appetite': 35, 'pain_behind_the_eyes': 36, 'back_pain': 37, 
    'constipation': 38, 'abdominal_pain': 39, 'diarrhoea': 40, 'mild_fever': 41, 'yellow_urine': 42, 
    'yellowing_of_eyes': 43, 'acute_liver_failure': 44, 'fluid_overload': 45, 'swelling_of_stomach': 46, 
    'swelled_lymph_nodes': 47, 'malaise': 48, 'blurred_and_distorted_vision': 49, 'phlegm': 50, 'throat_irritation': 51, 
    'redness_of_eyes': 52, 'sinus_pressure': 53, 'runny_nose': 54, 'congestion': 55, 'chest_pain': 56, 
    'weakness_in_limbs': 57, 'fast_heart_rate': 58, 'pain_during_bowel_movements': 59, 'pain_in_anal_region': 60, 
    'bloody_stool': 61, 'irritation_in_anus': 62, 'neck_pain': 63, 'dizziness': 64, 'cramps': 65, 'bruising': 66, 
    'obesity': 67, 'swollen_legs': 68, 'swollen_blood_vessels': 69, 'puffy_face_and_eyes': 70, 'enlarged_thyroid': 71, 
    'brittle_nails': 72, 'swollen_extremeties': 73, 'excessive_hunger': 74, 'extra_marital_contacts': 75, 
    'drying_and_tingling_lips': 76, 'slurred_speech': 77, 'knee_pain': 78, 'hip_joint_pain': 79, 'muscle_weakness': 80, 
    'stiff_neck': 81, 'swelling_joints': 82, 'movement_stiffness': 83, 'spinning_movements': 84, 'loss_of_balance': 85, 
    'unsteadiness': 86, 'weakness_of_one_body_side': 87, 'loss_of_smell': 88, 'bladder_discomfort': 89, 
    'foul_smell_of urine': 90, 'continuous_feel_of_urine': 91, 'passage_of_gases': 92, 'internal_itching': 93, 
    'toxic_look_(typhos)': 94, 'depression': 95, 'irritability': 96, 'muscle_pain': 97, 'altered_sensorium': 98, 
    'red_spots_over_body': 99, 'belly_pain': 100, 'abnormal_menstruation': 101, 'dischromic _patches': 102, 
    'watering_from_eyes': 103, 'increased_appetite': 104, 'FRCpolyuria': 105, 'family_history': 106, 'mucoid_sputum': 107, 
    'rusty_sputum': 108, 'lack_of_concentration': 109, 'visual_disturbances': 110, 'receiving_blood_transfusion': 111, 
    'receiving_unsterile_injections': 112, 'coma': 113, 'stomach_bleeding': 114, 'distention_of_abdomen': 115, 
    'history_of_alcohol_consumption': 116, 'fluid_overload.1': 117, 'blood_in_sputum': 118, 'prominent_veins_on_calf': 119, 
    'palpitations': 120, 'painful_walking': 121, 'pus_filled_pimples': 122, 'blackheads': 123, 'scurring': 124, 
    'skin_peeling': 125, 'silver_like_dusting': 126, 'small_dents_in_nails': 127, 'inflammatory_nails': 128, 
    'blister': 129, 'red_sore_around_nose': 130, 'yellow_crust_ooze': 131
}
diseases_list = {
    15: 'Fungal infection', 4: 'Allergy', 16: 'GERD', 9: 'Chronic cholestasis', 14: 'Drug Reaction', 
    33: 'Peptic ulcer diseae', 1: 'AIDS', 12: 'Diabetes ', 17: 'Gastroenteritis', 6: 'Bronchial Asthma', 
    23: 'Hypertension ', 30: 'Migraine', 7: 'Cervical spondylosis', 32: 'Paralysis (brain hemorrhage)', 
    28: 'Jaundice', 29: 'Malaria', 8: 'Chicken pox', 11: 'Dengue', 37: 'Typhoid', 40: 'hepatitis A', 
    19: 'Hepatitis B', 20: 'Hepatitis C', 21: 'Hepatitis D', 22: 'Hepatitis E', 3: 'Alcoholic hepatitis', 
    36: 'Tuberculosis', 10: 'Common Cold', 34: 'Pneumonia', 13: 'Dimorphic hemmorhoids(piles)', 18: 'Heart attack', 
    39: 'Varicose veins', 26: 'Hypothyroidism', 24: 'Hyperthyroidism', 25: 'Hypoglycemia', 31: 'Osteoarthristis', 
    5: 'Arthritis', 0: '(vertigo) Paroymsal  Positional Vertigo', 2: 'Acne', 38: 'Urinary tract infection', 
    35: 'Psoriasis', 27: 'Impetigo'
}

# Model Prediction function
def get_predicted_value(patient_symptoms):
    input_vector = np.zeros(len(symptoms_dict))
    invalid_symptoms = []
    for item in patient_symptoms:
        if item in symptoms_dict:
            input_vector[symptoms_dict[item]] = 1
        else:
            invalid_symptoms.append(item)
    if invalid_symptoms or not patient_symptoms:
        return None, invalid_symptoms if invalid_symptoms else ["No symptoms provided"]
    return diseases_list[svc.predict([input_vector])[0]], None

# Login required decorator
def login_required(f):
    def wrap(*args, **kwargs):
        if 'loggedin' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

# Chatbot logic
def get_chatbot_response(user_input):
    user_input = user_input.lower().strip()
    
    # Greetings
    if any(greet in user_input for greet in ["hello", "hi", "hey"]):
        return "Hello! How can I assist you with your health today?"
    
    # Symptom-related queries
    elif "symptom" in user_input or "feel" in user_input or "sick" in user_input:
        return "Please tell me more about your symptoms (e.g., fever, cough, headache), and I’ll try to help you."
    
    # Disease prediction based on symptoms
    elif any(symptom in user_input for symptom in symptoms_dict.keys()):
        symptoms = [s for s in symptoms_dict.keys() if s in user_input]
        if symptoms:
            predicted_disease, error = get_predicted_value(symptoms)
            if predicted_disease:
                desc, pre, med, diet, workout = helper(predicted_disease)
                response = f"Based on your symptoms, you might have **{predicted_disease}**. Here’s a brief description: {desc}\n\n" \
                           f"**Precautions**: {', '.join(pre)}\n" \
                           f"**Medications**: {', '.join(med)}\n" \
                           f"**Diet**: {', '.join(diet)}\n" \
                           f"**Workouts**: {', '.join(workout)}\n\n" \
                           "Please consult a doctor for a proper diagnosis!"
                return response
            else:
                return "I couldn’t identify a disease based on that. Could you provide more specific symptoms?"
        return "I didn’t catch any specific symptoms. Could you list them clearly (e.g., fever, cough)?"
    
    # Doctor-related queries
    elif "doctor" in user_input or "specialist" in user_input:
        if "list" in user_input or "all" in user_input:
            doctors = get_all_doctors()
            if doctors:
                doctor_list = "\n".join([f"- {d['doctor_name']} ({d['specialist']}) - {d['hospital_name']}, {d['place']}" for d in doctors])
                return f"Here are all available doctors:\n{doctor_list}"
            return "No doctors are available in the database right now."
        return "Do you need help finding a doctor? Mention a disease or specialty (e.g., 'cardiologist') for recommendations."
    
    # Appointment booking assistance
    elif "appointment" in user_input or "book" in user_input:
        return "To book an appointment, please visit the 'Appointments' section after predicting a disease or tell me a doctor’s name/specialty to guide you."
    
    # General health advice
    elif "health" in user_input or "tips" in user_input:
        return "For general health, stay hydrated, eat a balanced diet, exercise regularly, and get enough sleep. Any specific concerns?"
    
    # Exit or goodbye
    elif "bye" in user_input or "exit" in user_input or "goodbye" in user_input:
        return "Goodbye! Stay healthy and feel free to come back if you need help."
    
    # Default response
    return "I’m not sure how to help with that. Try asking about symptoms, diseases, doctors, or health tips!"

# Routes
@app.route('/')
def index():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    all_diseases = list(diseases_list.values())
    symptoms_list = list(symptoms_dict.keys())
    all_doctors = get_all_doctors()
    return render_template('index.html', all_diseases=all_diseases, symptoms_list=symptoms_list, all_doctors=all_doctors)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM login WHERE username = %s AND password = %s', (username, password))
        user = cursor.fetchone()
        cursor.close()
        if user:
            session['loggedin'] = True
            session['username'] = user['username']
            session['user_id'] = user['id']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM login WHERE username = %s', (username,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            flash('Username already exists.', 'danger')
            cursor.close()
            return render_template('register.html')

        cursor.execute('SELECT * FROM login WHERE email = %s', (email,))
        existing_email = cursor.fetchone()
        
        if existing_email:
            flash('Email already exists.', 'danger')
            cursor.close()
            return render_template('register.html')

        cursor.execute('INSERT INTO login (username, email, password) VALUES (%s, %s, %s)', (username, email, password))
        mysql.connection.commit()
        cursor.close()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('username', None)
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/predict', methods=['GET', 'POST'])
@login_required
def predict():
    all_diseases = list(diseases_list.values())
    symptoms_list = list(symptoms_dict.keys())
    all_doctors = get_all_doctors()
    if request.method == 'POST':
        user_symptoms = request.form.getlist('symptoms')
        print("User selected symptoms:", user_symptoms)
        if not user_symptoms:
            flash("Please select at least one symptom.", 'warning')
            return render_template('index.html', all_diseases=all_diseases, symptoms_list=symptoms_list, all_doctors=all_doctors)
        predicted_disease, invalid_symptoms = get_predicted_value(user_symptoms)
        if predicted_disease is None:
            flash(f"Prediction failed: {', '.join(invalid_symptoms)}", 'danger')
            return render_template('index.html', all_diseases=all_diseases, symptoms_list=symptoms_list, all_doctors=all_doctors)
        dis_des, precautions, medications, rec_diet, workout = helper(predicted_disease)
        recommended_doctors = get_recommended_doctors(predicted_disease)
        return render_template('index.html', predicted_disease=predicted_disease, dis_des=dis_des,
                               my_precautions=precautions, medications=medications, my_diet=rec_diet,
                               workout=workout, recommended_doctors=recommended_doctors,
                               all_diseases=all_diseases, symptoms_list=symptoms_list, all_doctors=all_doctors)
    return render_template('index.html', all_diseases=all_diseases, symptoms_list=symptoms_list, all_doctors=all_doctors)

@app.route('/about')
def about():
    return render_template("about.html")

@app.route('/contact')
def contact():
    return render_template("contact.html")

@app.route('/blog')
def blog():
    return render_template("blog.html")

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM information WHERE user_id = %s', (session['user_id'],))
    profile_info = cursor.fetchone()
    
    if request.method == 'POST':
        phone_number = request.form['phone_number']
        age = request.form['age']
        gender = request.form['gender']
        address = request.form['address']

        if profile_info:
            cursor.execute('''
                UPDATE information 
                SET phone_number = %s, age = %s, gender = %s, address = %s 
                WHERE user_id = %s
            ''', (phone_number, age, gender, address, session['user_id']))
            flash('Profile updated successfully!', 'success')
        else:
            cursor.execute('''
                INSERT INTO information (user_id, phone_number, age, gender, address) 
                VALUES (%s, %s, %s, %s, %s)
            ''', (session['user_id'], phone_number, age, gender, address))
            flash('Profile created successfully!', 'success')
        
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('profile'))
    
    cursor.close()
    return render_template('profile.html', profile_info=profile_info)

@app.route('/book_appointment/<doctor_id>', methods=['GET', 'POST'])
@login_required
def book_appointment(doctor_id):
    doctor = get_doctor_by_id(doctor_id)
    if not doctor:
        flash('Doctor not found.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        patient_name = request.form['patient_name']
        age = request.form['age']
        gender = request.form['gender']
        appointment_date = request.form['appointment_date']
        visit_time = request.form['visit_time']

        # Basic validation
        try:
            appointment_date = datetime.strptime(appointment_date, '%Y-%m-%d').date()
            visit_time = datetime.strptime(visit_time, '%H:%M').time()
            if appointment_date < datetime.now().date():
                flash('Appointment date cannot be in the past.', 'danger')
                return render_template('book_appointment.html', doctor=doctor)
            age = int(age)
            if age <= 0 or age > 150:
                raise ValueError("Invalid age")
        except ValueError as e:
            flash(f'Invalid input: {str(e)}', 'danger')
            return render_template('book_appointment.html', doctor=doctor)

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('''
            INSERT INTO appointments (user_id, doctor_id, patient_name, age, gender, appointment_date, visit_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (session['user_id'], doctor_id, patient_name, age, gender, appointment_date, visit_time))
        mysql.connection.commit()
        cursor.close()
        flash(f'Appointment booked successfully with Dr. {doctor["doctor_name"]} on {appointment_date} at {visit_time.strftime("%H:%M")}.', 'success')
        return redirect(url_for('appointments'))  # Redirect to appointments page after booking

    return render_template('book_appointment.html', doctor=doctor)  # Render booking form for GET request

@app.route('/appointments')
@login_required
def appointments():
    appointments = get_user_appointments(session['user_id'])
    return render_template('appointments.html', appointments=appointments)

@app.route('/download_appointment/<int:appointment_id>')
@login_required
def download_appointment(appointment_id):
    appointments = get_user_appointments(session['user_id'])
    appointment = next((appt for appt in appointments if appt['appointment_id'] == appointment_id), None)
    if not appointment:
        flash('Appointment not found.', 'danger')
        return redirect(url_for('appointments'))

    # Generate PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph("Appointment Details", styles['Heading1']))
    elements.append(Spacer(1, 12))

    # Appointment Details Table
    data = [
        ["Field", "Details"],
        ["Patient Name", appointment['patient_name']],
        ["Doctor Name", appointment['doctor_name']],
        ["Specialist", appointment['specialist']],
        ["Hospital", appointment['hospital_name']],
        ["Location", f"{appointment['place']}, {appointment['pincode']}"],
        ["Contact", appointment['contact_number']],
        ["Date", appointment['appointment_date'].strftime('%Y-%m-%d')],
        ["Time", appointment['visit_time'].strftime('%H:%M')],
        ["Age", str(appointment['age'])],
        ["Gender", appointment['gender']],
        ["Status", appointment['status']],
        ["Booked On", appointment['booking_time'].strftime('%Y-%m-%d %H:%M:%S')]
    ]
    table = Table(data, colWidths=[150, 300])
    table.setStyle([
        ('BACKGROUND', (0, 0), (-1, 0), '#3529a1'),
        ('TEXTCOLOR', (0, 0), (-1, 0), '#ffffff'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 1, '#000000'),
        ('BACKGROUND', (0, 1), (-1, -1), '#f8fbff'),
    ])
    elements.append(table)
    elements.append(Spacer(1, 24))

    # Instructions Section
    elements.append(Paragraph("Important Instructions for Your Appointment", styles['Heading2']))
    elements.append(Spacer(1, 12))
    instructions = [
        "Carry the appointment letter with you.",
        "Bring all original documents related to your medical history.",
        "Arrive at least 15 minutes early for a smooth check-in process.",
        "Follow any pre-appointment guidelines provided by the hospital.",
        "In case of rescheduling, contact the hospital in advance.",
        "Wishing you a smooth and successful consultation."
    ]
    for instruction in instructions:
        elements.append(Paragraph(f"• {instruction}", styles['BodyText']))
        elements.append(Spacer(1, 6))

    # Logo Placeholder (replace with actual image path if available)
    elements.append(Spacer(1, 24))
    logo_path = "C:\\Users\\nithi\\OneDrive\\Desktop\\Final\\Medicine-Recommendation-System-Personalized-Medical-Recommendation-System-with-Machine-Learning\\static\\aap2.png"  # Replace with actual path
    elements.append(Image(logo_path, width=100, height=100))
    seal = Paragraph("<b>SymtoMedAi Seal</b>", styles['Normal'])
    seal_style = styles['Normal']
    seal_style.alignment = 1  # Center alignment
    seal_style.textColor = colors.darkblue
    elements.append(seal)

    # Build the PDF
    doc.build(elements)
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name=f"appointment_{appointment_id}.pdf", mimetype='application/pdf')

# Chatbot Routes
@app.route('/chatbot')
@login_required
def chatbot():
    return render_template('chatbot.html')

@app.route('/chatbot_response', methods=['POST'])
@login_required
def chatbot_response():
    user_input = request.form.get('message')
    if not user_input:
        return jsonify({'response': 'Please type something!'})
    response = get_chatbot_response(user_input)
    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(debug=True)