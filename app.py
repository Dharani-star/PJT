# doing necessary imports
from flask import Flask, render_template, request, jsonify, make_response
# from flask_cors import CORS, cross_origin
import requests
import pymongo
import json
import os
import Conversations
# from DataRequests import MakeApiRequests
# from sendEmail import EMailClient
from pymongo import MongoClient

app = Flask(__name__)  # initialising the flask app with the name 'app'


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


# processing the request from dialogflow
def processRequest(req):
    # dbConn = pymongo.MongoClient("mongodb://localhost:27017/")  # opening a connection to Mongo
    log = Conversations.Log()
    sessionID = req.get('responseId')
    result = req.get("queryResult")
    intent = result.get("intent").get('displayName')
    query_text = result.get("queryText")
    parameters = result.get("parameters")
    # cust_name = parameters.get("cust_name")
    # cust_contact = parameters.get("cust_contact")
    # cust_email = parameters.get("cust_email")
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
                webhookresponse = f"The slot with {doctor_name} on {appointment_date} at {time_slot} is available. Please provide your details to book the appointment."

                return {
                    # "outputContexts": [
                    #     {
                    #         "name": f"projects/{project_id}/agent/sessions/{session_id}/contexts/awaiting_patient_details",
                    #         "lifespanCount": 5
                    #     }
                    # ],
                    "fulfillmentMessages": [{"text": {"text": [webhookresponse]}}],
                    
                    # "followupEventInput": {
                    #     "name": "auto_respond_patient_details",  # Name of event in Dialogflow
                    #     "parameters": {
                    #         "Doctor_Name": doctor_name,
                    #         "Date": appointment_date,
                    #         "Timeslot": time_slot
                    #     },
                    #     "languageCode": "en"
                    # }
                }
            else:
                return {"fulfillmentMessages": [{"text": {"text": [f"Sorry, the slot at {time_slot} is already booked."]}}]}

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

   

    
    elif intent == "PatientDetails":
    # Extract patient details
        doctor_name = parameters.get("Doctor_Name")
        time_slot = parameters.get("Timeslot")
        #appointment_date = parameters.get("Date")
        patient_name = parameters.get("patient_name")
        patient_age = parameters.get("patient_age")
        patient_contact = parameters.get("patient_contact")
    
        # Store patient details in separate collection
        appointment_data = {
            "doctor_name": doctor_name,
            "appointment_time": time_slot,
            "patient_details": {
                "name": patient_name,
                "age": patient_age,
                "contact": patient_contact
            },
            "status": "Confirmed"
        }
        db.Patient_Appointments.insert_one(appointment_data)
    
        webhookresponse = f"Thank you {patient_name}, your appointment with {doctor_name}  at {time_slot} has been confirmed!"
    
        return {"fulfillmentMessages": [{"text": {"text": [webhookresponse]}}]}


        
               
    
    
        
    

    

            
           

            



        
                 
                    


    


def configureDataBase():
    client = MongoClient("mongodb+srv://Dharani:pjt25@cluster0.qql63.mongodb.net/test?retryWrites=true&w=majority")
    return client.get_database('Appointment_booking')


def makeAPIRequest(query):
    api = MakeApiRequests.Api()

    if query == "world":
        return api.makeApiWorldwide()
    if query == "state":
        return api.makeApiRequestForIndianStates()

    else:
        return api.makeApiRequestForCounrty(query)


def prepareEmail(contact_list):
    mailclient = EMailClient.GMailClient()
    mailclient.sendEmail(contact_list)


# if __name__ == '__main__':
#     port = int(os.getenv('PORT'))
#     print("Starting app on port %d" % port)
#     app.run(debug=False, port=port, host='0.0.0.0')
if __name__ == "__main__":
    # app.run(port=5000, debug=True) # running the app on the local machine on port 8000
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
