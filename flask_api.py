from flask import Flask
from flask import request, abort,jsonify
import sqlite3
import json
import configparser

config = configparser.ConfigParser()
config.read('config.txt')
lv_db_path = config.get('paths', 'db_path_o')
lv_db_name = config.get('db_names','db_name_a')
lv_db_full_path = lv_db_path + lv_db_name

app = Flask(__name__)

@app.route('/', methods=['POST'])
def index():  
	lv_payload  = request.get_json()
	lv_claim_no = lv_payload["claim_no"]
	print("Claim number for filtering the details table: ",lv_claim_no)
	print("Payload received: ",lv_payload)

	if not lv_payload or not 'claim_no' in lv_payload:
		abort(400)
	conn = sqlite3.connect(lv_db_full_path)
	conn.row_factory = sqlite3.Row
	cur = conn.cursor()
	cur.execute("SELECT * FROM claims_details WHERE claim_no=?", (lv_claim_no,))
	lv_claim_details = cur.fetchone()	

	ret_row_dict = {}
	if lv_claim_details: #len(lv_claim_details) > 0:
		ret_row_dict = {lv_claim_details.keys()[i]: lv_claim_details[i] for i in range(len(lv_claim_details))}

	return jsonify(ret_row_dict)

if __name__ == '__main__':


	app.run(debug=False)



