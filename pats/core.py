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

VERSION = '0.3'

class PATSException(Exception):
    pass

class PATSAPIClient(object):
    # controlled values for product catalogue
    possible_media_types = ['PRINT', 'DIGITAL']
    possible_media_subtypes_print = ['DISPLAY_PRINT', 'CLASSIFIED', 'INSERTS', 'PRINT_CUSTOM']
    possible_media_subtypes_digital = ['DISPLAY_DIGITAL', 'VIDEO', 'MOBILE', 'TABLET', 'APP']
    # "old" values pre April 2015
    possible_categories = ['ARTS_AND_ENTERTAINMENT','AUTOMOTIVE','BUSINESS','CAREERS','EDUCATION','FAMILY_AND_PARENTING','HEALTH_AND_FITNESS','FOOD_AND_DRINK','HOBBIES_AND_INTERESTS','HOME_AND_GARDEN','LAW_GOVERNMENT_AND_POLITICS','NEWS','PERSONAL_FINANCE','SOCIETY','SCIENCE','PETS','SPORTS','STYLE_AND_FASHION','TECHNOLOGY_AND_COMPUTING','TRAVEL','REAL_ESTATE','SHOPPING','RELIGION_AND_SPIRITUALITY','SOCIAL_MEDIA']
    # "new" values sent by Jon on 8 April 2015
    possible_categories = ['ARTS_AND_ENTERTAINMENT','BEAUTY_AND_FITNESS','BOOKS_AND_LITERATURE','BUSINESS_AND_INDUSTRIAL','COMPUTERS_AND_ELECTRONICS','FINANCE','FOOD_AND_DRINK','GAMES','HEALTH','HOBBIES_AND_LEISURE','HOME_AND_GARDEN','INTERNET_AND_TELECOM','JOBS_AND_EDUCATION','LAW_GOVT_AND_POLITICS_NEWS','ONLINE_COMMUNITIES','PEOPLE_AND_SOCIETY','PETS_AND_ANIMALS','REAL_ESTATE','REFERENCE','SCIENCE','SHOPPING','SPORTS','TRAVEL']
    # debugging mode flag
    debug_mode = False

    def __init__(self, api_key, debug_mode=False):
        """
        Initialize a PATS instance.
        """
        self.api_key = api_key
        if debug_mode:
            self.debug_mode = True

    def _get_headers(self, extra_headers):
        # Set User-Agent
        headers = {
            'User-Agent': "PATS Python Library/%s" % VERSION,
            'Content-Type': 'application/json',
            'X-MO-API-Key': self.api_key
        }
        headers.update(extra_headers)
        return headers

    def _send_request(self, method, domain, path, extra_headers, body=None):
        # Create the http object
        h = HTTPSConnection(domain)

        # uncomment this when things just aren't working...
        if self.debug_mode:
            h.set_debuglevel(10)

        # Perform the request and get the response headers and content
        headers = self._get_headers(extra_headers)
        h.request(method,
                  path,
                  body,
                  headers)
        response = h.getresponse()
        response_status = response.status
        response_text = response.read()

        if self.debug_mode:
            print "DEBUG: response status is %d, full response is" % response_status
            print response_text

        # Bad Request gives an error in text, not JSON
        if response_status == 400:
            self._relay_error(response_status, response_text)

        # 422 is "unprocessable entity" but more details are given in the JS response
        # so we should use that instead
        if response_status != 200 and response_status != 422:
            self._relay_error(response_status, response.reason)

        js = json.JSONDecoder().decode(response_text)

        if response_status == 422 and 'message' in js:
            self._relay_error(js['code'], js['message'])
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
                "%s Possibly invalid API key %s" % (reason, self.api_key))
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
            "orderNumber": self.order_number, 
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
    unitAmount = None # "2000000",
    plannedCost = None # "30000.00",
    unitType = None # "Impressions",
    section = None # "Sport",
    subsection = None # "Football",
    subMediaType = None #  "Display (Digital)",
    productId = None # "TIMESSPORTBANNER",
    buyCategory = None # "Standard",
    packageType = None # "Standalone",

    possible_operations = [
        'Add',
        'Update',
        'Delete'
    ]

    operation = 'Add'

    def __init__(self, *args, **kwargs):
        # we probably should generate this automatically? what happens to it as the order changes?
        self.lineNumber = kwargs.get('lineNumber', '')
        self.externalPlacementId = kwargs.get('externalPlacementId', '')
        self.lineItemExternalId = kwargs.get('lineItemExternalId', '')
        self.placementName = kwargs.get('placementName', '')
        self.costMethod = kwargs.get('costMethod', '')
        self.unitAmount = kwargs.get('unitAmount', '')
        self.plannedCost = kwargs.get('plannedCost', '')
        self.unitType = kwargs.get('unitType', '')
        self.section = kwargs.get('section', '')
        self.subsection = kwargs.get('subsection', '')
        self.subMediaType = kwargs.get('subMediaType', '')
        self.productId = kwargs.get('productId', '')
        self.buyCategory = kwargs.get('buyCategory', '')
        self.packageType = kwargs.get('packageType', '')

    def setOperation(self, operation):
        if operation not in self.possible_operations:
            raise PATSException('Operation %s should be one of %s' % (operation, ', '.join(self.possible_operations)))
        self.operation = operation

    def dict_repr(self):
        dict = {
            "operation": self.operation,
            "lineNumber": self.lineNumber,
            "externalPlacementId": self.externalPlacementId,
            "placementName": self.placementName,
            "costMethod": self.costMethod,
            "unitAmount": self.unitAmount,
            "plannedCost": self.plannedCost,
            "unitType": self.unitType,
            "section": self.section,
            "subsection": self.subsection,
            "subMediaType": self.subMediaType,
            "buyCategory": self.buyCategory,
        }
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
        return dict

class InsertionOrderLineItemPrint(InsertionOrderLineItem):
    # lineNumber, externalPlacementId, placementName, costMethod, plannedCost,
    # unitType, subMediaType, section, subsection, buyCategory, packageType, productId all handled in parent class

    # for validation
    possible_buy_categories_print = [
        'Magazine', 'Newspaper', 'Supplement', 'Consumer', 'Classified - National', 'Direct Mail',
        'Trade', 'Classified - Regional', 'Directories, i.e. Yellow Pages', 'Display – National',
        'Inserts', 'Display - Regional', 'Sponsorship'
    ]

    publication = None # "Time",
    # "printInsertion":{
    size = None # ":"25x4",
    rate = None # "15.00",
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
        self.publication = kwargs.get('publication', '')
        self.size = kwargs.get('size', '')
        self.color = kwargs.get('color', '')
        self.units = kwargs.get('units', '')
        self.rate = kwargs.get('rate', '')
        self.printPosition = kwargs.get('printPosition', '')
        self.positionName = kwargs.get('positionName', '')
        self.isPositionGuaranteed = kwargs.get('isPositionGuaranteed', '')
        self.includeInDigitalEdition = kwargs.get('includeInDigitalEdition', '')
        self.coverDate = kwargs.get('coverDate', None)
        self.saleDate = kwargs.get('saleDate', None)
        self.copyDeadline = kwargs.get('copyDeadline', None)
        self.sizeNumCols = kwargs.get('sizeNumCols', None)
        self.sizeNumUnits = kwargs.get('sizeNumUnits', None)
        #if self.buyCategory not in self.possible_buy_categories_print:
        #    raise PATSException("Buy Category %s not valid." % self.buyCategory)

    def dict_repr(self, *args, **kwargs):
        dict = super(InsertionOrderLineItemPrint, self).dict_repr(*args, **kwargs)
        printInsertion = {
                "size": self.size,
                "color": self.color,
                "printPosition": self.printPosition,
                "positionName": self.positionName,
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
        dict.update({
            "operation": self.operation,
            "publication": self.publication,
            # the parent class handles "unitAmount" but print has "units" differently
            "rate": self.rate,
            "units": self.units,
            "printInsertion": printInsertion
        })
        return dict

class InsertionOrderLineItemDigital(InsertionOrderLineItem):
    # for validation
    possible_buy_categories_online = [
        'Fee - Ad Serving', 'Fee - Ad Verification', 'Fee - Data', 'Fee - Mobile',
        'Fee - Privacy Icon', 'Fee - Production', 'Fee - Research', 'Fee - Search',
        'Fee - Sponsorship', 'Fee - Tax', 'Fee - Technology', 'Fee - Viewability',
        'Fee – Other',
        'Display Standard', 'Rich Media', 'Mobile', 'Video', 'Package','Roadblock',
        'Interstitial','In-Game', 'Social', 'Sponsorship', 'Tablet', 'Text', 'Custom-Other'
    ]

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
        if self.buyCategory not in self.possible_buy_categories_online:
            raise PATSException("Buy Category %s not valid." % self.buyCategory)

    def dict_repr(self):
        dict = super(InsertionOrderLineItemDigital, self).dict_repr()
        dict.update({
            "site": self.site,
            "rate": self.rate,
            "flightStart": self.flightStart.strftime("%Y-%m-%d"),
            "flightEnd": self.flightEnd.strftime("%Y-%m-%d"),
            "dimensions": self.dimensions,
            "dimensionsPosition": self.dimensionsPosition,
            "servedBy": self.servedBy,
            "bookingCategoryName": self.bookingCategoryName,
        })
        if self.flighting:
            flightingArray = []
            for flight in self.flighting:
                flightingArray.append(
                      {
                        "startDate":flight['startDate'].strftime("%Y-%m-%d"),
                        "endDate":flight['endDate'].strftime("%Y-%m-%d"),
                        "unitAmount":flight['unitAmount'],
                        "plannedCost":flight['plannedCost']
                      }
                )
            dict.update({
                "flighting": flightingArray
            })
        return dict
