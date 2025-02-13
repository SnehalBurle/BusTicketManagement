from flask import Flask, render_template, request, redirect, url_for, flash, jsonify,  request, render_template
import mysql.connector
from flask_bcrypt import Bcrypt
import serial, requests
import threading

rfid_scanned = False
current_rfid = None
station_data = {}
station_name = ''

app = Flask(__name__)
bcrypt = Bcrypt(app)


# Database Configuration
def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='root',
        database='bus_ticket_management'
    )

# Routes
@app.route('/')
def index():
    return render_template('index.html')

def register():
    user_name = ""
    password = ""
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO register(USERNAME, PASSWORD) VALUES (%s, %s)", (user_name, hashed_password))
    conn.commit()
    conn.close()
    cursor.close()

@app.route('/login', methods=['POST'])
def admin_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT PASSWORD FROM register WHERE USERNAME = %s", (username,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        if result and bcrypt.check_password_hash(result['PASSWORD'], password):
            return jsonify({'success':True, 'message': 'Login successful'}), 200
        else:
            return jsonify({'success':False, 'error': 'Invalid username or password'}), 401

    except mysql.connector.Error as err:
        return jsonify({'Success':False, 'error': f'Database error: {err}'}), 500

@app.route('/get_routes', methods=['GET'])
def get_routes():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT RouteNo FROM routes")
        routes = [row[0] for row in cursor.fetchall()]
        return jsonify({'routes': routes})
    except Exception as e:
        return jsonify({'error': str(e)})
    finally:
            cursor.close()
            connection.close()

@app.route('/get_stations_for_bus', methods=['GET'])
def get_stations_for_bus():
    route_no = request.args.get('route_no')
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT STATION_NAME FROM stations WHERE RouteNo = %s ORDER BY STATION_NUMBER", (route_no,))
        stations = [row[0] for row in cursor.fetchall()]
        return jsonify({'success' : True, 'stations': stations})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
            cursor.close()
            connection.close()

@app.route('/add_rfid_user', methods=['POST'])
def add_rfid_user():
    data = request.get_json()
    rfid_no = data['rfid_no']
    balance = data['balance']
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO passenger (RFIDNo, Balance) VALUES (%s, %s)" %(rfid_no, balance))
        cursor.execute("INSERT INTO recharge (RFIDNo, RechargeAmount) VALUES (%s, %s)" %(rfid_no, balance))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'RFID User added successfully'})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/get_balance', methods=['GET'])
def get_balance():
    rfid_no = request.args.get('rfid_no')
    if not rfid_no:
        return jsonify({'success': False, 'message': 'RFID number is required'})
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT balance FROM passenger WHERE rfidno = %s"
        cursor.execute(query, (rfid_no,))
        result = cursor.fetchone()
        if result:
            return jsonify({'success': True, 'balance': result['balance']})
        else:
            return jsonify({'success': False, 'message': 'RFID not found'})
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': f'Database error: {err}'})
    finally:
        cursor.close()
        conn.close()

@app.route('/update_balance', methods=['POST'])
def update_balance():
    data = request.json
    rfid_no = data.get('rfid_no')
    amount = data.get('amount')
    if not rfid_no or not amount or float(amount) <= 0:
        return jsonify({'success': False, 'message': 'Invalid input data.'})
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE passenger SET Balance = Balance + %s WHERE RFIDNo = %s", (amount, rfid_no))
        cur.execute("INSERT INTO recharge (RFIDNo, RechargeAmount) VALUES (%s, %s)", (rfid_no, amount))
        conn.commit()
        cur.execute("SELECT balance FROM passenger WHERE rfidno = %s", (rfid_no,))
        new_balance = cur.fetchone()[0]
        cur.close()
        return jsonify({'success': True, 'new_balance': new_balance, 'message': 'Balance updated successfully.'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/add_route', methods=['POST'])
def add_route():
    route_name = request.json.get('route_number')
    start_stop = request.json.get('start_stop')
    end_stop = request.json.get('end_stop')
    if not route_name or not start_stop or not end_stop:
        return jsonify({'success': False, 'message': 'Please provide all required fields (route name, start stop, end stop)'}), 400
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO routes (RouteNo, SOURCE, DESTINATION) VALUES (%s, %s, %s)", (route_name.upper(), start_stop.upper(), end_stop.upper()))
        return jsonify({'success': True, 'message': 'Route added successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cur.close()
        conn.commit()

@app.route('/get_stations', methods=['GET'])
def get_stations():
    route_no = request.args.get('route_no')
    route_no=route_no.upper()
    if not route_no:
        return jsonify({"success": False, "message": "Route number is required."})
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT SOURCE FROM routes WHERE RouteNo = %s", (route_no,))
        result = cursor.fetchone()
        if result:
            return jsonify({"success": True, 'route_no': route_no})
        else:
            return jsonify({"success": False, "message": "No Route as Mentioned"})
    except mysql.connector.Error as err:
        return jsonify({"success": False, "message": f"Database error: {err}"})
    finally:
        cursor.close()
        conn.close()

@app.route('/save_stations', methods=['POST'])
def save_stations():
    data = request.get_json()
    route_no = data.get('route_no')
    stations = data.get('stations')
    if not route_no or not stations:
        return jsonify({"success": False, "message": "Route number and stations are required."})
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM stations WHERE RouteNo = %s", (route_no,))
        for order, station_name in enumerate(stations, start=1):
            cursor.execute("INSERT INTO stations (RouteNo, STATION_NUMBER, STATION_NAME) VALUES (%s, %s, %s)",
                           (route_no, order, station_name.upper()))
        conn.commit()
        return jsonify({"success": True, "message": "Stations updated successfully."})
    except mysql.connector.Error as err:
        return jsonify({"success": False, "message": f"Database error: {err}"})
    finally:
        cursor.close()
        conn.close()

@app.route('/get_stations_for_route', methods=['GET'])
def get_stations_for_route():
    route_no = request.args.get('route_no')
    routeno=route_no.upper()
    if not route_no:
        return jsonify({'success': False, 'message': 'Route number is required'}), 400
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        query = "SELECT STATION_NAME FROM stations WHERE RouteNo = %s"
        cursor.execute(query, (routeno,))
        stations = [row[0] for row in cursor.fetchall()]
        cursor.close()
        connection.close()
        if stations:
            return jsonify({'success': True, 'stations': stations})
        else:
            return jsonify({'success': False, 'message': 'No stations found for this route'})
    else:
        return jsonify({'success': False, 'message': 'Database connection error'})

@app.route('/update_fare_for_route', methods=['POST'])
def update_fare_for_route():
    data = request.get_json()
    route_no = data.get('route_no')
    source_station = data.get('source_station')
    destination_station = data.get('destination_station')
    fare = data.get('fare')
    if not route_no or not source_station or not destination_station or fare is None:
        return jsonify({'success': False, 'message': 'All fields are required'}), 400
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        query1 = "SELECT Fare from fare where RouteNo=%s and Station1=%s and Station2=%s"
        cursor.execute(query1,(route_no,source_station,destination_station))
        if cursor.fetchone():
            cursor.execute("UPDATE fare SET Fare = %s WHERE RouteNo = %s and Station1=%s and Station2=%s", (fare, route_no,source_station,destination_station))
        else:
            query = "INSERT INTO fare (RouteNo, Station1, Station2, Fare) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE Fare = %s"
            cursor.execute(query, (route_no.upper(), source_station, destination_station, fare, fare))
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'success': True, 'message': 'Fare updated successfully'})
    else:
        return jsonify({'success': False, 'message': 'Database connection error'})

@app.route('/get_recharge_info', methods=['POST'])
def get_recharge_info():
    try:
        data = request.json
        rfid = data.get('rfid')
        connection = get_db_connection()
        if not rfid:
            return jsonify({'success': False, 'message': 'RFID number is required.'})
        cursor = connection.cursor()
        query = "SELECT RechargeDate, RechargeAmount FROM recharge WHERE RFIDNo = %s ORDER BY RechargeDate DESC"
        cursor.execute(query, (rfid,))
        recharges = cursor.fetchall()
        return jsonify({'success': True, 'recharges': recharges})
    except Exception as e:
        print("Error:", e)
        return jsonify({'success': False, 'message': 'An error occurred while fetching recharge info.'})

@app.route('/get_ticket_date', methods=['POST'])
def get_ticket_date():
    try:
        data = request.json
        route = data.get('route')
        Date = data.get('Date')
        connection = get_db_connection()
        cursor = connection.cursor()
        query = "SELECT ROUTENO,TIMESTAMP,START_STOP,END_STOP,FARE FROM TICKET WHERE ROUTENO = %s AND DATE(TIMESTAMP) = %s ORDER BY TIMESTAMP DESC"
        cursor.execute(query, (route,Date))
        tickets = cursor.fetchall()
        return jsonify({'success': True, 'recharges': tickets})
    except Exception as e:
        print("Error:", e)
        return jsonify({'success': False, 'message': str(e)})

@app.route('/get_tickets_info', methods=['POST'])
def get_tickets_info():
    try:
        data = request.json
        rfid = data.get('rfid')
        connection = get_db_connection()
        if not rfid:
            return jsonify({'success': False, 'message': 'RFID number is required.'})
        cursor = connection.cursor()
        query = "SELECT ROUTENO,TIMESTAMP,START_STOP,END_STOP,FARE FROM TICKET WHERE RFID_NO = %s ORDER BY TIMESTAMP DESC"
        cursor.execute(query, (rfid,))
        tickets = cursor.fetchall()
        return jsonify({'success': True, 'recharges': tickets})
    except Exception as e:
        print("Error:", e)
        return jsonify({'success': False, 'message': str(e)})


@app.route('/check_rfid', methods=['GET'])
def check_rfid():
	global rfid_scanned
	if rfid_scanned:
		rfid_scanned = False
		return jsonify({"scanned": True})
	return jsonify({"scanned": False})

@app.route('/rfid', methods=['POST'])
def rfid():
	global station_name, rfid
	data = request.get_json()
	if not data or 'station' not in data:
		return jsonify({"success": False, "message": "Invalid data"}), 400
	station_name = data['station']
	get_station(rfid)
	print(f"RFID scanned at station: {station_name}")
	connection = get_db_connection()
	cursor = connection.cursor()
	query = "SELECT Balance FROM Passenger WHERE RFIDNo = %s"
	cursor.execute(query, (rfid,))
	balance=cursor.fetchone()
	return jsonify({"success": True, "rfid": rfid, "balance" : balance})

def get_station_name():
	return station_name

def get_station(int_uid):
	global station_data
	if int_uid not in station_data:
		station_data[int_uid] = {"start": None, "end": None} 
	if station_data[int_uid]["start"] is None:
		station_data[int_uid]["start"] = get_station_name()
		print(f"Start station recorded: {station_data[int_uid]['start']}")
	else:
		station_data[int_uid]["end"] = get_station_name()
		print(f"End station recorded: {station_data[int_uid]['end']}")
		send_to_backend(int_uid, station_data[int_uid])
		del station_data[int_uid]  # Reset tracking for this RFID

def get_rfid():
	global rfid_scanned, station_data, rfid
	arduino_port = 'COM5'
	baud_rate = 9600
	flask_url = "http://127.0.0.1:5000/rfid"

	try:
		serial_port = serial.Serial(arduino_port, baud_rate, timeout=1)
		print("Connected to Arduino")
	except Exception as e:
		print(f"Error connecting to Arduino: {e}")
		exit()

	while True:
		try:
			if serial_port.in_waiting > 0:
				uid = serial_port.readline().decode('utf-8').strip()
				int_uid = int(uid, 16)
				print(f"Card UID: {int_uid}")
				rfid_scanned = True
				rfid = int_uid
				

		except KeyboardInterrupt:
			print("Exiting...")
			break
		except Exception as e:
			print(f"Error: {e}")

def send_to_backend(rfid, data):
    try:
        rfid = rfid
        startstation = data["start"]
        endstation = data["end"]
        connection = get_db_connection()
        if not rfid:
            return jsonify({'success': False, 'message': 'RFID number is required.'})
        cursor = connection.cursor()
        query = "SELECT RouteNo, Fare FROM FARE WHERE Station1 = %s AND Station2 = %s"
        cursor.execute(query, (startstation,endstation))
        result=cursor.fetchone()
        if result is not None:
            RouteNo, Fare = result  # Unpack values correctly
            query1 = "INSERT INTO TICKET(START_STOP, END_STOP, RFID_NO, ROUTENO, FARE) VALUES(%s, %s, %s, %s, %s)"
            cursor.execute(query1, (startstation, endstation, rfid, RouteNo, Fare))
            print("Ticket Generated Successfully!!")
            query1 = "UPDATE passenger SET Balance = Balance - %s WHERE RFIDNo = %s"
            cursor.execute(query1, (Fare, rfid))
            print("Balance Updated Successfully!!")
            connection.commit()
            cursor.close()
            connection.close()
        else:
            RouteNo, Fare = None, None
            print("ERRRRROORRRR")
    except Exception as e:
        print("Error:", e)
	
		
rfid_thread = threading.Thread(target=get_rfid, daemon=True)
rfid_thread.start()

if __name__ == '__main__':
    app.run(debug=False)
	#register()

