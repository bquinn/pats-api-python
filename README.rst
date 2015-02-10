pats - Interface to the PATS API
================================

Python API wrapper for PATS, the Publishers Advertising Transaction System
(http://www.pats.org.uk/)

Installation
------------

Installing from pypi (using pip - not ready yet)::

    pip install pats

Installing from github::

    pip install -e git://github.com/bquinn/.git#egg=pats-api-python

Usage
-----

Example::

    import pats

    pats_buyer = pats.PATSAPIClient(api_key=PATS_AGENCY_API_KEY, agency_id=AGENCY_ID)
    pats_seller = pats.PATSAPIClient(api_key=PATS_PUBLISHER_API_KEY, vendor_id=VENDOR_ID)

    # create a new campaign
    campaign_details = pats.CampaignDetails(
        organisation_id = 'xxxxxx',
        person_id = 'yyyyy',
        company_id = 'COMPANYID',
        campaign_name = 'PATS API test campaign 1',
        start_date = '2015-02-01',
        end_date = '2015-02-28',
        advertiser_code = 'AAB',
        print_campaign=True,
        digital_campaign=True,
        campaign_budget = 1000000,
        external_campaign_id= 'BQTESTCAMPAIGN1'
    )

    campaign_id = pats_buyer.create_campaign(campaign_details)
    # returns PATS Campaign ID eg 'CPZVF'

    insertion_order_details = InsertionOrderDetails(
        order_id='MyTestOrder-0001',
        publisher_id=PATS_PUBLISHER_ID,
        agency_buyer_first_name='Brendan',
        agency_buyer_last_name='Quinn',
        agency_buyer_email='brendan@patsbuyer.com',
        order_number='1111',
        recipient_emails=['patsdemo@patsseller.com'],
        terms_and_conditions=[{"name":"Test Ts and Cs", "content":"Test Ts and Cs"}],
        respond_by_date='2015-01-27',
        additional_info='No additional info',
        message='This is the message sent with the order',
        notify_emails=['brendan@patswatcher.com']
    )

    line_item_1 = InsertionOrderLineItemDigital(
        lineNumber="1",
        externalPlacementId="TestOrder-Monday-PATSTest-1-001",
        placementName="Sport Banner",
        costMethod="CPM",
        unitAmount="2000000",
        plannedCost="30000.00",
        unitType="Impressions",
        section="Sport",
        subMediaType="Display (Digital)",
        productId="PATSSPORTBANNER",
        buyCategory="Standard",
        packageType="Standalone",
        site="mysite.co.uk",
        rate="15.00",
        flightStart="2015-02-01",
        flightEnd="2015-02-28",
        dimensions="468x60",
        dimensionsPosition="Above the Fold",
        servedBy="3rd party",
        bookingCategoryName="Standalone",
        flighting=[
            { "startDate": "2015-02-01", "endDate": "2015-02-28", "unitAmount": 2000000, "plannedCost": "30000.00" }
        ]
    )
    line_items = [ line_item_1 ]
    response = pats_buyer.create_order(agency_id=agency_id, company_id=company_id, person_id=person_id, external_campaign_id=external_campaign_id, media_type=media_type, insertion_order_details=insertion_order_details, line_items=line_items)
    # returns {"status":"SUCCESSFUL","fieldValidations":[],"publicId":"MyTestOrder-0001","version":1}
    
Features so far
---------------

Buyer side:
* Create campaign: create_campaign()
* View campaign including RFPs: view_campaign_detail()
* RFPs:
  * Submit RFP submit_rfp() (coming soon)
  * Submit product-based RFP: submit_product_rfp() (coming soon)
  * View RFP including proposals: view_rfp_detail(user_email, rfp_id)
  * Get RFP attachment: get_rfp_attachment(user_email, rfp_id, attachment_id)
  * Search RFPs: search_rfps()
  * Get proposal attachment: get_proposal_attachment(user_email, proposal_id, attachment_id)
  * Return proposal: return_proposal() (coming soon)
* Orders:
  * Create print or digital order against a campaign: create_order()
  * View orders between dates: view_orders(start_date, end_date)
  * (NB: "Get order status" is changing for next version)
  * Return order revision: return_order_revision(order_public_id, order_major_version, order_minor_version, buyer_email, seller_email, revision_due_date, comment)
* Product Catalogue:
  * list products: list_products()
* Entity classes:
  * Constructors for campaign details, order details, print line item, digital line item

Seller side:
* Product Catalogue:
  * add or edit print or digital product: save_product()
  * list products: list_products()
* Orders:
  * View orders between dates: view_orders(start_date, end_date)
  * View detail of an order: view_order_detail(order_id)
* RFPs:
  * View RFPs between dates: view_rfps(start_date, end_date)
  * View proposals for an RFP: view_proposals(rfp_id)
  * Send proposal against an RFP: send_proposal(rfp_id, proposal_external_id, comments, digital_line_items, print_line_items)
  * 
