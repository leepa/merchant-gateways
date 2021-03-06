from merchant_gateways.billing.gateways.payflow import Payflow
from merchant_gateways.tests.billing.gateways.payflow_suite import PayflowProMockServer
from merchant_gateways.tests.billing.gateways.gateway_suite import GatewayTestCase

from mock import Mock

class PayflowTests(GatewayTestCase):

    def get_gateway(self):
        return Payflow(**{'user':'username',
                          'password':'password',
                          'vendor':'VENDORID',
                          'partner':'PayPal',})

    def get_success_mock(self):
        return Mock(side_effect=PayflowProMockServer())

'''
class PayflowTest < Test::Unit::TestCase
  def setup
    Base.mode = :test

    @gateway = PayflowGateway.new( # TODO
      :login => 'LOGIN',
      :password => 'PASSWORD'
    )

    @amount = 100
    @credit_card = credit_card('4242424242424242')
    @options = { :billing_address => address }
  end


  def test_partial_avs_match
    @gateway.expects(:ssl_post).returns(successful_duplicate_response)

    response = @gateway.purchase(@amount, @credit_card, @options)
    assert_equal 'A', response.avs_result['code']
    assert_equal 'Y', response.avs_result['street_match']
    assert_equal 'N', response.avs_result['postal_match']
  end

  def test_using_test_mode
    assert @gateway.test?
  end

  def test_overriding_test_mode
    Base.gateway_mode = :production

    gateway = PayflowGateway.new(
      :login => 'LOGIN',
      :password => 'PASSWORD',
      :test => true
    )

    assert gateway.test?
  end

  def test_using_production_mode
    Base.gateway_mode = :production

    gateway = PayflowGateway.new(
      :login => 'LOGIN',
      :password => 'PASSWORD'
    )

    assert !gateway.test?
  end

  def test_partner_class_accessor
    assert_equal 'PayPal', PayflowGateway.partner
    gateway = PayflowGateway.new(:login => 'test', :password => 'test')
    assert_equal 'PayPal', gateway.options[:partner]
  end

  def test_partner_class_accessor_used_when_passed_in_partner_is_blank
    assert_equal 'PayPal', PayflowGateway.partner
    gateway = PayflowGateway.new(:login => 'test', :password => 'test', :partner => '')
    assert_equal 'PayPal', gateway.options[:partner]
  end

  def test_passed_in_partner_overrides_class_accessor
    assert_equal 'PayPal', PayflowGateway.partner
    gateway = PayflowGateway.new(:login => 'test', :password => 'test', :partner => 'PayPalUk')
    assert_equal 'PayPalUk', gateway.options[:partner]
  end

  def test_express_instance
    gateway = PayflowGateway.new(
      :login => 'test',
      :password => 'password'
    )
    express = gateway.express
    assert_instance_of PayflowExpressGateway, express
    assert_equal 'PayPal', express.options[:partner]
    assert_equal 'test', express.options[:login]
    assert_equal 'password', express.options[:password]
  end

  def test_default_currency
    assert_equal 'USD', PayflowGateway.default_currency
  end

  def test_supported_countries
    assert_equal ['US', 'CA', 'SG', 'AU'], PayflowGateway.supported_countries
  end

  def test_supported_card_types
    assert_equal [:visa, :master, :american_express, :jcb, :discover, :diners_club], PayflowGateway.supported_cardtypes
  end

  def test_initial_recurring_transaction_missing_parameters
    assert_raises ArgumentError do
      response = @gateway.recurring(@amount, @credit_card,
        :periodicity => :monthly,
        :initial_transaction => { }
      )
    end
  end

  def test_initial_purchase_missing_amount
    assert_raises ArgumentError do
      response = @gateway.recurring(@amount, @credit_card,
        :periodicity => :monthly,
        :initial_transaction => { :amount => :purchase }
      )
    end
  end

  def test_successful_recurring_action
    @gateway.stubs(:ssl_post).returns(successful_recurring_response)

    response = @gateway.recurring(@amount, @credit_card, :periodicity => :monthly)

    assert_instance_of PayflowResponse, response
    assert_success response
    assert_equal 'RT0000000009', response.profile_id
    assert response.test?
    assert_equal "R7960E739F80", response.authorization
  end

  def test_recurring_profile_payment_history_inquiry
    @gateway.stubs(:ssl_post).returns(successful_payment_history_recurring_response)

    response = @gateway.recurring_inquiry('RT0000000009', :history => true)
    assert_equal 1, response.payment_history.size
    assert_equal '1', response.payment_history.first['payment_num']
    assert_equal '7.25', response.payment_history.first['amt']
  end

  def test_recurring_profile_payment_history_inquiry_contains_the_proper_xml
    request = @gateway.send( :build_recurring_request, :inquiry, nil, :profile_id => 'RT0000000009', :history => true)
    assert_match %r(<PaymentHistory>Y</PaymentHistory), request
  end

  def test_format_issue_number
    xml = Builder::XmlMarkup.new
    credit_card = credit_card("5641820000000005",
      :type         => "switch",
      :issue_number => 1
    )

    @gateway.send(:add_credit_card, xml, credit_card)
    doc = REXML::Document.new(xml.target!)
    node = REXML::XPath.first(doc, '/Card/ExtData')
    assert_equal '01', node.attributes['Value']
  end

  def test_duplicate_response_flag
    @gateway.expects(:ssl_post).returns(successful_duplicate_response)

    response = @gateway.authorize(@amount, @credit_card, @options)
    assert_success response
    assert response.params['duplicate']
  end

  def test_ensure_gateway_uses_safe_retry
    assert @gateway.retry_safe
  end

  private
  def successful_recurring_response
    <<-XML
<ResponseData>
  <Result>0</Result>
  <Message>Approved</Message>
  <Partner>paypal</Partner>
  <RPRef>R7960E739F80</RPRef>
  <Vendor>ActiveMerchant</Vendor>
  <ProfileId>RT0000000009</ProfileId>
</ResponseData>
  XML
  end

  def successful_payment_history_recurring_response
    <<-XML
<ResponseData>
  <Result>0</Result>
  <Partner>paypal</Partner>
  <RPRef>R7960E739F80</RPRef>
  <Vendor>ActiveMerchant</Vendor>
  <ProfileId>RT0000000009</ProfileId>
  <RPPaymentResult>
    <PaymentNum>1</PaymentNum>
    <PNRef>V18A0D3048AF</PNRef>
    <TransTime>12-Jan-08 04:30 AM</TransTime>
    <Result>0</Result>
    <Tender>C</Tender>
    <Amt Currency="7.25"></Amt>
    <TransState>6</TransState>
  </RPPaymentResult>
</ResponseData>
  XML
  end


  def successful_duplicate_response
    <<-XML
<?xml version="1.0"?>
<XMLPayResponse xmlns="http://www.verisign.com/XMLPay">
	<ResponseData>
		<Vendor>ActiveMerchant</Vendor>
		<Partner>paypal</Partner>
		<TransactionResults>
			<TransactionResult Duplicate="true">
				<Result>0</Result>
				<ProcessorResult>
					<AVSResult>A</AVSResult>
					<CVResult>M</CVResult>
					<HostCode>A</HostCode>
				</ProcessorResult>
				<IAVSResult>N</IAVSResult>
				<AVSResult>
					<StreetMatch>Match</StreetMatch>
					<ZipMatch>No Match</ZipMatch>
				</AVSResult>
				<CVResult>Match</CVResult>
				<Message>Approved</Message>
				<PNRef>V18A0CBB04CF</PNRef>
				<AuthCode>692PNI</AuthCode>
				<ExtData Name="DATE_TO_SETTLE" Value="2007-11-28 10:53:50"/>
			</TransactionResult>
		</TransactionResults>
	</ResponseData>
</XMLPayResponse>
    XML
  end
end
'''

# CONSIDER  does Payflow have a remote test mode?

#  TODO  better name for reference - and use or lose it!
reference = '''<Authorization>
  <PayData>
    <Invoice>
          <BillTo>
            <Name>Ron Weasley</Name>
            <Phone>(555)555-5555</Phone>
            <Address>
              <Street>1234 My Street</Street>
              <City>Ottawa</City>
              <State>ON</State>
              <Country>CA</Country>
              <Zip>K1C2N6</Zip>
            </Address>
          </BillTo>
      <TotalAmt Currency="USD">1.00</TotalAmt>
    </Invoice>
    <Tender>
      <Card>
        <CardType>Visa</CardType>
        <CardNum>4242424242424242</CardNum>
        <ExpDate>201109</ExpDate>
        <NameOnCard>Longbob</NameOnCard>
        <CVNum>123</CVNum>
        <ExtData Name="LASTNAME" Value="Longsen" />
      </Card>
    </Tender>
  </PayData>
</Authorization>'''

'''      def build_credit_card_request(action, money, credit_card, options)
        xml = Builder::XmlMarkup.new
        xml.tag! TRANSACTIONS[action] do
          xml.tag! 'PayData' do
            xml.tag! 'Invoice' do
              xml.tag! 'CustIP', options[:ip] unless options[:ip].blank?
              xml.tag! 'InvNum', options[:order_id].to_s.gsub(/[^\w.]/, '') unless options[:order_id].blank?
              xml.tag! 'Description', options[:description] unless options[:description].blank?

              billing_address = options[:billing_address] || options[:address]
              add_address(xml, 'BillTo', billing_address, options) if billing_address
              add_address(xml, 'ShipTo', options[:shipping_address], options) if options[:shipping_address]

              xml.tag! 'TotalAmt', amount(money), 'Currency' => options[:currency] || currency(money)
            end

            xml.tag! 'Tender' do
              add_credit_card(xml, credit_card)
            end
          end
        end
        xml.target!
      end

      def add_address(xml, tag, address, options)
        return if address.nil?
        xml.tag! tag do
          xml.tag! 'Name', address[:name] unless address[:name].blank?
          xml.tag! 'EMail', options[:email] unless options[:email].blank?
          xml.tag! 'Phone', address[:phone] unless address[:phone].blank?
          xml.tag! 'CustCode', options[:customer] if !options[:customer].blank? && tag == 'BillTo'

          xml.tag! 'Address' do # TODO etc!
            xml.tag! 'Street', address[:address1] unless address[:address1].blank?
            xml.tag! 'City', address[:city] unless address[:city].blank?
            xml.tag! 'State', address[:state].blank? ? "N/A" : address[:state]
            xml.tag! 'Country', address[:country] unless address[:country].blank?
            xml.tag! 'Zip', address[:zip] unless address[:zip].blank?
      '''

xml_pay_request = '''<?xml version="1.0" encoding="UTF-8"?>
<XMLPayRequest Timeout="30" version="2.1"
xmlns="http://www.paypal.com/XMLPay">
  <RequestData>
    <Vendor>LOGIN</Vendor>
    <Partner>PayPal</Partner>
    <Transactions>
      <Transaction>
        <Verbosity>MEDIUM</Verbosity>
        <Authorization>
          <PayData>
            <Invoice>
              <BillTo>
                <Name>Ron Weasley</Name>
                <Phone>(555)555-5555</Phone>
                <Address>
                  <Street>1234 My Street</Street>
                  <City>Ottawa</City>
                  <State>ON</State>
                  <Country>CA</Country>
                  <Zip>K1C2N6</Zip>
                </Address>
              </BillTo>
              <TotalAmt Currency="USD">1.00</TotalAmt>
            </Invoice>
            <Tender>
              <Card>
                <CardType>Visa</CardType>
                <CardNum>4242424242424242</CardNum>
                <ExpDate>201109</ExpDate>
                <NameOnCard>Longbob</NameOnCard>
                <CVNum>123</CVNum>
                <ExtData Name="LASTNAME" Value="Longsen" />
              </Card>
            </Tender>
          </PayData>
        </Authorization>
      </Transaction>
    </Transactions>
  </RequestData>
  <RequestAuth>
    <UserPass>
      <User>LOGIN</User>
      <Password>Y</Password>
    </UserPass>
  </RequestAuth>
</XMLPayRequest>
'''

  # TODO reconstruct ssl_post
