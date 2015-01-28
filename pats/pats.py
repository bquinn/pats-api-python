
# -*- coding: utf-8 -*-

# Copyright (c) 2009, Jaccob Burch
# Copyright (c) 2010, Olivier Hervieu
# Copyright (c) 2011, Ken Pepple
#
# All rights reserved.

# Copyright (c) 2014, Brendan Quinn, Clueful Media Ltd / JT-PATS Ltd
#
# The MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
PATS Python library - Brendan Quinn Dec 2014

Based on Mediaocean PATS API documented at https://developer.mediaocean.com/
"""

from collections import OrderedDict
from httplib import HTTPSConnection
import json
import os
import re
import string
from urllib import urlencode

AGENCY_API_DOMAIN = 'prisma-demo.api.mediaocean.com'
PUBLISHER_API_DOMAIN = 'prisma-demo.api.mediaocean.com'

VERSION = '0.1'

class PATSException(Exception):
    pass

class PATSAPIClient(object):
    # controlled values for product catalogue
    possible_media_types = ['PRINT', 'DIGITAL']
    possible_media_subtypes_print = ['DISPLAY_PRINT', 'CLASSIFIED', 'INSERTS', 'PRINT_CUSTOM']
    possible_media_subtypes_digital = ['DISPLAY_DIGITAL', 'VIDEO', 'MOBILE', 'TABLET', 'APP']
    possible_categories = ['ARTS_AND_ENTERTAINMENT','AUTOMOTIVE','BUSINESS','CAREERS','EDUCATION','FAMILY_AND_PARENTING','HEALTH_AND_FITNESS','FOOD_AND_DRINK','HOBBIES_AND_INTERESTS','HOME_AND_GARDEN','LAW_GOVERNMENT_AND_POLITICS','NEWS','PERSONAL_FINANCE','SOCIETY','SCIENCE','PETS','SPORTS','STYLE_AND_FASHION','TECHNOLOGY_AND_COMPUTING','TRAVEL','REAL_ESTATE','SHOPPING','RELIGION_AND_SPIRITUALITY','SOCIAL_MEDIA']

    def __init__(self, api_key):
        """
        Initialize a PATS instance.
        """
        self.api_key = api_key

    def _get_headers(self, extra_headers):
        # Set User-Agent
        headers = {
            'User-Agent': "PATS Python Library/%s" % VERSION,
            'Content-Type': 'application/json',
            'X-MO-API-Key': self.api_key
        }
        headers.update(extra_headers)
        return headers

    def _send_request(self, method, domain, path, extra_headers, body):
        # Create the http object
        h = HTTPSConnection(domain)

        # uncomment this when things just aren't working...
        # h.set_debuglevel(10)

        # Perform the request and get the response headers and content
        headers = self._get_headers(extra_headers)
        h.request(method,
                  path,
                  body,
                  headers)
        response = h.getresponse()

        # 422 is "unprocessable entity" but more details are given in the JS response
        # so we should use that instead
        if response.status != 200 and response.status != 422:
            self._relay_error(response.status, response.reason)

        
        js = json.JSONDecoder().decode(response.read())

        if response.status == 422 and 'message' in js:
            self._relay_error(js['code'], js['message'])
        # sometimes the call returns 200 but then have a "FAILED" message in the response
        if 'status' in js and js['status'] == 'FAILED':
            # TODO might be fragile, or at least it only returns the first error
            self._relay_error(422, js['fieldValidations'][0]['message'])

        return js

    def _relay_error(self, error_code, reason=""):
        """
        Errors from http://developer.mediaocean.com/docs/catalog_api/Save_print_products_to_catalog:
         - 400 Bad request, the parameters you provided did not validate,
           see message. (Unfortunately 200 can mean a validation error as well! It's
           passed back in the JSON)
         - 401 Not authorized, the API key and/or User-Id given is not valid.
         - 403 Forbidden, The request was a valid request, but the server is refusing to
           respond to it. Unlike a 401 Unauthorized response, authenticating will make
           no difference.
         - 404 Not Found. Entity from the request is not found. A message is included
           giving the reason for the failure.
         - 422 Unprocessable Entity. Request wasn't valid. This is returned as a result
           of a data validation error.
         - 500 Internal server error, something failed to execute properly on
           the PATS/Mediaocean side.
        """
        if error_code == 400:
            raise PATSException(
                "Bad Request. The parameters you provided did not validate")
        elif error_code == 401:
            raise PATSException(
                "%s Probably invalid API key %s" % (reason, self.api_key))
        elif error_code == 406:
            raise PATSException(
                "Not acceptable, your IP address has exceeded the API limit")
        elif error_code == 409:
            raise PATSException(
                "Not approved, the user has yet to approve your retrieve request")
        elif error_code == 500:
            raise PATSException(
                "Internal server error")
        else:
            raise PATSException(
                "Error: %s" % reason)

    def save_product_data(self, vendor_id=None, data=None): 
        """
        Save a new or updated product to a vendor's product catalogue.

        The parameters are :
        - vendor_id (required) : ID of the vendor (publisher) whose catalogue
          you are updating.
        - data (required) : Payload of the product(s) you are updating.
        """
        if vendor_id is None:
            raise PATSException("Vendor ID is required")

        js = self._send_request(
            "POST",
            PUBLISHER_API_DOMAIN,
            "/vendors/%s/products/" % vendor_id,
            { 'Accept': 'application/vnd.mediaocean.catalog-v1+json' },
            json.dumps(data)
        )
        if js['validationResults']:
            raise PATSException("Product ID "+js['validationResults'][0]['productId']+": error is "+js['validationResults'][0]['message'])
        productId = js['products'][0]['productPublicId']
        return js

    def save_product(self, vendor_id, product_id, product_name, image_encoded,
        product_status, product_description, product_url,
        publication_name, publication_url,
        media_type, media_subtype, section, subsections,
        category, nonstandard, product_start_date, product_end_date,
        product_contact_name, product_contact_email, product_contact_phone,
        creative_contact_name, creative_contact_email, creative_contact_phone,
        media_kit_url, rate_card_url, circulation, accepts_colour, editions_available,
        positions_available, sizes_available, publishing_cycle, publication_days, regions_available,
        rate_card_cpm, discount_rate_cpm, positioning,
        # digital only attributes
        placement_type, has_UGC, can_demo_target,
        can_geotarget_country, can_geotarget_region, can_geotarget_city, can_geotarget_post_code,
        can_thirdpartydata_target_exelate, can_thirdpartydata_target_bluekai,
        can_behaviorally_target, is_retargeting, can_whitelist_urls, can_guarantee_sov,
        can_competitive_separate, max_daily_impressions,
        # digital (video) only attributes
        lengths):

        if product_id is None:
            raise PATSException("Product ID is required")
        
        # validation of lots of parameters for uploading products
        media_type = media_type.upper()
        if media_type not in self.possible_media_types:
            raise PATSException("Product %s: media_type '%s' must be one of '%s'" % (product_id, media_type, ','.join(self.possible_media_types)))
        media_subtype = media_subtype.upper()
        if media_type == 'PRINT':
            if media_subtype not in self.possible_media_subtypes_print:
                raise PATSException("media_subtype for PRINT '%s' must be one of '%s'" % (media_subtype, ','.join(self.possible_media_subtypes_print)))
        if media_type == 'DIGITAL':
            if media_subtype not in self.possible_media_subtypes_digital:
                raise PATSException("media_subtype for DIGITAL '%s' must be one of '%s'" % (media_subtype, ','.join(self.possible_media_subtypes_digital)))
        placement_type = placement_type.upper()
        category = category.upper().translate(string.maketrans(" ", "_"))
        if publication_days:
            publisher_days_array = ["{"+day.upper()+"_short}" for day in re.split(',', publication_days)]
        else:
            publisher_days_array = []
        if editions_available:
            if media_type == 'PRINT':
                editions = editions_available
            else:
                editions = [ re.split(',', editions_available) ]
        if media_type == 'DIGITAL' and media_subtype == 'VIDEO':
            lengths_array = [ re.split(',', lengths) ]
        if regions_available:
            regions = re.split(',', regions_available)
        else:
            regions = None
        if positions_available:
            # get rid of empty positions
            positions_available = re.sub(',,+', ',', positions_available)
            positions_available = re.sub(',$', '', positions_available)
            positions_array = re.split(',', positions_available)
        else:
            raise PATSException("Available positions are required")
        if sizes_available:
            # get rid of empties and trailing ",0" sequences that News have in their data
            sizes_available = re.sub(',0', '', sizes_available)
            sizes_available = re.sub(',,+', ',', sizes_available)
            sizes_available = re.sub(',$', '', sizes_available)
            # split and de-dupe
            sizes_array = list(OrderedDict.fromkeys(re.split(',', sizes_available)))
        else:
            raise PATSException("Product sizes are required")
        if not circulation:
            print("Warning: circulation not set. Setting to 0")
            circulation = 0
        if not nonstandard:
            print("Warning: nonstandard not set. Setting to False")
            nonstandard = False
        if subsections:
            subsections_array = re.split(',', subsections)
        #else:
        #    raise PATSException("Subsections are required (for now)")
        if product_end_date:
            pass
            # convert from excel format d/m/Y to ISO format
            #date_object = datetime.strptime(product_end_date, '%d/%m/%Y')
            #end_date = datetime.strftime(date_object, '%Y-%m-%d')
        else:
            end_date = ''
        if not product_contact_email:
            raise PATSException("Product Contact Email is required")
        if not category:
            raise PATSException("Category is required")
        if category not in self.possible_categories:
            raise PATSException("Category '%s' should be one of %s" % (category, ','.join(self.possible_categories)))

        # now create JSON object to be passed to API
        data = {
            "products": [
                {
                    "standardAttributes": {
                      "productId":product_id,
                      "productName":product_name,
                      "productURL":product_url,
                      "status":product_status == 'Active',
                      "productDescription":product_description,
                      "publicationName":publication_name,
                      #"publicationUrl":publication_url,
                      "mediaType":"{"+media_type+"}",
                      "subMediaType":"{"+media_subtype+"}",
                      "productSection":section,
                      "category":"{"+category+"}",
                      "isNonStandard":nonstandard == 'TRUE',
                      "startDate":product_start_date,
                      "endDate":product_end_date,
                      "contactName":product_contact_name,
                      "contactPhone":product_contact_phone,
                      "contactEmail":product_contact_email,
                      #"creativeContactName":creative_contact_name,
                      #"creativeContactPhone":creative_contact_phone,
                      #"creativeContactEmail":creative_contact_email,
                      "mediaKitURL":media_kit_url,
                      "rateCardURL":rate_card_url
                    }
                }
            ]
        }
        if image_encoded:
            data['products'][0]['standardAttributes'].update({
                "productLogo":"data:image/jpeg;base64,"+image_encoded,
            })

        if subsections:
            data['products'][0]['standardAttributes'].update({
                  "productSubSection":subsections_array,
            })
        if media_type == 'PRINT':
            #if regions is None:
            #    raise PATSException("region is required")
            if not publishing_cycle:
                raise PATSException("Publishing cycle is required")
            data['products'][0]['standardAttributes'].update({
                    "acceptsColor" : False,
                    "circulation": int(circulation),
                    "sizes": sizes_array, # ["Full Page","Half Page"],
                    "availablePositions": positions_array, # ["Front Half"],
                    "cycle": publishing_cycle, # "Daily",
                    #"customPlacementAttributes": [],
                    #"customTargetingAttributes": []
            })
            if publisher_days_array:
                data['products'][0]['standardAttributes'].update({
                    "publisherDays" : publisher_days_array,
                })
            if regions:
                data['products'][0]['standardAttributes'].update({
                    "regions": regions, # ["Manhattan"],
                })

        if media_type == 'DIGITAL':
            if not max_daily_impressions:
                max_daily_impressions = 0
            if rate_card_cpm == '':
                rate_card_cpm = '0'
            if discount_rate_cpm == '':
                discount_rate_cpm = '0'
            data['products'][0]['standardAttributes'].update({
                      # digital - generic attributes
                      "sizes": sizes_array, # ["300x250", "320x50"],
                      "placementType":"{"+placement_type+"}",
                      "hasUserGeneratedContent": has_UGC=='TRUE',
                      "canDemoTarget":can_demo_target=='TRUE',
                      "canGeoTargetCountry":can_geotarget_country=='TRUE',
                      "canGeoTargetRegion":can_geotarget_region=='TRUE',
                      "canGeoTargetCity":can_geotarget_city=='TRUE',
                      "canGeoTargetPostalCodes":can_geotarget_post_code=='TRUE',
                      "canThirdPartyDataTargetExelate":can_thirdpartydata_target_exelate=='TRUE',
                      "canThirdPartyDataTargetBlueKai":can_thirdpartydata_target_bluekai=='TRUE',
                      "canBehaviorallyTarget":can_behaviorally_target=='TRUE',
                      "isRetargeting":is_retargeting=='TRUE',
                      "canWhitelistURLs":can_whitelist_urls=='TRUE',
                      "canGuaranteeSOV":can_guarantee_sov=='TRUE',
                      "canCompetitiveSeparate":can_competitive_separate=='TRUE',
                      "maxDailyImpressions":int(max_daily_impressions),
                      "standardRateCardCPM": rate_card_cpm,
                      "standardDiscountCPM": discount_rate_cpm,
                      "positioning": "{"+positioning+"}",

                      # digital - tablet-only attributes
                      #"device": [
                      #    "Android Tablet",
                      #    "Apple Tablet"
                      #],
            })
            if media_subtype == 'VIDEO':
                data['products'][0]['standardAttributes'].update({
                      "length":lengths_array,
                })

            # end standard attributes
#                "customAttributes": "[{'customSection': 'placement section to decide product placement'}, {'comments': 'Draft version'}]"

        return self.save_product_data(vendor_id, data)

    def list_products(self, agency_id=None, vendor_id=None, start_index=None, max_results=None, include_logo=False):
        """
        List products in a vendor's product catalogue.

        The parameters are :
        - agency_id (required): ID of the agency you are representing when making
          the request.
        - vendor_id (required): ID of the vendor (publisher) whose catalogue
          you are requesting.
        - start_index (optional): First product to load (if doing paging)
        - max_results (optional): 
        """
        if vendor_id is None:
            raise PATSException("Vendor ID is required")

        params = {}
        if start_index:
            params.update({'start_index' : start_index})
        if max_results:
            params.update({'max_results' : max_results})
        if include_logo:
            params.update({'include_logo' : include_logo})
        params = urlencode(params)

        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            "/agencies/%s/vendors/%s/products/?%s" % (agency_id, vendor_id, params),
            { 'Accept': 'application/vnd.mediaocean.catalog-v1+json' }
        )
        if js['validationResults']:
            raise PATSException("Product ID "+js['validationResults'][0]['productId']+": error is "+js['validationResults'][0]['message'])
        productId = js['products'][0]['productPublicId']
        return js

    def create_order(self, **kwargs):
        """
        create a print or digital order in PATS.
        agency_id: PATS ID of the buying agency (eg 35-IDSDKAD-7)
        company_id: PATS ID of the buying company (eg PATS3)
        person_id: (optional?) PATS ID of the person sending the order (different
            from the person named as the buyer contact in the order)
        """
        if kwargs.get('agency_id') == None:
            raise PATSException("Agency ID is required")
        if kwargs.get('company_id') == None:
            raise PATSException("Company ID is required")
        if kwargs.get('insertion_order_details') == None:
            raise PATSException("Insertion Order object is required")
        insertion_order = kwargs.get('insertion_order_details', None)

        extra_headers = {}
        extra_headers.update({
            'Accept': 'application/vnd.mediaocean.prisma-v1.0+json',
            'X-MO-Company-ID': kwargs.get('company_id'),
            'X-MO-Organization-ID': kwargs.get('agency_id')
        })
        if kwargs.get('person_id'):
            extra_headers.update({
                'X-MO-Person-ID': kwargs['person_id']
            })
            
        # order payload
        data = {
            'externalCampaignId':kwargs.get('external_campaign_id', None),
            'mediaType':kwargs.get('media_type', 'PRINT'),
            'insertionOrder':insertion_order.dict_repr()
        }
        # technically line items are optional!
        if kwargs.get('line_items'):
            line_items = []
            for line_item in kwargs['line_items']:
                line_items.append(line_item.dict_repr())
            data.update({
                'lineItems':line_items
            })

        # send request
        js = self._send_request(
            "PUT",
            AGENCY_API_DOMAIN,
            "/order/send",
            extra_headers,
            json.dumps(data)
        )
        return js

    def create_campaign(self, campaign_details=None, **kwargs):
        """
        Create an agency-side campaign, which is then used to send RFPs and orders.
        "campaign_details" must be a CampaignDetails instance.
        """
        if not isinstance(campaign_details, CampaignDetails):
            raise PATSException(
                "The campaign_details parameter should be a CampaignDetails instance")

        # Create the http object
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.prisma-v1.0+json',
            'X-MO-Person-ID': campaign_details.person_id,
            'X-MO-Company-ID': campaign_details.company_id,
            'X-MO-Organization-ID': campaign_details.organisation_id
        }
        js = self._send_request(
            "POST",
            AGENCY_API_DOMAIN,
            "/campaigns",
            extra_headers,
            campaign_details.json_repr()
        )

        campaignId = js['campaignId']
        return campaignId
        

class JSONSerializable(object):
    def json_repr(self):
        return json.dumps(self.dict_repr())

    def dict_repr(self):
        raise PATSException("We shouldn't get here, stuff should happen in subclass")

class CampaignDetails(JSONSerializable):
    """
    CampaignDetails - 
    """
    organisation_id = '' # 
    person_id = '' # 'amh1' or 'brenddlo'
    company_id = '' # 'PATS3'
    campaign_name = '' # "BQ Monday test campaign 1"
    external_campaign_id = '' # "BQMONDAYTEST1"
    start_date = '' # "2015-02-01"
    end_date = '' # "2015-02-28"
    advertiser_code = '' # code of advertiser, eg "DEM"
    media_mix = [] # { "Media": [ { "MediaMix": "Online" }, { "MediaMix": "Print" } ] }
    campaign_budget = 0 # 1000000
    external_campaign_id = '' # "BQMONDAYTEST1"

    def __init__(self, *args, **kwargs):
        self.organisation_id = kwargs.get('organisation_id', '')
        self.person_id = kwargs.get('person_id', '')
        self.company_id = kwargs.get('company_id', '')
        self.campaign_name = kwargs.get('campaign_name', '')
        self.start_date = kwargs.get('start_date', '')
        self.end_date = kwargs.get('end_date', '')
        self.advertiser_code = kwargs.get('advertiser_code', '')
        self.print_campaign = kwargs.get('print_campaign', [])
        self.print_campaign_budget = kwargs.get('print_campaign_budget', [])
        self.digital_campaign = kwargs.get('digital_campaign', [])
        self.digital_campaign_budget = kwargs.get('digital_campaign_budget', [])
        self.campaign_budget = kwargs.get('campaign_budget', '')
        self.external_campaign_id = kwargs.get('external_campaign_id', '')

    def dict_repr(self):
        dict = {
            "CampaignName": self.campaign_name,
            "StartDate": self.start_date,
            "EndDate": self.end_date,
            "Advertiser": self.advertiser_code,
            # update MediaBudget below
            "ExternalDetails": {
                "CampaignSourceID": self.external_campaign_id
            }
        }
        # we want to end up with
        # "MediaBudget": { "Medias": { "Media": [ { "MediaMix": "Online" }, {"MediaMix": "Print" } ] }, "CampaignBudget": 50000 }
        media_budget = {}
        if self.campaign_budget:
            media_budget.update({
                "CampaignBudget": self.campaign_budget,
            })
        medias = []
        if self.print_campaign:
            medias.append({ "MediaMix": "Print" })
        if self.print_campaign_budget:
            pass #TODO
        if self.digital_campaign:
            medias.append({ "MediaMix": "Online" })
        if self.digital_campaign_budget:
            pass #TODO
        media_budget.update({ "Medias": { "Media": medias } })
        dict.update({'MediaBudget': media_budget})
        return dict
        
class InsertionOrderDetails(JSONSerializable):
    """
    InsertionOrderDetails - generic attributes of an order (print or digital).
    """
    campaign_id = None
    order_id = None
    media_type = None
    publisher_id = None
    agency_buyer_first_name = None
    agency_buyer_last_name = None
    agency_buyer_email = None
    order_number = None # not needed?
    recipient_emails = []
    # [{"name":"Extra Ts and Cs","content":"Extra Terms and Conditions that apply to the LOreal booking."}],
    terms_and_conditions = []
    respond_by_date = None # "2015-01-20"
    additional_info = None # "",
    message = None # "Here's a sample order for the L'Oreal campaign."
    notify_emails = [] # ":["brendanquinnoz@gmail.com"]

    def __init__(self, *args, **kwargs):
        self.campaign_id = kwargs.get('campaign_id', '')
        self.media_type = kwargs.get('media_type', '')
        self.order_id = kwargs.get('order_id', '')
        self.publisher_id = kwargs.get('publisher_id', '')
        self.agency_buyer_first_name = kwargs.get('agency_buyer_first_name', '')
        self.agency_buyer_last_name = kwargs.get('agency_buyer_last_name', '')
        self.agency_buyer_email = kwargs.get('agency_buyer_email', '')
        self.order_number = kwargs.get('order_number', '')
        self.recipient_emails = kwargs.get('recipient_emails', [])
        # this is actually an array so needs to change
        self.terms_and_conditions = kwargs.get('terms_and_conditions', [])
        self.respond_by_date = kwargs.get('respond_by_date', '')
        self.additional_info = kwargs.get('additional_info', '')
        self.message = kwargs.get('message', '')
        self.notify_emails = kwargs.get('notify_emails', [])

    def dict_repr(self):
        dict = {
            "orderId":self.order_id,
            "publisherId": self.publisher_id,
            "agencyBuyerFirstName": self.agency_buyer_first_name,
            "agencyBuyerLastName": self.agency_buyer_last_name,
            "agencyBuyerEmail": self.agency_buyer_email,
            "orderNumber": self.order_number, 
            "recipientEmails": self.recipient_emails, # array
            "termsAndConditions": self.terms_and_conditions, # array
            "respondByDate": self.respond_by_date, 
            "additionalInfo": self.additional_info, 
            "message": self.message,
            "notifyEmails": self.notify_emails # array
        }
        return dict

class InsertionOrderLineItem(JSONSerializable):
    lineNumber = None # "1",
    externalPlacementId = None # ":"TestOrder-Monday-NewsUK-1-001",
    placementNumber = None # ":"TestOrder-Monday-NewsUK-1-001",
    placementName = None # ":"Times Sport Banner",
    costMethod = None # "CPM",
    unitAmount = None # "2000000",
    plannedCost = None # "30000.00",
    unitType = None # "Impressions",
    section = None # "Sport",
    subMediaType = None #  "Display (Digital)",
    productId = None # "TIMESSPORTBANNER",
    buyCategory = None # "Standard",
    packageType = None # "Standalone",

    def __init__(self, *args, **kwargs):
        # we probably should generate this automatically? what happens to it as the order changes?
        self.lineNumber = kwargs.get('lineNumber', '')
        self.externalPlacementId = kwargs.get('externalPlacementId', '')
        self.placementNumber = kwargs.get('placementNumber', '')
        self.placementName = kwargs.get('placementName', '')
        self.costMethod = kwargs.get('costMethod', '')
        self.unitAmount = kwargs.get('unitAmount', '')
        self.plannedCost = kwargs.get('plannedCost', '')
        self.unitType = kwargs.get('unitType', '')
        self.section = kwargs.get('section', '')
        self.subMediaType = kwargs.get('subMediaType', '')
        self.productId = kwargs.get('productId', '')
        self.buyCategory = kwargs.get('buyCategory', '')
        self.packageType = kwargs.get('packageType', '')

    def dict_repr(self):
        dict = {
            "lineNumber":self.lineNumber,
            "externalPlacementId":self.externalPlacementId,
            "placementNumber": self.placementNumber,
            "placementName":self.placementName,
            "costMethod": self.costMethod,
            "unitAmount": self.unitAmount,
            "plannedCost": self.plannedCost,
            "unitType": self.unitType,
            "section": self.section,
            "subMediaType": self.subMediaType,
            "productId": self.productId,
            "buyCategory": self.buyCategory,
            # FIXME: for 2015.1, packages are not supported, so this fails to show up in the inbox grid
            # "packageType": self.packageType
        }
        return dict

class InsertionOrderLineItemPrint(InsertionOrderLineItem):
    # lineNumber, externalPlacementId, placementNumber, placementName, costMethod, plannedCost,
    # unitType, subMediaType, section, buyCategory, packageType, productId all handled in parent class

    publication = None # "Time",
    # "printInsertion":{
    size = None # ":"25x4",
    color = None # ":"4CLR",
    colorName = None # ":"4 colour",
    printPosition = None # ":"Front Half",
    positionName = None # ":"Front Half",
    isPositionGuaranteed = None # ":"false",
    includeInDigitalEdition = None # ":"false",
    coverDate = None # ":"2015-02-10",
    saleDate = None # ":"2015-02-01",
    copyDeadline = None # ":"2015-02-01"
    # }

    def __init__(self, *args, **kwargs):
        super(InsertionOrderLineItemPrint, self).__init__(*args, **kwargs)
        self.size = kwargs.get('size', '')
        self.color = kwargs.get('color', '')
        self.colorName = kwargs.get('colorName', '')
        self.printPosition = kwargs.get('printPosition', '')
        self.positionName = kwargs.get('positionName', '')
        self.isPositionGuaranteed = kwargs.get('isPositionGuaranteed', '')
        self.includeInDigitalEdition = kwargs.get('includeInDigitalEdition', '')
        self.coverDate = kwargs.get('coverDate', '')
        self.saleDate = kwargs.get('saleDate', '')
        self.copyDeadline = kwargs.get('copyDeadline', '')

    def dict_repr(self, line_number):
        dict = super(InsertionOrderLineItemPrint, self).dict_repr()
        dict.update({
            "publication": self.publication,
            "size": self.size,
            "color": self.color,
            "colorName": self.colorName,
            "printPosition": self.printPosition,
            "positionName": self.positionName,
            "isPositionGuaranteed":self.isPositionGuaranteed,
            "includeInDigitalEditirion": self.includeInDigitalEdition,
            "coverDate": self.coverDate,
            "saleDate": self.saleDate,
            "copyDeadline": self.copyDeadline
        })
        return dict

class InsertionOrderLineItemDigital(InsertionOrderLineItem):
    site = None # ": "thetimes.co.uk" ,
    rate = None # "15.00",
    flightStart = None # "2015-02-01",
    flightEnd = None # "2015-02-28",
    dimensions = None #  "468x60",
    dimensionsPosition = None #  "Above the Fold",
    servedBy = None # "3rd party",
    bookingCategoryName = None # "Standard",
    # needs to be its own object probably
    flighting = None #":[
    #    { "startDate":"2015-02-01", "endDate":"2015-02-28", "unitAmount":"2000000", "plannedCost":"30000.00" }
    #]

    def __init__(self, *args, **kwargs):
        super(InsertionOrderLineItemDigital, self).__init__(*args, **kwargs)
        self.site = kwargs.get('site', '')
        self.rate = kwargs.get('rate', '')
        self.flightStart = kwargs.get('flightStart', '')
        self.flightEnd = kwargs.get('flightEnd', '')
        self.dimensions = kwargs.get('dimensions', '')
        self.dimensionsPosition = kwargs.get('dimensionsPosition', '')
        self.servedBy = kwargs.get('servedBy', '')
        self.bookingCategoryName = kwargs.get('bookingCategoryName', '')
        self.flighting = kwargs.get('flighting', [])

    def dict_repr(self):
        dict = super(InsertionOrderLineItemDigital, self).dict_repr()
        dict.update({
            "site": self.site,
            "rate": self.rate,
            "flightStart": self.flightStart,
            "flightEnd": self.flightEnd,
            "dimensions": self.dimensions,
            "dimensionsPosition": self.dimensionsPosition,
            "servedBy": self.servedBy,
            "bookingCategoryName": self.bookingCategoryName,
            "flighting": self.flighting
        })
        return dict
