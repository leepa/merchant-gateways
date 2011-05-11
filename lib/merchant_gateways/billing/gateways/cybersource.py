from gateway import Gateway
from merchant_gateways.billing import response
from lxml import etree

from merchant_gateways.billing.common import xmltodict, dicttoxml, ET, XMLDict

class Cybersource(Gateway):
    namespace = 'urn:schemas-cybersource-com:transaction-data-1.59'
    TEST_URL = 'https://ics2wstest.ic3.com/commerce/1.x/transactionProcessor'
    LIVE_URL = 'https://ics2ws.ic3.com/commerce/1.x/transactionProcessor'
    CREDIT_CARD_CODES = {'visa': '001',
                         'master': '002',
                         'american_express': '003',
                         'discover': '004',}
    
    def __init__(self, merchant_id, api_key, **options):
        self.merchant_id = merchant_id
        self.api_key = api_key
        super(Cybersource, self).__init__(**options)

    def authorize(self, money, credit_card, **options):
        message = self.build_authorization_request(money, credit_card, **options)
        return self.commit(message)
    
    def purchase(self, money, credit_card=None, card_store_id=None, **options):
        if card_store_id:
            assert False, 'TODO'
        else:
            message = self.build_authorization_request(money, credit_card, **options)
        return self.commit(message)
    
    def void(self, authorization, **options):
        self.request = self.build_reversal_request(authorization, **options)
        return self.commit(self.request)
    
    def credit(self, money, authorization, **options):
        request = self.build_credit_request(money, authorization, **options)
        return self.commit(request)
    
    def capture(self, money, authorization, **options):
        request = self.build_capture_request(money, authorization, **options)
        return self.commit(request)
    
    def parse_tokens(self, authorization):
        if ';' in authorization:
            request_token, request_id = authorization.split(';')[:2]
        else:
            request_token, request_id = authorization, authorization
        return {'request_token':request_token,
                'request_id':request_id,}
    
    def get_cybersource_card_type(self, credit_card):
        return self.CREDIT_CARD_CODES.get(credit_card.card_type, '005') #TODO is this accurate?
    
    def get_merchant_reference_code(self, options):
        return options.get('order_id', 'foo')
    
    def build_bill_to(self, credit_card, address):
        return XMLDict([('firstName', credit_card.first_name),
                        ('lastName', credit_card.last_name),
                        ('street1', address['address1']),
                        ('street2', address.get('address2','')),
                        ('city', address['city']),
                        ('state', address['state']),
                        ('postalCode', address['zip']),
                        ('country', address['country']),
                        ('phoneNumber', address.get('phone')),
                        ('email', address.get('email', 'none@none.com')), #TODO test server complains if there is no email
                        ])
    
    def build_card(self, credit_card):
        return XMLDict([('accountNumber', credit_card.number),
                        ('expirationMonth', credit_card.month),
                        ('expirationYear', credit_card.year),
                        ('cvNumber', credit_card.verification_value),
                        ('cardType', self.get_cybersource_card_type(credit_card)),
                       ])

    def build_authorization_request(self, money, credit_card, **options):
        entries = XMLDict([('merchantID', self.merchant_id),
                           ('merchantReferenceCode', self.get_merchant_reference_code(options)),])
        if 'address' in options:
            entries['billTo'] = self.build_bill_to(credit_card, options['address'])
        entries['purchaseTotals'] = XMLDict([('currency', money.currency),
                                             ('grandTotalAmount', money.amount),])
        entries['card'] = self.build_card(credit_card)
        entries['ccAuthService'] = XMLDict(attrib={'run':'true'})
        return self.build_soap(entries)
    
    def build_capture_request(self, money, authorization, **options):
        entries = XMLDict([('merchantID', self.merchant_id),
                           ('merchantReferenceCode', self.get_merchant_reference_code(options)),])
        entries['purchaseTotals'] = XMLDict([('currency', money.currency),
                                             ('grandTotalAmount', money.amount),])
        tokens = self.parse_tokens(authorization)
        entries['orderRequestToken'] = tokens['request_token']
        entries['ccCaptureService'] = XMLDict([('authRequestID', tokens['request_id'])], 
                                              attrib={'run':'true'})
        return self.build_soap(entries)
    
    def build_purchase_request(self, money, credit_card, **options):
        entries = XMLDict([('merchantID', self.merchant_id),
                           ('merchantReferenceCode', self.get_merchant_reference_code(options)),])
        if 'address' in options:
            entries['billTo'] = self.build_bill_to(credit_card, options['address'])
        entries['purchaseTotals'] = XMLDict([('currency', money.currency),
                                             ('grandTotalAmount', money.amount),])
        entries['card'] = self.build_card(credit_card)
        entries['ccAuthService'] = XMLDict(attrib={'run':'true'})
        entries['ccCaptureService'] = XMLDict(attrib={'run':'true'})
        return self.build_soap(entries)
    
    def build_reversal_request(self, authorization, **options):
        entries = XMLDict([('merchantID', self.merchant_id),
                           ('merchantReferenceCode', self.get_merchant_reference_code(options)),])
        #TODO do we need money?
        if 'money' in options:
            entries['purchaseTotals'] = XMLDict([('currency', options['money'].currency),
                                                 ('grandTotalAmount', options['money'].amount),])
        else:
            entries['purchaseTotals'] = XMLDict([('currency', 'USD'),
                                                 ('grandTotalAmount', 100),])
        tokens = self.parse_tokens(authorization)
        entries['orderRequestToken'] = tokens['request_token']
        entries['ccAuthReversalService'] = XMLDict([('authRequestID', tokens['request_id'])], 
                                              attrib={'run':'true'})
        return self.build_soap(entries)
    
    def build_credit_request(self, money, authorization, **options):
        entries = XMLDict([('merchantID', self.merchant_id),
                           ('merchantReferenceCode', self.get_merchant_reference_code(options)),])
        if 'address' in options and 'credit_card' in options:
            entries['billTo'] = self.build_bill_to(options['credit_card'], options['address'])
        entries['purchaseTotals'] = XMLDict([('currency', money.currency),
                                             ('grandTotalAmount', money.amount),])
        if 'credit_card' in options:
            entries['card'] = self.build_card(options['credit_card'])
        tokens = self.parse_tokens(authorization)
        entries['orderRequestToken'] = tokens['request_token']
        entries['ccCreditService'] = XMLDict([('captureRequestID', tokens['request_id'])], 
                                             attrib={'run':'true'})
        return self.build_soap(entries)
    
    def build_soap(self, xml_dict):
        #TODO build this up properly
        soap_payload = '''<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
            <soapenv:Header>
                <wsse:Security soapenv:mustUnderstand="1" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
                    <wsse:UsernameToken>
                        <wsse:Username>%(merchant_id)s</wsse:Username>
                        <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">%(api_key)s</wsse:Password>
                    </wsse:UsernameToken>
                </wsse:Security>
            </soapenv:Header>
            <soapenv:Body>
            %(body)s
            </soapenv:Body>
        </soapenv:Envelope>
        '''
        root = ET.Element('requestMessage')
        root.attrib['xmlns'] = self.namespace
        dicttoxml(xml_dict, root)
        body = ET.tostring(root)
        return soap_payload % {'merchant_id': self.merchant_id,
                               'api_key': self.api_key,
                               'body': body,}

    def parse(self, response):
        print response
        doc  = etree.XML(response)
        result = xmltodict(doc, strip_namespaces=True)
        if 'Body' in result:
            result = result['Body']['replyMessage']
        return result

    class Response(response.Response):
        def lookup_reconciliation_id(self):
            for service, key in [('ccAuthReply', 'reconciliationID'),
                                 ('ccCaptureReply', 'reconciliationID'),
                                 ('ccCreditReply', 'reconciliationID'),]:
                if service in self.result:
                    return self.result[service][key]

    def commit(self, request, **options):
        url = self.is_test and self.TEST_URL or self.LIVE_URL

        result = self.parse(self.post_webservice(url, request, {}))
        
        if 'ccAuthReply' in result and 'authorizationCode' in result['ccAuthReply']:
            authorization = ';'.join([result['requestToken'], result['ccAuthReply']['authorizationCode']])
        else:
            authorization = result['requestToken']
        
        response = Cybersource.Response( success=result['decision'] == 'ACCEPT', 
                                         message='',
                                         result=result,
                                         is_test=self.is_test,
                                         authorization=authorization,
                                         transaction=authorization,)
        return response

