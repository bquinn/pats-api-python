# -*- coding: utf-8 -*-

# Copyright (c) 2015, Brendan Quinn, Clueful Media Ltd / JT-PATS Ltd
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
PATS Python library - Core functions - Brendan Quinn Dec 2014

Based on Mediaocean PATS API documented at https://developer.mediaocean.com/
"""

from collections import OrderedDict
from httplib import HTTPSConnection
import datetime
import json
import os
import re
import string
from urllib import urlencode

VERSION = '0.5'

class PATSException(Exception):
    pass

class PATSAPIClient(object):
    # controlled values for product catalogue
    possible_media_types = ['PRINT', 'DIGITAL']
    possible_media_subtypes_print = ['DISPLAY_PRINT', 'CLASSIFIED', 'INSERTS', 'PRINT_CUSTOM']
    possible_media_subtypes_digital = ['DISPLAY_DIGITAL', 'VIDEO', 'MOBILE', 'TABLET', 'APP']
    # "old" values pre April 2015
    # possible_categories = ['ARTS_AND_ENTERTAINMENT','AUTOMOTIVE','BUSINESS','CAREERS','EDUCATION','FAMILY_AND_PARENTING','HEALTH_AND_FITNESS','FOOD_AND_DRINK','HOBBIES_AND_INTERESTS','HOME_AND_GARDEN','LAW_GOVERNMENT_AND_POLITICS','NEWS','PERSONAL_FINANCE','SOCIETY','SCIENCE','PETS','SPORTS','STYLE_AND_FASHION','TECHNOLOGY_AND_COMPUTING','TRAVEL','REAL_ESTATE','SHOPPING','RELIGION_AND_SPIRITUALITY','SOCIAL_MEDIA']
    # "new" values sent by Jon on 8 April 2015
    possible_categories = ['ARTS_AND_ENTERTAINMENT','BEAUTY_AND_FITNESS','BOOKS_AND_LITERATURE','BUSINESS_AND_INDUSTRIAL','COMPUTERS_AND_ELECTRONICS','FINANCE','FOOD_AND_DRINK','GAMES','HEALTH','HOBBIES_AND_LEISURE','HOME_AND_GARDEN','INTERNET_AND_TELECOM','JOBS_AND_EDUCATION','LAW_GOVT_AND_POLITICS_NEWS','ONLINE_COMMUNITIES','PEOPLE_AND_SOCIETY','PETS_AND_ANIMALS','REAL_ESTATE','REFERENCE','SCIENCE','SHOPPING','SPORTS','TRAVEL']
    # debugging mode flag
    debug_mode = False

    # raw_mode - update information about raw request and response payloads
    raw_mode = False

    # session - if we need to write info to the session, it will be injected in the constructor
    session = None

    def __init__(self, api_key, debug_mode=False, raw_mode=False, session=None):
        """
        Initialize a PATS instance.
        Parameters:
        api_key: key of PATS API user (buyer or seller as appropriate).
        debug_mode: if True, output HTTP request and response.
        raw_mode: store curl equivalent of each command, and the raw output, in user session if provided
        session: handle to user session object which stores data in raw mode
        """
        self.api_key = api_key
        if debug_mode:
            self.debug_mode = True
        if raw_mode:
            self.raw_mode = True
        if session:
            self.session = session

    def _get_headers(self, extra_headers):
        # Set user agent, API key and output type
        content_type = 'application/json'
        headers = {
            'User-Agent': "PATS Python Library/%s" % VERSION,
            'Content-Type': content_type,
            'X-MO-API-Key': self.api_key
        }
        headers.update(extra_headers)
        return headers

    def _send_request(self, method, domain, path, extra_headers, body=None):
        # Create the http object
        h = HTTPSConnection(domain)

        if self.debug_mode:
            h.set_debuglevel(10)

        # Construct the request headers
        headers = self._get_headers(extra_headers)

        # In "raw mode", create the equivalent curl(1) command for this request
        # and save it in the session provided in the constructor
        curl = ''
        if self.raw_mode and self.session:
            curl = 'curl -v -X "%s" ' % method
            for header_name, header_value in headers.iteritems():
                curl += '-H "%s: %s" ' % (header_name, header_value)
            if body:
                # we want to turn ' into '"'"' for curl output so we need to do this!
                match = re.compile("'")
                curl_body = match.sub("'\"'\"'", body)
                if method == "POST" or method == "PUT":
                    curl += "--data '%s' " % curl_body
            # escape the url in double-quotes because it might contain & characters
            curl += '"https://%s%s"' % (domain, path)
            self.session['curl_command'] = curl
             
        # Perform the request and get the response headers and content
        h.request(method,
                  path,
                  body,
                  headers)
        response = h.getresponse()
        response_status = response.status
        response_text = response.read()
        if self.raw_mode and self.session:
            self.session['response_status'] = response_status
            self.session['response_text'] = response_text

        if self.debug_mode:
            print "DEBUG: response status is %d, full response is" % response_status
            print response_text

        # Bad Request gives an error in text, not JSON
        if response_status == 400:
            self._relay_error(response_status, response_text)

        # 422 is "unprocessable entity" but more details are given in the JS response
        # so we should use that instead
        if response_status != 200 and response_status != 422:
            self._relay_error(response_status, response.reason + " " + response_text)

        js = None
        if response_text == '':
            return ''

        js = json.JSONDecoder().decode(response_text)

        if response_status == 422:
            if 'message' in js:
                self._relay_error(js['code'], js['message'])
            else:
                # if we didn't get a JSON payload (eg Create RFP), just report the whole response
                self._relay_error(response_status, response_text)
        # sometimes the call returns 200 but then have a "FAILED" message in the response
        if 'status' in js and js['status'] == 'FAILED':
            errorString = ""
            for errorjs in js['fieldValidations']:
                if errorString:
                    errorString += ", "
                if 'dataName' in errorjs and errorjs['dataName'] != None:
                    errorString += errorjs['dataName'] + ": "
                if 'message' in errorjs:
                    errorString += errorjs['message']
            self._relay_error(422, errorString)

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
                "%s (Possibly invalid API key) %s" % (reason, self.api_key))
        elif error_code == 404:
            raise PATSException(
                "Not found: %s" % reason)
        elif error_code == 406:
            raise PATSException(
                "Not acceptable (perhaps your IP address has exceeded the API limit?)")
        elif error_code == 409:
            raise PATSException(
                "Not approved, the user has yet to approve your retrieve request")
        elif error_code == 500:
            raise PATSException(
                "Internal server error")
        else:
            raise PATSException(
                "Error: %s" % reason)

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
        if not isinstance(self.start_date, datetime.date):
            raise PATSException("Campaign start date must be a Python date (or blank)")
        self.end_date = kwargs.get('end_date', '')
        if not isinstance(self.end_date, datetime.date):
            raise PATSException("Campaign end date must be a Python date (or blank)")
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
            "StartDate": self.start_date.strftime("%Y-%m-%d"),
            "EndDate": self.end_date.strftime("%Y-%m-%d"),
            "Advertiser": self.advertiser_code,
            # update MediaBudget below
            "ExternalDetails": {
                "CampaignSourceID": self.external_campaign_id
            }
        }
        if self.campaign_budget and (self.print_campaign_budget or self.digital_campaign_budget):
            raise PATSException("Campaign can't have both individual budgets and a campaign budget")
        # we want to end up with either
        # "MediaBudget": { "Medias": { "Media": [ { "MediaMix": "Online" }, {"MediaMix": "Print" } ] }, "CampaignBudget": 50000 }
        # or
        # "MediaBudget": { "Medias": { "Media": [ { "MediaMix": "Online", "Budget": 50000.00 } ] } }
        media_budget = {}
        if self.campaign_budget:
            media_budget.update({
                "CampaignBudget": self.campaign_budget,
            })
        medias = []
        if self.print_campaign:
            print_campaign = {"MediaMix": "Print"}
            if self.print_campaign_budget:
                print_campaign.update({"Budget": self.print_campaign_budget})
            medias.append(print_campaign)
        if self.digital_campaign:
            digital_campaign = {"MediaMix": "Online"}
            if self.digital_campaign_budget:
                digital_campaign.update({"Budget": self.digital_campaign_budget})
            medias.append(digital_campaign)
        media_budget.update({ "Medias": { "Media": medias } })
        dict.update({'MediaBudget': media_budget})
        return dict
        
class InsertionOrderDetails(JSONSerializable):
    """
    InsertionOrderDetails - generic attributes of an order (print or digital).
    """
    campaign_id = None
    external_order_id = None
    external_publisher_order_id = None
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
        self.external_order_id = kwargs.get('external_order_id', '')
        if len(self.external_order_id) > 32:
            raise PATSException("Order fails if length of external_order_id is more than 32 characters")
        self.external_publisher_order_id = kwargs.get('external_order_id', '')
        if len(self.external_publisher_order_id) > 32:
            raise PATSException("Order fails if length of external_publisher_order_id is more than 32 characters")
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
            "externalOrderId":self.external_order_id,
            "externalPublisherOrderId":self.external_publisher_order_id,
            "publisherId": self.publisher_id,
            "agencyBuyerFirstName": self.agency_buyer_first_name,
            "agencyBuyerLastName": self.agency_buyer_last_name,
            "agencyBuyerEmail": self.agency_buyer_email,
            "recipientEmails": self.recipient_emails, # array of strings
            "termsAndConditions": self.terms_and_conditions, # array of "name" / "content" pairs
            "respondByDate": self.respond_by_date.strftime("%Y-%m-%d"), 
            "additionalInfo": self.additional_info, 
            "message": self.message,
            "notifyEmails": self.notify_emails # array of strings
        }
        return dict

class InsertionOrderLineItem(JSONSerializable):
    lineNumber = None # "1",
    externalPlacementId = None # ":"TestOrder-Monday-NewsUK-1-001",
    lineItemExternalId = None # used in proposals apparently
    placementName = None # ":"Times Sport Banner",
    costMethod = None # "CPM",
    rate = None # "15.0",
    plannedCost = None # "30000.00",
    unitType = None # "Impressions",
    section = None # "Sport",
    subsection = None # "Football",
    subMediaType = None #  "Display (Digital)",
    productId = None # "TIMESSPORTBANNER",
    buyCategory = None # "Standard",
    buyType = None # "Display", only used in revisions
    packageType = None # "Standalone",
    packageName = None # "MyCoolPackage",

    possible_operations = [
        'Add',
        'Update',
        'Delete'
    ]

    operation = 'Add'

    def getvar(self, varname, default, args, kwargs):
        """
        Sometimes we're passed a kwargs string, sometimes a dict. This handles both
        (but there is probably a nicer way to do this)
        """
        if args:
            return args[0].get(varname, default)
        if kwargs:
            return kwargs.get(varname, default)

    def __init__(self, *args, **kwargs):
        self.operation = self.getvar('operation', 'Add', args, kwargs)
        self.lineNumber = self.getvar('lineNumber', '', args, kwargs)
        self.externalPlacementId = self.getvar('externalPlacementId', '', args, kwargs)
        self.lineItemExternalId = self.getvar('lineItemExternalId', '', args, kwargs)
        self.placementName = self.getvar('placementName', '', args, kwargs)
        self.costMethod = self.getvar('costMethod', '', args, kwargs)
        self.unitType = self.getvar('unitType', '', args, kwargs)
        self.plannedCost = self.getvar('plannedCost', None, args, kwargs)
        self.costMethod = self.getvar('costMethod', '', args, kwargs)
        self.buyCategory = self.getvar('buyCategory', '', args, kwargs)
        self.buyType = self.getvar('buyType', '', args, kwargs)
        self.rate = self.getvar('rate', None, args, kwargs)
        self.section = self.getvar('section', '', args, kwargs)
        self.subsection = self.getvar('subsection', '', args, kwargs)
        self.comments = self.getvar('comments', '', args, kwargs)
        self.packageType = self.getvar('packageType', 'Standalone', args, kwargs)
        self.packageName = self.getvar('packageName', '', args, kwargs)
        self.subMediaType = self.getvar('subMediaType', '', args, kwargs)
        self.target = self.getvar('target', '', args, kwargs)
        self.productId = self.getvar('productId', '', args, kwargs)

    def setOperation(self, operation):
        if operation not in self.possible_operations:
            raise PATSException('Operation %s should be one of %s' % (operation, ', '.join(self.possible_operations)))
        self.operation = operation

    def dict_repr(self, mode="buyer"):
        dict = {
            "lineNumber": self.lineNumber,
            "externalPlacementId": self.externalPlacementId,
            "packageType": self.packageType,
            "costMethod": self.costMethod,
            "unitType": self.unitType,
            "section": self.section,
            "buyCategory": self.buyCategory,
            "comments": self.comments,
            "target": self.target,
        }
        if self.rate != None:
            dict.update({
                "rate": "{0:.4f}".format(self.rate)
            })
        if self.plannedCost != None:
            dict.update({
                "plannedCost": "{0:.2f}".format(self.plannedCost)
            })
        else:
            dict.update({
                "plannedCost": ""
            })
        if mode == "buyer":
            dict.update({
                "operation": self.operation,
                "placementName": self.placementName,
                # fails for digital - PATS-522
                "subsection": self.subsection,
                "subMediaType": self.subMediaType
            })
        else:
            # handle submediatype and subsection differently on seller side
            customColumns = []
            if self.subMediaType:
                customColumns.append({
                    "name": "SUBMEDIATYPE",
                    "value": self.subMediaType
                })
            if self.subsection:
                customColumns.append({
                    "name": "SUBSECTION",
                    "value": self.subsection
                })
            # for no good reason, on the seller side placementName is called "name"
            dict.update({
                "name": self.placementName,
                # we also have a separate buyType in revision mode only
                "buyType": self.buyType,
                "customColumns": customColumns
            })
        if self.externalPlacementId:
            dict.update({
                "externalPlacementId": self.externalPlacementId
            })
        if self.lineItemExternalId:
            dict.update({
                "lineItemExternalId": self.lineItemExternalId
            })
        if self.productId:
            dict.update({
                "productId": self.productId
            })
        if self.packageName:
            dict.update({
                "packageName": self.packageName
            })
        return dict

class InsertionOrderLineItemPrint(InsertionOrderLineItem):
    # lineNumber, externalPlacementId, placementName, costMethod, plannedCost,
    # unitType, subMediaType, section, subsection, buyCategory, packageType, productId all handled in parent class

    # for validation
    possible_buy_categories_print = [
        # implied buyType: Newspaper
        'Consumer', 'Trade',
        # implied buyType: Magazine
        'Classified - National', 'Classified - Regional', 'Display - National', 'Display - Regional',
        # implied buyType: Supplement
        'Direct Mail', 'Directories, i.e. Yellow Pages', 'Inserts', 'Sponsorship',
        # implied buyType: Fee
        'Production'
    ]

    publication = None # "Time",
    # "printInsertion":{
    size = None # ":"25x4",
    # print has "units", digital has "unitAmount" for some reason
    units = 0
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
        self.publication = self.getvar('publication', '', args, kwargs)
        self.size = self.getvar('size', '', args, kwargs)
        self.color = self.getvar('color', '', args, kwargs)
        self.units = self.getvar('units', '', args, kwargs)
        self.printPosition = self.getvar('printPosition', '', args, kwargs)
        self.region = self.getvar('region', '', args, kwargs)
        self.publication = self.getvar('publication', '', args, kwargs)
        self.isPositionGuaranteed = self.getvar('isPositionGuaranteed', '', args, kwargs)
        self.includeInDigitalEdition = self.getvar('includeInDigitalEdition', '', args, kwargs)
        self.coverDate = self.getvar('coverDate', '', args, kwargs)
        self.saleDate = self.getvar('saleDate', '', args, kwargs)
        self.sizeNumCols = self.getvar('sizeNumCols', '', args, kwargs)
        self.sizeNumUnits = self.getvar('sizeNumUnits', '', args, kwargs)

        # validation
        if self.buyCategory not in self.possible_buy_categories_print:
            raise PATSException("Buy Category %s not valid." % self.buyCategory)

    def dict_repr(self, mode="buyer"):
        dict = super(InsertionOrderLineItemPrint, self).dict_repr(mode)
        printInsertion = {
                "size": self.size,
                "color": self.color,
                "printPosition": self.printPosition,
                "isPositionGuaranteed":self.isPositionGuaranteed,
                "includeInDigitalEdition": self.includeInDigitalEdition
        }
        if self.coverDate:
            printInsertion.update({
                "coverDate": self.coverDate.strftime("%Y-%m-%d")
            })
        if self.saleDate:
            printInsertion.update({
                "saleDate": self.saleDate.strftime("%Y-%m-%d")
            })
        if self.copyDeadline:
            printInsertion.update({
                "copyDeadline": self.copyDeadline.strftime("%Y-%m-%d")
            })
        if self.sizeNumCols:
            printInsertion.update({
                "sizeNumCols": self.sizeNumCols
            })
        if self.sizeNumUnits:
            printInsertion.update({
                "sizeNumUnits": self.sizeNumUnits
            })
        if self.units:
            dict.update({
                # digital has "unitAmount" but print has "units"
                "units": self.units
            })
            dict.update({
                "operation": self.operation,
            })
        dict.update({
            "publication": self.publication,
            "region": self.region,
            "printInsertion": printInsertion
        })
        return dict

class InsertionOrderLineItemDigital(InsertionOrderLineItem):
    # for validation
    # see http://developer.mediaocean.com/docs/read/publisher_orders_api/Order_API_seller_reference_data
    possible_buy_categories_online = [
        'Fee - Ad Serving', 'Fee - Ad Verification', 'Fee - Data', 'Fee - Mobile',
        'Fee - Privacy Icon', 'Fee - Production', 'Fee - Research', 'Fee - Search',
        'Fee - Sponsorship', 'Fee - Tax', 'Fee - Technology', 'Fee - Viewability',
        'Fee - Other',
        # confusion - buyer-side has "Display" and seller side has "Display Standard"
        # among other differences...
        'Display', 'Display Standard', 'Rich Media', 'Mobile', 'Video',
        'Package','Roadblock', 'Interstitial','In-Game',
        'Social', 'Sponsorship', 'Tablet', 'Text',
        'Custom-Other'
    ]
    #possible_servedby = [
    #    'Site',
    #    '3rd party',
    #    'Other'
    #]

    lineItemId = None # only used in revisions
    site = None # ": "thetimes.co.uk" ,
    unitAmount = None # "2000000",
    flightStart = None # "2015-02-01",
    flightEnd = None # "2015-02-28",
    dimensions = None #  "468x60",
    dimensionsPosition = None #  "Above the Fold",
    servedBy = None # "3rd party",
    primaryPlacement = None # True/False
    # needs to be its own object probably
    flighting = None #":[
    #    { "startDate":"2015-02-01", "endDate":"2015-02-28", "unitAmount":"2000000", "plannedCost":"30000.00" }
    #]

    def __init__(self, *args, **kwargs):
        super(InsertionOrderLineItemDigital, self).__init__(*args, **kwargs)
        self.lineItemId = self.getvar('lineItemId', None, args, kwargs)
        self.flightStart = self.getvar('flightStart', '', args, kwargs)
        self.flightEnd = self.getvar('flightEnd', '', args, kwargs)
        self.site = self.getvar('site', '', args, kwargs)
        self.dimensions = self.getvar('dimensions', '', args, kwargs)
        self.dimensionsPosition = self.getvar('dimensionsPosition', '', args, kwargs)
        self.servedBy = self.getvar('servedBy', '', args, kwargs)
        self.unitAmount = self.getvar('unitAmount', '', args, kwargs)
        self.flighting = self.getvar('flighting', '', args, kwargs)
        self.primaryPlacement = self.getvar('primaryPlacement', None, args, kwargs)

        # validation
        #if self.servedBy not in self.possible_servedby:
        #    raise PATSException("servedBy %s not valid." % self.servedBy)
        if self.buyCategory not in self.possible_buy_categories_online:
            raise PATSException("Buy Category %s not valid." % self.buyCategory)

    def dict_repr(self, mode="buyer"):
        dict = super(InsertionOrderLineItemDigital, self).dict_repr(mode)
        dict.update({
            "site": self.site,
            "dimensions": self.dimensions,
            "dimensionsPosition": self.dimensionsPosition,
            "servedBy": self.servedBy
        })
        # lineItemId only exists for revisions
        if mode == "seller" and self.lineItemId:
            dict.update({
                "lineItemId": self.lineItemId
            })
        # package children don't have dates, units or loads of other things
        if self.flightStart:
            dict.update({
                "flightStart": self.flightStart.strftime("%Y-%m-%d"),
            })
        if self.flightEnd:
            dict.update({
                "flightEnd": self.flightEnd.strftime("%Y-%m-%d"),
            })
        if self.unitAmount:
            dict.update({
                "unitAmount": self.unitAmount,
            })
        if self.rate:
            if mode == "buyer":
                dict.update({
                    "rate": "{0:.4f}".format(self.rate),
                })
            else:
                dict.update({
                    "rate": {
                        "amount": "{0:.4f}".format(self.rate),
                        "currencyCode": "GBP"
                    }
                })
        if self.plannedCost:
            if mode == "buyer":
                dict.update({
                    "plannedCost": "{0:.2f}".format(self.plannedCost),
                })
            else:
                dict.update({
                    "cost": {
                        "amount": "{0:.2f}".format(self.plannedCost),
                        "currencyCode": "GBP"
                    }
                })
        if self.primaryPlacement:
            dict.update({
                "primaryPlacement": self.primaryPlacement,
            })
        if self.flighting:
            flightingArray = []
            for flight in self.flighting:
                flightingArray.append(
                      {
                        "startDate":flight['startDate'].strftime("%Y-%m-%d"),
                        "endDate":flight['endDate'].strftime("%Y-%m-%d"),
                        "unitAmount":flight['unitAmount'],
                        "plannedCost":"{0:.2f}".format(flight['plannedCost'])
                      }
                )
            dict.update({
                "flighting": flightingArray
            })
        return dict

class ProposalLineItem(JSONSerializable):
    """
    This shouldn't be necessary - proposal line items should be the same as order ones.
    But for now this is necessary.
    """
    lineItemExternalId = None
    productId = None
    productName = None
    section = None
    subsection = None
    subMediaType = None
    unitType = None
    rate = None
    units = None
    costMethod = None
    buyCategory = None
    periods = []

    def __init__(self, *args, **kwargs):
        self.lineItemExternalId = kwargs.get('lineItemExternalId', '')
        self.productId = kwargs.get('productId', '')
        self.productName = kwargs.get('productName', '')
        self.section = kwargs.get('section', '')
        self.subsection = kwargs.get('subsection', '')
        self.subMediaType = kwargs.get('subMediaType', '')
        self.unitType = kwargs.get('unitType', '')
        self.rate = kwargs.get('rate', '')
        self.units = kwargs.get('units', '')
        self.costMethod = kwargs.get('costMethod', '')
        self.periods = kwargs.get('periods', [])

    def dict_repr(self):
        dict = {
            # called "externalPlacementId" for orders
            "lineItemExternalId":self.lineItemExternalId,
            # same in orders
            "productId":self.productId,
            "productName": self.productName,
            "section":self.section,
            "subsection":self.subsection,
            "subMediaType":self.subMediaType,
            "unitType":self.unitType,
            "rate":"{0:.4f}".format(self.rate),
            "units":self.units,
            "costMethod":self.costMethod,
        }
        if self.periods:
            dict.update({
                "periods":self.periods
            })
        return dict

    def getCost(self):
        # the weird proposal line item definition doesn't have a cost field, just rate and units.
        # so we have to calcuate it here to know what our value should be for testing purposes.
        cost = 0
        if self.costMethod == 'CPM':
            cost = self.units * self.rate / 1000
        elif self.costMethod == 'Flat':
            cost = self.rate
        else:
            cost = self.units * self.rate
        return cost

class ProposalLineItemDigital(ProposalLineItem):
    """
    Again, this shouldn't be necessary - get rid of it ASAP!
    """
    site = None
    dimensionsAndPosition = None
    flightStart = None
    flightEnd = None
    servedBy = None

    # for validation
    # see http://developer.mediaocean.com/docs/proposals_api/Proposals_API_reference_data#buy_categories
    possible_buy_categories_online = [
        'Display', 'RichMedia', 'Mobile', 'Video',
        'Interstitial','In-Game', 'Social', 'Sponsorship',
        'Tablet', 'Text', 'Custom-Other'
    ]
    possible_servedby = [
        'Site',
        '3rd party',
        'Other'
    ]

    def __init__(self, *args, **kwargs):
        super(ProposalLineItemDigital, self).__init__(*args, **kwargs)
        self.site = kwargs.get('site', '')
        self.buyCategory = kwargs.get('buyCategory', '')
        self.dimensionsAndPosition = kwargs.get('dimensionsAndPosition', '')
        self.flightStart = kwargs.get('flightStart', '')
        self.flightEnd = kwargs.get('flightEnd', '')
        self.servedBy = kwargs.get('servedBy', '')
        if self.buyCategory not in self.possible_buy_categories_online:
            raise PATSException("Buy Category %s not valid." % self.buyCategory)
        if self.servedBy not in self.possible_servedby:
            raise PATSException("servedBy %s not valid." % self.servedBy)

    def dict_repr(self, *args, **kwargs):
        dict = super(ProposalLineItemDigital, self).dict_repr(*args, **kwargs)
        dict.update({
            "site":self.site,
            "buyCategory":self.buyCategory,
            "dimensionsAndPosition":self.dimensionsAndPosition,
            "servedBy":self.servedBy,
            "flightStart":self.flightStart.strftime("%Y-%m-%d"),
            "flightEnd":self.flightEnd.strftime("%Y-%m-%d")
        })
        return dict

class ProposalLineItemPrint(ProposalLineItem):
    """
    Until we can share one line item class between both orders and proposals...
    """
    publication = None
    region = None
    size = None
    color = None
    position = None
    coverDate = None

    # for validation
    # should be in http://developer.mediaocean.com/docs/read/proposals_api/Proposals_API_reference_data
    # but they're not listed... raised as PATS-1035.
    #possible_buy_categories_print = [
    #    'Standard', 'RichMedia', 'Mobile', 'Video',
    #    'Interstitial','In-Game', 'Social', 'Sponsorship',
    #    'Tablet', 'Text', 'Custom-Other'
    #]

    def __init__(self, *args, **kwargs):
        super(ProposalLineItemPrint, self).__init__(*args, **kwargs)
        self.publication = kwargs.get('publication', '')
        self.buyCategory = kwargs.get('buyCategory', '')
        self.region = kwargs.get('region', '')
        self.size = kwargs.get('size', '')
        self.color = kwargs.get('color', '')
        self.position = kwargs.get('position', '')
        self.coverDate = kwargs.get('coverDate', '')
        #if self.buyCategory not in self.possible_buy_categories_print:
        #    raise PATSException("Buy Category %s not valid." % self.buyCategory)

    def dict_repr(self, *args, **kwargs):
        dict = super(ProposalLineItemPrint, self).dict_repr(*args, **kwargs)
        dict.update({
            "publication":self.publication,
            "buyCategory":self.buyCategory,
            "region":self.region,
            "size":self.size,
            "color":self.color,
            "position":self.position,
            "coverDate":self.coverDate.strftime("%Y-%m-%d"),
        })
        return dict
