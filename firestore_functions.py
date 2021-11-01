import logging
from datetime import datetime
from case import Case
import pytz
import firebase_admin
import main
from pytz import timezone
from firebase_admin import credentials
from firebase_admin import firestore

#Function to initialize a Firestore app
def init(firestore_project, correlation_id):
  try:
      # Use the application default credentials
      cred = credentials.ApplicationDefault()
      firebase_admin.initialize_app(cred, {
        'projectId': firestore_project,
      })      
      db = firestore.client()
      return db
  except Exception as e:
      logging.error(correlation_id + " - Error initializing Firestore: " + format(str(e)))
      return 'Error: {}'.format(str(e))


#Function to gracefully delete the Firestore app
def delete():
  app = firebase_admin.get_app(name='[DEFAULT]')
  if app:
    firebase_admin.delete_app(app)


#Function to search for a firestore document against case number
def search_case(db, case_number, correlation_id):
    try:
        #Create a query against the collection
        doc_ref = db.collection(u'service-cloud-cases').document(case_number)
        doc = doc_ref.get()

        if doc.exists:
            case = Case.from_dict(doc.to_dict())
            return case
    except Exception as e:
        logging.error(correlation_id + " - Error searching case in Firestore: " + format(str(e)))
        return 'Error: {}'.format(str(e))


#Function to add a new firestore document or update existing document based on case number
def add_case(db, request, correlation_id):
    documentId = request.get('case_number', None)
    try:
        doc_ref = db.collection(u'service-cloud-cases').document(documentId)
        doc_ref.set({
            u'case_number': request.get('case_number'),
            u'created_timestamp': request.get('created_timestamp'),
            u'last_updated_timestamp': request.get('last_updated_timestamp'),
            u'status' : request.get('status'),
            u'language' : request.get('language'),
            u'channel' : request.get('channel'),
            u'agent_id' : request.get('agent_id'),
            u'priority' : request.get('priority'),
            u'escalation_code' : request.get('escalation_code'),
            u'from_email' : request.get('from_email'),
            u'external_id' : request.get('external_id'),
            u'object_id' : request.get('object_id'),
            u'cdc_customer_id' : request.get('cdc_customer_id'),
            u'name' : request.get('name'),
            u'email_subject' : request.get('email_subject'),
            u'operations_investigation' : request.get('operations_investigation'),
            u'mpc_decision' : request.get('mpc_decision'),
            u'investigation_transfer_timestamp' : request.get('investigation_transfer_timestamp'),
            u'twilio_task_created' : request.get('twilio_task_created'),
            u'twilio_task_sid' : request.get('twilio_task_sid'),
            u'twilio_task_status' : request.get('twilio_task_status'),
            u'twilio_task_timestamp' : request.get('twilio_task_timestamp')
        })
    except Exception as e:
        logging.error(correlation_id + " - Error adding case in Firestore: " + format(str(e)))
        return 'Error: {}'.format(str(e))


#Function to Delete Firestore Collection based on case number
def delete_case(db, case_number, correlation_id):
    try:
        db.collection(u'service-cloud-cases').document(case_number).delete()
    except Exception as e:
        logging.error(correlation_id + " - Error deleting case from Firestore: " + format(str(e)))
        return 'Error: {}'.format(str(e))

def create_firestore_document(attributes, case, task_created, existing_case, twilio_response):
    '''
        Creating fields for Firestore document for collection: service-cloud-cases
    '''
    document = {}
    create_date_str = attributes.get('reported_date')
    created_timestamp_pst = main.convertStringToTimestamp(create_date_str)
    
    document['case_number'] = attributes.get('ticket_ID')
    document['created_timestamp'] = created_timestamp_pst
    document['last_updated_timestamp'] = datetime.now()
    document['status'] = attributes.get('case_status')
    document['language'] = attributes.get('language')
    document['channel'] = attributes.get('channel')
    document['agent_id'] = attributes.get('agent_ID', None)
    document['priority'] = case['ServicePriorityCode'] if 'ServicePriorityCode' in case else None
    document['escalation_code'] = case.get('EscalationStatusCode', None)
    document['from_email'] = attributes.get('from_email')
    document['external_id'] = attributes.get('externalID')
    document['object_id'] = attributes.get('object_ID')
    document['cdc_customer_id'] = attributes.get('cdc_customer_ID')
    document['name'] = attributes.get('name', None)
    document['email_subject'] = attributes.get('email_subject')
    investigation_val = attributes.get('operations_investigation', None)
    document['operations_investigation'] = investigation_val
    mpc_decision = attributes.get('mpc_decision', None)
    document['mpc_decision'] = mpc_decision
    document['twilio_task_created'] = task_created
    if not twilio_response and existing_case is not None:
        if hasattr(existing_case, 'twilio_task_sid'):
            document['twilio_task_sid'] = existing_case.twilio_task_sid
        if hasattr(existing_case, 'twilio_task_status'):
            document['twilio_task_status'] = existing_case.twilio_task_status
        if hasattr(existing_case, 'twilio_task_timestamp'):
            document['twilio_task_timestamp'] = existing_case.twilio_task_timestamp
    else:
        document['twilio_task_sid'] = twilio_response.get('sid') if 'sid' in twilio_response else None
        document['twilio_task_status'] = twilio_response.get('assignment_status') if 'assignment_status' in twilio_response else None
        document['twilio_task_timestamp'] = datetime.now()
    
    if investigation_val == '111' and mpc_decision is None:
        #If the mpc_decision value is empty, i.e, mpc decision has not been given yet,
        #Record the timestamp of when the case is being transferred to Risk
        #If not empty, that means the case is getting transferred back to Risk more than once
        document['investigation_transfer_timestamp'] = datetime.now()
    elif existing_case is not None:
        if hasattr(existing_case, 'investigation_transfer_timestamp'):
            document['investigation_transfer_timestamp'] = existing_case.investigation_transfer_timestamp
            
    return document