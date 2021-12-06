from google.cloud import secretmanager
import base64
import json
import sys
import yaml
import os
import logging
import requests
from pytz import timezone
import pytz
import uuid
from datetime import date, datetime, timedelta
from case import Case
import firestore_functions

workspace_sid = os.environ['WORKSPACE_SID']
twilio_task_api_url_base = os.environ['TWILIO_API_URL_BASE']
task_channel = os.environ['TASK_CHANNEL']
project_id = os.environ['PROJECT']
report_api_url = os.environ['REPORT_API_URL']
environment = os.environ['ENVIRONMENT']
mpc_wait_time = os.environ['MPC_WAIT_TIME']
correlation_id = str(uuid.uuid1())
global twilio_task_created

def pubsub_to_caseMessage(event, context):
    '''
      This is the function's entry point, the pubsub message is decoded and loaded in as json.
    '''
    pubsub_message = base64.b64decode(event['data']).decode('utf-8')
    logging.info(correlation_id + " - Loading inbound message as json")
    pubsub_message = json.loads(pubsub_message)
    print(pubsub_message)

    global config_dict
    global twilio_task_created
    twilio_task_created = False

    #Reading property variables from config.yaml file
    stream = open("config.yaml", 'r')    
    config_dict = yaml.safe_load(stream)

    #Initiatize firebase app
    db = firestore_functions.init(project_id, correlation_id)
    sc_case_message = ''
    twilio_response = ''
    existing_case = ''

    if 'ServiceRequestCollection' in pubsub_message:
        sc_case_message = pubsub_message['ServiceRequestCollection']['ServiceRequest']
        case_number = sc_case_message['ID']
        case_status = sc_case_message['ServiceRequestUserLifeCycleStatusCode']
        
        if case_status != 'Y7' and case_status != '6':
            #Case status is not resolved or closed
            existing_case = firestore_functions.search_case(db, case_number, correlation_id) #Search if the case is present in Firestore
            request_body = {}
            #employee_id = ''
            attributes = create_attributes(sc_case_message)

            '''
            if sc_case_message['ProcessorPartyID'] != "":
                #If Processor Party ID is present in the payload, query the corresponding employee ID
                employee_id = get_employeeId(sc_case_message['ProcessorPartyID'])
                attributes['agent_ID'] = employee_id
            '''
            
            if create_task(sc_case_message, existing_case):     

                #ExternalID needs to be generated only when conditions satisfy for creating new task in Twilio
                external_id = uuid.uuid4().hex.upper()
                attributes['externalID'] = external_id
                request_body = create_request(attributes)
                response = post_twilio_task(request_body)
                twilio_response = response.json()
                if response.reason != "Created":
                    logging.error(correlation_id + "Error creating task in twilio: " + twilio_response)

            #Add the case to Firestore. In case of existing documents, the last updated timestamp and status will be updated based on document ID
            firestore_doc = firestore_functions.create_firestore_document(attributes, sc_case_message, twilio_task_created, existing_case, twilio_response)
            firestore_functions.add_case(db, firestore_doc, correlation_id)
        else:
            #If case is resolved/closed, case document should be deleted from Firestore
            firestore_functions.delete_case(db, case_number, correlation_id)
    else:
        logging.error(correlation_id + "Error creating task for case: " + pubsub_message)
            
    #Gracefully deletes the firestore app
    firestore_functions.delete()

def getPropertyValue(key):
    property_dict = config_dict.get(environment)
    if key in property_dict:
        return property_dict.get(key)

def getCredentials(secret_name):
    #Get API credentials from Secret Manager
    client = secretmanager.SecretManagerServiceClient()    
    request = {"name": f"projects/{project_id}/secrets/{secret_name}/versions/latest"}
    response = client.access_secret_version(request)
    secret_string = response.payload.data.decode("UTF-8")
    return secret_string

def update_twilio_task_created(value):
    global twilio_task_created
    twilio_task_created = value

def typecode_map(key):
    #Mapping service cloud case type code to twilio description
    typecode_dict = {}
    typecode_dict["39"] = "E-mail"
    typecode_dict["86"] = "Phone"
    typecode_dict["1976"] = "Chat"
    typecode_dict["2574"] = "Memo"
    if key in typecode_dict:
        return typecode_dict.get(key)

def status_map(key):
    #Mapping service cloud status code to twilio description
    status_dict = {}
    status_dict["6"] = "Closed"
    status_dict["Y2"] = "New"
    status_dict["Y3"] = "Awaiting Action"
    status_dict["Y4"] = "Working on It"
    status_dict["Y5"] = "Waiting for Customer"
    status_dict["Y6"] = "Waiting for Department"
    status_dict["Y7"] = "Resolved"
    if key in status_dict:
        return status_dict.get(key)

def language_map(key):
    #Mapping service cloud language code to twilio description
    language_dict = {}
    language_dict["101"] = "English"
    language_dict["111"] = "French"
    if key in language_dict:
        return language_dict.get(key)

def operations_map(key):
    #Mappings for the team which needs to investigate the case
    operations_dict = {}
    operations_dict["101"] = "Transfer to MPC Specialist"
    operations_dict["111"] = "Transfer to ERM"
    operations_dict["121"] = "ERM COA Decided"
    if key in operations_dict:
        return operations_dict.get(key)

def mpc_decision_map(key):
    #Mapping for MPC Decision by Risk
    mpc_decision_dict = {}
    mpc_decision_dict["101"] = "Claim Accepted"
    mpc_decision_dict["111"] = "Claim Denied"
    if key in mpc_decision_dict:
        return mpc_decision_dict.get(key)

def channel_map(key):
    #Mapping service cloud channel codes to twilio description
    channel_dict = {}
    channel_dict["1"] = "Manual Data Entry"
    channel_dict["5"] = "Email"
    channel_dict["7"] = "Chat"
    channel_dict["8"] = "Telephony"
    if key in channel_dict:
        return channel_dict.get(key)

def create_task(message, case):
    #Check if conditions are valid to create a new task in Twilio
    case_language = ''
    case_status = ''
    investigation_transfer_timestamp = ''
    global queue_details_dict

    if case is not None:
        if hasattr(case, 'language'):
            case_language = case.language
        if hasattr(case, 'status'):
            case_status = case.status
        investigation_transfer_timestamp = case.investigation_transfer_timestamp
        twilio_task_flag = case.twilio_task_created #Check the last status of twilio task created flag
    '''
    else:
        #This is needed if a case is reopened after resolved, case is deleted from Firestore 
        #created_timestamp needs to be read from the message and converted from string to datetime for comparison
        created_date_str = message['CreationDateTime'] if 'CreationDateTime' in message else None
        investigation_transfer_timestamp = convertStringToTimestamp(created_date_str) #Need to update this logic later
    '''
    request_status = status_map(message['ServiceRequestUserLifeCycleStatusCode']) if 'ServiceRequestUserLifeCycleStatusCode' in message else None
    request_language = language_map(message['CaseLanguage_KUT']) if 'CaseLanguage_KUT' in message else None
    channel = message['DataOriginTypeCode'] if 'DataOriginTypeCode' in message else None
    escalation = message['EscalationStatusCode'] if 'EscalationStatusCode' in message else None
    investigation = message['Investigation_KUT'] if 'Investigation_KUT' in message else None   
    now = datetime.now(tz=pytz.utc)

    if escalation == '2':
        #Case escalated, should not create new task in Twilio, will go to escalation queue in SC
        return False

    if case_status == request_status and case_language == request_language:
        #If status and language remains unchanged, and change in any other field is made in SC, new task should not be created in Twilio, 
        #The twilio task created flag should retain the existing value for such changes
        update_twilio_task_created(twilio_task_flag)
        return False

    if channel == '5' and request_status.lower() == 'new':
        update_twilio_task_created(True)
        #Email channel and a new case
        if not case:
            #Case not present in firestore, new document needs to be added to Firestore collection and new task created in Twilio
            queue_details_dict = getPropertyValue('email_queue_standard')
            return True
        elif case_status == request_status and case_language != request_language:  
            #Existing case in Firestore in status New
            #Compares if there is a change in language, new task created in twilio only when language is changed
            #Firestore document is updated with latest timestamp, status and/or language
            queue_details_dict = getPropertyValue('email_queue_standard')
            return True
        else:
            #Change in any other field of the case in service cloud other does not create new task in Twilio.
            return False

    elif request_status.lower() == 'awaiting action':
        update_twilio_task_created(True)
        #If status of the case is Awaiting Action
        if investigation == '101':
            #If case is transferred to concierge specialist
            queue_details_dict = getPropertyValue('operations_risk_priority')
            return True
        if investigation == '111':
            #If case is Transferred to Risk
            update_twilio_task_created(False)
            return False
        if investigation == '121':
            #If MPC Claim, COA decided
            if investigation_transfer_timestamp and investigation_transfer_timestamp is not None:
                #If investigation transfer timestamp is present
                if investigation_transfer_timestamp <= (now-timedelta(hours=int(mpc_wait_time))):
                    #If case transfer to risk is more than 48 hours, create the task in twilio immediately
                    #These will be excluded from the batch job
                    queue_details_dict = getPropertyValue('operations_risk_standard')
                    return True
                else:
                    #If not 48 hours from when case transferred to Risk, 
                    #don't create task in Twilio, task will be created by the scheduler
                    update_twilio_task_created(False)
                    return False
            else:
                #No investigation transfer timestamp, might be the case is reopen after resolved
                queue_details_dict = getPropertyValue('operations_risk_standard')
                return True
        else:
            queue_details_dict = getPropertyValue('email_queue_standard')
            return True


def convertStringToTimestamp(date_string):
    #Convert datetime string to aware date object
    try:
        #Converting reported date string to aware datetime object, needed to compare date in the scheduled job
        utc = pytz.timezone("UTC")
        naive_date_obj = datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S.%f')
        converted_timestamp_utc  = utc.localize(naive_date_obj)
        converted_timestamp_pst = converted_timestamp_utc.astimezone(timezone('US/Pacific'))
        return converted_timestamp_pst
    except ValueError as val:
        logging.warning("Error: {}".format(str(val)))


def get_employeeId(processor_party_ID):
    #Call the Report API to get the employee ID for corresponding Business Partner ID/ Processor party ID. 
    #The employee ID needs to be passed in the task attribute to create the Twilio Task.
    employee_id = ''
    payload = {}
    payload['$inlinecount'] = 'allpages'
    payload['$filter'] = "(CPARTY_IDENTF_TY eq 'HCM001') and (CBP_INT_ID eq '"+ processor_party_ID + "')"
    payload['$format'] = 'json'
    payload['$select'] = 'CEE_ID'

    headers = {"Content-Type":"application/json;charset=UTF-8","Accept":"application/json;charset=UTF-8"}

    secret_name = "report-api-secret"
    credential = getCredentials(secret_name)
    secret = credential.split(":")
    username = secret[0]
    password = secret[1]
    
    try:
        r = requests.get(url=report_api_url, auth=(username, password), timeout=10)
        cookies = r.cookies
        response = requests.get(url=report_api_url, auth=(username, password), headers=headers, params=payload, cookies=cookies, timeout=10)
        decoded_data=response.content.decode('utf-8-sig')
        data = json.loads(decoded_data)
        employee_id = data['d']['results'][0]['CEE_ID']        
        return employee_id
    except ValueError as val:
        logging.warning(correlation_id + " - Employee ID not present. Error: {}".format(str(val)))
    except Exception as e:
        logging.warning(correlation_id + " - Error getting Employee ID. Error: {}".format(str(e)))


def create_attributes(message):
    '''
        Creating the custom attributes field in the twilio task message payload
    '''
    
    attributes_dict = {}
    attributes_dict['channel_SID'] = task_channel
    attributes_dict['name'] = message['ReportedPartyName'] if 'ReportedPartyName' in message else None
    attributes_dict['ticket_ID'] = message['ID'] if 'ID' in message else None
    attributes_dict['case_status'] = status_map(message['ServiceRequestUserLifeCycleStatusCode']) if 'ServiceRequestUserLifeCycleStatusCode' in message else None
    if 'ServiceRequestInteractions' in message:
        interactions = len(message['ServiceRequestInteractions'])
        if interactions > 0:
            attributes_dict['from_email'] = message['ServiceRequestInteractions'][0]['ServiceRequestInteractionInteractions'][0]['FromEmailURI']
    email_subject = message['Name'] if 'Name' in message else None
    parsed_email_subject = email_subject.replace(' & ', ' and ')
    attributes_dict['email_subject'] = parsed_email_subject
    attributes_dict['reported_date'] = message['CreationDateTime'] if 'CreationDateTime' in message else None
    attributes_dict['language'] = language_map(message['CaseLanguage_KUT']) if 'CaseLanguage_KUT' in message else None
    attributes_dict['channel'] = channel_map(message['DataOriginTypeCode']) if 'DataOriginTypeCode' in message else None
    attributes_dict['cdc_customer_ID'] = message['CDCCustomerID_KUT'] if 'CDCCustomerID_KUT' in message else None
    attributes_dict['object_ID'] = message['ObjectID']
    attributes_dict['operations_investigation'] = message['Investigation_KUT'] if 'Investigation_KUT' in message else None
    attributes_dict['mpc_decision'] = mpc_decision_map(message['MPCDecision_KUT']) if 'MPCDecision_KUT' in message else None

    return attributes_dict

def create_request(attributes):
    request = {}
    request['Priority'] = queue_details_dict['priority']
    request['Timeout'] = getPropertyValue('timeout')
    request['TaskChannel'] = task_channel
    request['WorkflowSid'] = queue_details_dict['workflowSid']
    request['Attributes'] = json.dumps(attributes)
    return request


def post_twilio_task(data):
    '''
        Call Task Create Twilio API to create new tasks when conditions meet
    '''
    headers = {"Content-Type":"application/x-www-form-urlencoded; charset=utf-8", "Accept":"application/json;charset=utf-8"}    
    task_api_url = twilio_task_api_url_base + workspace_sid + "/Tasks"
    secret_name = "twilio-api-secret"
    credential = getCredentials(secret_name)
    secret = credential.split(":")
    username = secret[0]
    password = secret[1]
    try:
        response = requests.post(task_api_url, auth=(username, password), headers=headers, data=data, timeout=10)
        logging.info(correlation_id + " - Success posting create task message to Twilio. Response: " + response.reason)
    except Exception as e:
        logging.warning(correlation_id + " - Error creating task in Twilio: " + format(str(e)))
        return 'Error: {}'.format(str(e))
    return response