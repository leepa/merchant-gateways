
class Gateway(object):
    DEBIT_CARDS = ('switch', 'solo')
    money_format = 'dollars'
    supported_cardtypes = []
    options = {}

    def __init__(self, **options):
        self.gateway_mode = options.get('gateway_mode', 'live')
        self.is_test = options.get('is_test', False)
        self.options = options

    def supports(self, card_type):
        return (card_type in self.supported_cardtypes)

    def card_brand(self, source):
        try:
            result = source.brand
        except AttributeError:
            result = type(source)
        return str(result).lower()

#    def is_test(self):
 #       return self.gateway_mode == 'test'  TODO  also permit toast-tests

    def is_blank(self, val):
        if type(val) != type(''):
            return None
        return len(val.strip()) == 0

    def amount(self, money):
        if money is None:
            return None
        try:
            cents = money.cents
        except AttributeError:
            cents = money

        if type(money) == '' or int(cents) < 0:
            raise TypeError, 'money amount must be either a Money ojbect or a positive integer in cents.'

        if self.money_format == 'cents':
            return str(cents)
        return ("%.2f" % (float(cents) / 100))

    def currency(money):
        try:
            return money.currency
        except AttributeError:
            return self.default_currency

    def requires_start_data_or_issue_number(credit_card):
        if self.card_brand(credit_card).strip() == '':
            return False
        if card_brand(credit_card) in self.DEBIT_CARDS:
            return True
        return False

    def authorize(self, money, creditcard, **kwargs):
        raise NotImplementedError

    def purchase(self, money, creditcard, **kwargs):
        raise NotImplementedError

    def capture(self, money, authorization, **kwargs):
        raise NotImplementedError

    def void(self, identification, **kwargs):
        raise NotImplementedError

    def credit(self, money, identification, **kwargs):
        raise NotImplementedError

    def recurring(self, money, creditcard, **kwargs):
        raise NotImplementedError

    def store(self, creditcard, **kwargs):
        raise NotImplementedError

    def unstore(self, indentification, **kwargs):
        raise NotImplementedError

    def require(self, kwargs_hash, *args):
        for arg in args:
            if not kwargs_hash.has_key(arg):
                raise ValueError('%s missing in gateway parameters' % arg)

    def setup_address_hash(self, **options):
        'Create all address hash key value pairs so that we still function if we were only provided with one or two of them'
        
        self.options = options # or self.options
        options['billing_address'] = options.get('billing_address', options.get('address', {}))
        options['shipping_address'] = options.get('shipping_address', {})
        return self.options  #  TODO options, results, message, param, etc ALL ARE ALWAYS MEMBERS

class default_dict(dict):  #  TODO  propagate me
    """
    A subclass of dictionary that returns '' instead of feebly
    attempting to spank the programmer if (shocked gasp) the key is not found
    """
    def __getitem__(self, key):  #  TODO  validate at a different layer!
        return self.get(key, '')