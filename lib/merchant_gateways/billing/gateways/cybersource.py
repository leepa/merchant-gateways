from gateway import Gateway
from merchant_gateways.billing import response
from lxml import etree

from merchant_gateways.billing.common import xmltodict, dicttoxml, ET, XMLDict

import urllib2

class Cybersource(Gateway):
    namespace = 'urn:schemas-cybersource-com:transaction-data-1.59'

    TEST_URL = 'https://ics2wstest.ic3.com/commerce/1.x/transactionProcessor'
    LIVE_URL = 'https://ics2ws.ic3.com/commerce/1.x/transactionProcessor'

    CREDIT_CARD_CODES = {'visa': '001',
                         'master': '002',
                         'american_express': '003',
                         'discover': '004',}

    RESPONSE_CODES = {'100' : "Successful transaction",
        '101' : "Request is missing one or more required fields" ,
        '102' : "One or more fields contains invalid data",
        '150' : "General failure",
        '151' : "The request was received but a server time-out occurred",
        '152' : "The request was received, but a service timed out",
        '200' : "The authorization request was approved by the issuing bank but declined by CyberSource because it did not pass the AVS check",
        '201' : "The issuing bank has questions about the request",
        '202' : "Expired card",
        '203' : "General decline of the card",
        '204' : "Insufficient funds in the account",
        '205' : "Stolen or lost card",
        '207' : "Issuing bank unavailable",
        '208' : "Inactive card or card not authorized for card-not-present transactions",
        '209' : "American Express Card Identifiction Digits (CID) did not match",
        '210' : "The card has reached the credit limit",
        '211' : "Invalid card verification number",
        '221' : "The customer matched an entry on the processor's negative file",
        '230' : "The authorization request was approved by the issuing bank but declined by CyberSource because it did not pass the card verification check",
        '231' : "Invalid account number",
        '232' : "The card type is not accepted by the payment processor",
        '233' : "General decline by the processor",
        '234' : "A problem exists with your CyberSource merchant configuration",
        '235' : "The requested amount exceeds the originally authorized amount",
        '236' : "Processor failure",
        '237' : "The authorization has already been reversed",
        '238' : "The authorization has already been captured",
        '239' : "The requested transaction amount must match the previous transaction amount",
        '240' : "The card type sent is invalid or does not correlate with the credit card number",
        '241' : "The request ID is invalid",
        '242' : "You requested a capture, but there is no corresponding, unused authorization record.",
        '243' : "The transaction has already been settled or reversed",
        '244' : "The bank account number failed the validation check",
        '246' : "The capture or credit is not voidable because the capture or credit information has already been submitted to your processor",
        '247' : "You requested a credit for a capture that was previously voided",
        '250' : "The request was received, but a time-out occurred with the payment processor",
        '254' : "Your CyberSource account is prohibited from processing stand-alone refunds",
        '255' : "Your CyberSource account is not configured to process the service in the country you specified", }

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
            request_id, request_token = authorization.split(';')[:2]
        else:
            request_id, request_token = authorization, authorization
        return {'request_token':request_token,
                'request_id':request_id,}

    def get_cybersource_card_type(self, credit_card):
        return self.CREDIT_CARD_CODES.get(credit_card.card_type, '005') #TODO is this accurate?

    def get_merchant_reference_code(self, options):
        return options.get('order_id', 'foo') #TODO should we raise en error instead?

    def build_bill_to(self, credit_card, address):

        if credit_card:
            first_name = credit_card.first_name
            last_name = credit_card.last_name
        else:
            first_name = address.get('first_name')
            last_name = address.get('last_name')

        return XMLDict([('firstName', first_name),
                        ('lastName', last_name),
                        ('street1', address['address1']),
                        ('street2', address.get('address2','')),
                        ('city', address['city']),
                        ('state', address['state']),
                        ('postalCode', address['zip']),
                        ('country', address['country']),
                        ('phoneNumber', address.get('phone')),
                        ('email', address.get('email', 'none@none.com')),  # TODO: test server complains if there is no email
                        ('ipAddress', address.get('ipaddress')),
                        ])

    def build_card(self, credit_card):
        return XMLDict([('accountNumber', credit_card.number),
                        ('expirationMonth', credit_card.month),
                        ('expirationYear', credit_card.year),
                        ('cvNumber', credit_card.verification_value),
                        # ('cardType', self.get_cybersource_card_type(credit_card)),
                        # TODO - fix the value we get from the get_cybersource_card_type call - it is always returing '005', which is "Diner's Club."
                        # I am commenting it out for now, because it's optional for all card types; except for JCB, which we don't accept.
                       ])

    def build_business_rules(self, options):
        parts = list()
        def check_options(key):
            if options.get(key, False):
                parts.append((key, options[key]))

        for option in ['ignoreAVSResult', 'ignoreCVResult', 'ignoreDAVResult', 'ignoreExportResult', 'ignoreValidateResult', 'declineAVSFlags', 'scoreThreshold']:
            check_options(option)
        if parts:
            return XMLDict(parts)

    def build_grand_total(self, money):
        return XMLDict([('currency', money.currency.code),
                        ('grandTotalAmount', money.amount)])

    def build_afs_request(self, money, credit_card, **options):
        """
        Build an AFS only request. This deals directly with only
        the anti-fraud system rather than the full auth. process
        """
        entries = XMLDict([('merchantID', self.merchant_id),
                           ('merchantReferenceCode',
                               self.get_merchant_reference_code(options))])

        if 'address' in options:
            entries['billTo'] = self.build_bill_to(credit_card,
                    options['address'])

        if 'basket_items' in options and len(options['basket_items']):
            for item in options['basket_items']:
                entry = XMLDict({'unitPrice': str(item['amount']),
                                 'quantity': str(item['quantity'])},
                    attrib={'id': str(item['id'])})
                entry['productName'] = item['description']
                entry['totalAmount'] = str(item['totalAmount'])
                entries.appendlist('item', entry)
        else:
            entries['item'] = XMLDict({'unitPrice': str(money.amount),
                'quantity': 1},
                attrib={'id': '0'})
            entries['item']['productName'] = options.get('description', '')
            entries['item']['totalAmount'] = str(money.amount)

        entries['purchaseTotals'] = self.build_grand_total(money)
        entries['fundingTotals'] = self.build_grand_total(money)

        if credit_card:
            entries['card'] = self.build_card(credit_card)

        # merchantDefinedData is a [] and should be in the order you
        # want it sorted in the field0-20. If it's longer than 20,
        # CyberSource will probably reject it.
        if options.get('merchantDefinedData'):
            entries['merchantDefinedData'] = XMLDict()
            field = 1
            for v in options['merchantDefinedData']:
                entries['merchantDefinedData']['field%d' % field] = v
                field += 1

        entries['afsService'] = XMLDict(attrib={'run': 'true'})
        business_rules = self.build_business_rules(options)
        if business_rules:
            entries['businessRules'] = business_rules

        # Used for device fingerprinting - you should read the
        # documentation about what to put here. It's under NDA.
        if options.get('session_id'):
            entries['deviceFingerprintID'] = options['session_id']

        return self.build_soap(entries)

    def build_authorization_request(self, money, credit_card, **options):
        entries = XMLDict([('merchantID', self.merchant_id),
                           ('merchantReferenceCode', self.get_merchant_reference_code(options)),])
        if 'address' in options:
            entries['billTo'] = self.build_bill_to(credit_card, options['address'])
        entries['purchaseTotals'] = self.build_grand_total(money)
        entries['card'] = self.build_card(credit_card)
        entries['ccAuthService'] = XMLDict(attrib={'run':'true'})
        business_rules = self.build_business_rules(options)
        if business_rules:
            entries['businessRules'] = business_rules
        return self.build_soap(entries)

    def build_capture_request(self, money, authorization, **options):
        entries = XMLDict([('merchantID', self.merchant_id),
                           ('merchantReferenceCode', self.get_merchant_reference_code(options)),])
        entries['purchaseTotals'] = self.build_grand_total(money)
        tokens = self.parse_tokens(authorization)
        entries['orderRequestToken'] = tokens['request_token']
        entries['ccCaptureService'] = XMLDict([('authRequestID', tokens['request_id'])],
                                              attrib={'run':'true'})
        business_rules = self.build_business_rules(options)
        if business_rules:
            entries['businessRules'] = business_rules
        return self.build_soap(entries)

    def build_purchase_request(self, money, credit_card, **options):
        entries = XMLDict([('merchantID', self.merchant_id),
                           ('merchantReferenceCode', self.get_merchant_reference_code(options)),])
        if 'address' in options:
            entries['billTo'] = self.build_bill_to(credit_card, options['address'])
        entries['purchaseTotals'] = self.build_grand_total(money)
        entries['card'] = self.build_card(credit_card)
        entries['ccAuthService'] = XMLDict(attrib={'run':'true'})
        entries['ccCaptureService'] = XMLDict(attrib={'run':'true'})
        business_rules = self.build_business_rules(options)
        if business_rules:
            entries['businessRules'] = business_rules
        return self.build_soap(entries)

    def build_reversal_request(self, authorization, **options):
        entries = XMLDict([('merchantID', self.merchant_id),
                           ('merchantReferenceCode', self.get_merchant_reference_code(options)),])
        #TODO do we need money?
        if 'money' in options:
            entries['purchaseTotals'] = self.build_grand_total(options['money'])
        else:
            entries['purchaseTotals'] = XMLDict([('currency', 'USD'),
                                                 ('grandTotalAmount', 100),])
        tokens = self.parse_tokens(authorization)
        entries['orderRequestToken'] = tokens['request_token']
        entries['ccAuthReversalService'] = XMLDict([('authRequestID', tokens['request_id'])],
                                              attrib={'run':'true'})
        business_rules = self.build_business_rules(options)
        if business_rules:
            entries['businessRules'] = business_rules
        return self.build_soap(entries)

    def build_credit_request(self, money, authorization, **options):
        entries = XMLDict([('merchantID', self.merchant_id),
                           ('merchantReferenceCode', self.get_merchant_reference_code(options)),])
        if 'address' in options and 'credit_card' in options:
            entries['billTo'] = self.build_bill_to(options['credit_card'], options['address'])
        entries['purchaseTotals'] = self.build_grand_total(money)
        if 'credit_card' in options:
            entries['card'] = self.build_card(options['credit_card'])
        tokens = self.parse_tokens(authorization)
        entries['orderRequestToken'] = tokens['request_token']
        entries['ccCreditService'] = XMLDict([('captureRequestID', tokens['request_id'])],
                                             attrib={'run':'true'})
        business_rules = self.build_business_rules(options)
        if business_rules:
            entries['businessRules'] = business_rules
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

        try:
            result = self.parse(self.post_webservice(url, request, {}))

            authorization = ';'.join([result['requestID'], result['requestToken']])

            message = self.RESPONSE_CODES.get(result['reasonCode'], 'Response code: %s' % result['reasonCode'])

            response = Cybersource.Response( success=result['decision'] == 'ACCEPT',
                                             message=message,
                                             result=result,
                                             is_test=self.is_test,
                                             authorization=authorization,
                                             transaction=authorization,)
            return response
        except urllib2.HTTPError, error:
            print error.read()

        return None
