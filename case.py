class Case(object):
    def __init__(self, case_number, created_timestamp, last_updated_timestamp, status='', language='', channel='',
     agent_id='', priority='', escalation_code='', from_email='', external_id='', object_id='', cdc_customer_id='', 
     name='', email_subject='', operations_investigation='', mpc_decision = '', investigation_transfer_timestamp = '', 
     twilio_task_created='', twilio_task_sid='', twilio_task_status='', twilio_task_timestamp = ''):
        self.case_number = case_number
        self.created_timestamp = created_timestamp
        self.last_updated_timestamp = last_updated_timestamp
        self.status = status
        self.language = language
        self.channel = channel
        self.agent_id = agent_id
        self.priority = priority
        self.escalation_code = escalation_code
        self.from_email = from_email
        self.external_id = external_id
        self.object_id = object_id
        self.cdc_customer_id = cdc_customer_id
        self.name = name
        self.email_subject = email_subject
        self.operations_investigation = operations_investigation
        self.mpc_decision = mpc_decision
        self.investigation_transfer_timestamp = investigation_transfer_timestamp
        self.twilio_task_created = twilio_task_created
        self.twilio_task_sid = twilio_task_sid
        self.twilio_task_status = twilio_task_status
        self.twilio_task_timestamp = twilio_task_timestamp


    @staticmethod
    def from_dict(source):
        case = Case(source[u'case_number'], source[u'created_timestamp'], source[u'last_updated_timestamp'])
        
        if u'status' in source:
            case.status = source[u'status']

        if u'language' in source:
            case.language = source[u'language']
        
        if u'channel' in source:
            case.channel = source[u'channel']
        
        if u'agent_id' in source:
            case.agent_id = source[u'agent_id']
            
        if u'priority' in source:
            case.priority = source[u'priority']
            
        if u'escalation_code' in source:
            case.escalation_code = source[u'escalation_code']
            
        if u'from_email' in source:
            case.from_email = source[u'from_email']

        if u'external_id' in source:
            case.external_id = source[u'external_id']
            
        if u'object_id' in source:
            case.object_id = source[u'object_id']
            
        if u'cdc_customer_id' in source:
            case.cdc_customer_id = source[u'cdc_customer_id']
            
        if u'name' in source:
            case.name = source[u'name']
            
        if u'email_subject' in source:
            case.email_subject = source[u'email_subject']

        if u'operations_investigation' in source:
            case.operations_investigation = source['operations_investigation']

        if u'mpc_decision' in source:
            case.mpc_decision = source['mpc_decision']

        if u'investigation_transfer_timestamp' in source:
            case.investigation_transfer_timestamp = source['investigation_transfer_timestamp']
            
        if u'twilio_task_created' in source:
            case.twilio_task_created = source['twilio_task_created']

        if u'twilio_task_sid' in source:
            case.twilio_task_sid = source['twilio_task_sid']
        
        if u'twilio_task_status' in source:
            case.twilio_task_status = source['twilio_task_status']

        if u'twilio_task_timestamp' in source:
            case.twilio_task_timestamp = source['twilio_task_timestamp']
        
        return case

    def to_dict(self):
        case = {
            u'case_number': self.case_number,
            u'created_timestamp': self.created_timestamp,
            u'last_updated_timestamp': self.last_updated_timestamp
        }

        if self.status:
            case[u'status'] = self.status
        
        if self.language:
            case[u'language'] = self.language
        
        if self.channel:
            case[u'channel'] = self.channel

        if self.agent_id:
            case[u'agent_id'] = self.agent_id

        if self.priority:
            case[u'priority'] = self.priority

        if self.escalation_code:
            case[u'escalation_code'] = self.escalation_code

        if self.from_email:
            case[u'from_email'] = self.from_email

        if self.external_id:
            case[u'external_id'] = self.external_id

        if self.object_id:
            case[u'object_id'] = self.object_id

        if self.cdc_customer_id:
            case[u'cdc_customer_id'] = self.cdc_customer_id

        if self.name:
            case[u'name'] = self.name

        if self.email_subject:
            case[u'email_subject'] = self.email_subject

        if self.operations_investigation:
            case[u'operations_investigation'] = self.operations_investigation

        if self.mpc_decision:
            case[u'mpc_decision'] = self.mpc_decision

        if self.investigation_transfer_timestamp:
            case[u'investigation_transfer_timestamp'] = self.investigation_transfer_timestamp
        
        if self.twilio_task_created:
            case[u'twilio_task_created'] = self.twilio_task_created

        if self.twilio_task_sid:
            case[u'twilio_task_sid'] = self.twilio_task_sid

        if self.twilio_task_status:
            case[u'twilio_task_status'] = self.twilio_task_status
        
        if self.twilio_task_timestamp:
            case[u'twilio_task_timestamp'] = self.twilio_task_timestamp

        return case

    def __repr__(self):
        return(
            f'Case(\
                case_number={self.case_number}, \
                created_timestamp={self.created_timestamp}, \
                last_updated_timestamp={self.last_updated_timestamp}, \
                status={self.status}, \
                language={self.language}, \
                channel={self.channel}, \
                agent_id={self.agent_id}, \
                priority={self.priority}, \
                escalation_code={self.escalation_code}, \
                from_email={self.from_email}, \
                external_id={self.external_id}, \
                object_id={self.object_id}, \
                cdc_customer_id={self.cdc_customer_id}, \
                name={self.name}, \
                email_subject={self.email_subject}, \
                operations_investigation={self.operations_investigation}, \
                mpc_decision={self.mpc_decision}, \
                investigation_transfer_timestamp={self.investigation_transfer_timestamp}, \
                twilio_task_created={self.twilio_task_created}, \
                twilio_task_sid={self.twilio_task_sid}, \
                twilio_task_status={self.twilio_task_status}, \
                twilio_task_timestamp={self.twilio_task_timestamp} \
                )'
        )