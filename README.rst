pats - Interface to the PATS API
================================

Python API wrapper for PATS, the Publishers Advertising Transaction System
(http://www.pats.org.uk/)

Installation
------------

Installing from pypi (using pip - not ready yet):

    pip install pats

Installing from github:

    pip install -e git://github.com/bquinn/.git#egg=pats-api-python

Documentation
-------------

See https://pats.readthedocs.org/en/latest/

Example
-------

    import pats

    patsapi = pats.PATSAPIClient(api_key=MEDIAOCEAN_AGENCY_API_KEY)

    # create a new campaign
    campaign_details = pats.CampaignDetails(
        organisation_id = '35-IDSDKAD-7',
        person_id = 'brenddlo',
        company_id = 'PATS3',
        campaign_name = 'BQ PATS API test campaign 1',
        start_date = '2015-02-01',
        end_date = '2015-02-28',
        advertiser_code = 'AAB',
        print_campaign=True,
        digital_campaign=True,
        campaign_budget = 1000000,
        external_campaign_id = 'BQ2601TEST5'
    )

    campaign_id = patsapi.create_campaign(campaign_details)
    # returns PATS Campaign ID eg 'CPZVF'

    insertion_order_details = InsertionOrderDetails(
        order_id='MyTestOrder-0001',
        publisher_id=PATS_PUBLISHER_ID,
        agency_buyer_first_name='Brendan',
        agency_buyer_last_name='Quinn',
        agency_buyer_email='brendan@cluefulmedia.com',
        order_number='1111',
        recipient_emails=['patsdemo@engineer.com'],
        terms_and_conditions=[{"name":"Test Ts and Cs", "content":"Test Ts and Cs"}],
        respond_by_date='2015-01-27',
        additional_info='No additional info',
        message='This is the message sent with the order',
        notify_emails=['brendan@aggrity.com']
    )

    line_item_1 = InsertionOrderLineItemDigital(
        lineNumber="1",
        externalPlacementId="TestOrder-Monday-NewsUK-1-001",
        placementNumber="TestOrder-Monday-NewsUK-1-001",
        placementName="Times Sport Banner",
        costMethod="CPM",
        unitAmount="2000000",
        plannedCost="30000.00",
        unitType="Impressions",
        section="Sport",
        subMediaType="Display (Digital)",
        productId="TIMESSPORTBANNER",
        buyCategory="Standard",
        packageType="Standalone",
        site="thetimes.co.uk",
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
    response = pats.create_order(agency_id=agency_id, company_id=company_id, person_id=person_id, external_campaign_id=external_campaign_id, media_type=media_type, insertion_order_details=insertion_order_details, line_items=line_items)
    # returns {"status":"SUCCESSFUL","fieldValidations":[],"publicId":"MyTestOrder-0001","version":1}
    
Features so far
---------------

Seller side:
- Product Catalogue:
  - add print or digital product: save_product()
  - list products: list_products()

Buyer side:
- Create campaign: create_campaign()
- Create print or digital order against a campaign: create_order()
- Constructors for campaign details, order details, print line item, digital line item
