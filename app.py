# doing necessary imports
from flask import Flask, render_template, request, jsonify, make_response
# from flask_cors import CORS, cross_origin
import requests
import pymongo
import json
import os
import Conversations
import uuid
from pymongo import MongoClient
from google.oauth2 import service_account

app = Flask(__name__)  # initialising the flask app with the name 'app'

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\dhara\OneDrive\Documents\PJT FINAL\PJT FINAL\aimedicalreceptionist-aymp-98eb4c06c7f5.json"

# geting and sending response to dialogflow
@app.route('/webhook', methods=['POST'])
# @cross_origin()
def webhook():
    req = request.get_json(silent=True, force=True)
    res = processRequest(req)
    res = json.dumps(res, indent=4)
    print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get("message")

    if not user_message:
        return jsonify({"error": "No message provided"}), 400
 
    session_id = str(uuid.uuid4())  # Generates a unique session ID

    # Send user message to Dialogflow
    dialogflow_url = f"https://dialogflow.googleapis.com/v2/projects/aimedicalreceptionist-aymp/agent/sessions/{session_id}:detectIntent"
    headers = {
        "Authorization": f"Bearer {os.getenv('DIALOGFLOW_ACCESS_TOKEN')}",
        "Content-Type": "application/json",
    }
    dialogflow_payload = {
        "queryInput": {
            "text": {
                "text": user_message,
                "languageCode": "en"
            }
        }
    }

    response = requests.post(dialogflow_url, headers=headers, json=dialogflow_payload)
    dialogflow_response = response.json()

    bot_reply = dialogflow_response.get("queryResult", {}).get("fulfillmentText", "Sorry, I didn't understand that.")

    return jsonify({"response": bot_reply})

# processing the request from dialogflow
def processRequest(req):
    # dbConn = pymongo.MongoClient("mongodb://localhost:27017/")  # opening a connection to Mongo
    log = Conversations.Log()
    sessionID = req.get('responseId')
    result = req.get("queryResult")
    intent = result.get("intent").get('displayName')
    query_text = result.get("queryText")
    parameters = result.get("parameters")
    doctor_name = parameters.get("Doctor_Name")
    time_slot = parameters.get("Timeslot")
    db = configureDataBase()
    
    # 🔹 Extract session_id from outputContexts
    session_path = None
    output_contexts = result.get("outputContexts", [])
    
    if output_contexts:
        for context in output_contexts:
            if "sessions/" in context["name"]:  # Look for session in name
                session_path = context["name"]
                break  # Stop at first found session

    # If session is still missing, return error message
    if not session_path:
        print(" Warning: 'session' field is missing in Dialogflow request.")
        return {
            "fulfillmentMessages": [
                {
                    "text": {
                        "text": [
                            "Error: Missing session information in request."
                        ]
                    }
                }
            ]
        }

    # Extract session_id and project_id
    session_id = session_path.split("/sessions/")[-1].split("/")[0]  # Extract session ID
    project_id = session_path.split("/")[1]   # Extract project ID

    print(f"✅ Extracted session_id: {session_id}, project_id: {project_id}")

    # Continue with intent processing...
    if intent == "PatientDetails":
        
        patient_name = parameters.get("patient_name")
        patient_age = parameters.get("patient_age")
        patient_contact = parameters.get("patient_contact")


        
        # Store patient details in separate collection
        appointment_data = {
           
            "patient_details": {
                "name": patient_name,
                "age": patient_age,
                "contact": patient_contact
            },
            "status": "Confirmed"
        }
        db.Patientdetails.insert_one(appointment_data)
    
        webhookresponse = f"Thank you {patient_name}, your appointment with {doctor_name}  at {time_slot} has been confirmed!"
    
        return {"fulfillmentMessages": [{"text": {"text": [webhookresponse]}}]}

    
    if intent == "AppointmentBooking":
        doctor_name = parameters.get("Doctor_Name", "")
        appointment_date = parameters.get("Date", "")
        time_slot = parameters.get("Timeslot", "")

        # Check slot availability in MongoDB
        doctor = db.Booking_status.find_one({"doctor_name": doctor_name})

        if doctor:
            slot_found = False
            for slot in doctor["time_slots"]:
                if slot["time"] == time_slot and slot["flag"]:
                    slot_found = True
                    break

            if slot_found:
                db.Booking_status.update_one(
                    {"doctor_name": doctor_name, "time_slots.time": time_slot},
                    {"$set": {"time_slots.$.flag": False}}
                )
                webhookresponse = f"The slot with {doctor_name} on {appointment_date} at {time_slot} is available. Please provide your details to book the appointment in the following: ""The details are $name, $age, $contact"" "

                return {
                    
                    "fulfillmentMessages": [{"text": {"text": [webhookresponse]}}],
                    
                    
                }
            else:
                return {"fulfillmentMessages": [{"text": {"text": [f"Sorry, the slot at {[time_slot]} is already booked."]}}]}

    return {"fulfillmentMessages": [{"text": {"text": ["Something went wrong."]}}]}


    # if intent == "AppointmentBooking":
    #     # Find the document for the specified doctor
    #     doctor = db.Booking_status.find_one({"doctor_name": doctor_name})

    #     if doctor:
    #         # Check the time_slots array for the specified time
    #         slot_found = False
    #         for slot in doctor["time_slots"]:
    #             if slot["time"] == time_slot:
    #                 slot_found = True
    #                 if slot["flag"]:  # Slot is available
    #                     # Update the flag to false (book the slot)
    #                     db.Booking_status.update_one(
    #                         {"doctor_name": doctor_name, "time_slots.time": time_slot},
    #                         {"$set": {"time_slots.$.flag": False}}
    #                     )
    #                     webhookresponse = f"The appointment has been successfully booked with {doctor_name} at {time_slot}."
    #                 else:  # Slot is already booked
    #                     webhookresponse = f"Sorry, the slot at {time_slot} for {doctor_name} is already booked."
    #                 break
    #         if not slot_found:
    #             webhookresponse = f"No slot found at {time_slot} for {doctor_name}."
    #     else:
    #         webhookresponse = f"Doctor {doctor_name} is not available in the system."

    #     # Log the conversation
    #     fulfillmentText = webhookresponse
    #     log.saveConversations(sessionID, query_text, fulfillmentText, intent, db)

    #     return {
    #         "fulfillmentMessages": [
    #             {
    #                 "text": {
    #                     "text": [
    #                         webhookresponse
    #                     ]
    #                 }
    #             }
    #         ]
    #     }
    
    if intent == "EmergencyResponse":
        patient_condition = parameters.get("Condition")
        location = parameters.get("Location")
        phone_number = parameters.get("Phonenumber")

        # Store data in MongoDB
        emergency_data = {
            "patient_condition": patient_condition,
            "location": location,
            "phone_number": phone_number
        }
        db.Emergency_records.insert_one(emergency_data)

        webhookresponse = "Emergency details saved. Help is on the way!"

        # Log the conversation
        fulfillmentText = webhookresponse
        log.saveConversations(sessionID, query_text, fulfillmentText, intent, db)

        return {
            "fulfillmentMessages": [
                {
                    "text": {
                        "text": [
                            webhookresponse
                        ]
                    }
                }
            ]
        }

   

    
    


        
               
    
    
        
    

    

            
           

            



        
                 
                    


    


def configureDataBase():
    client = MongoClient("mongodb+srv://Dharani:pjt25@cluster0.qql63.mongodb.net/test?retryWrites=true&w=majority")
    return client.get_database('Appointment_booking')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
