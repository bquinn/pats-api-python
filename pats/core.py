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
import time
from urllib import urlencode

VERSION = '0.9' # update for 2016.1 APIs

RETRY_LIMIT = 3 # number of times to re-try HTTP requests if we get a gateway timeout error

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
             
        # Perform the request (with retries) and get the response headers and content
        retries = RETRY_LIMIT; response = ''; response_status = 0; response_text = ''
        for n in range(retries):
            h.request(method,
                  path,
                  body,
                  headers)
            
            response = h.getresponse()
            response_status = response.status
            response_text = response.read()
            if response_status == 504:
                # gateway timeout error: sleep then retry (up to retry limit)
                time.sleep(5)
            else:
                # go on
                break
        if self.raw_mode and self.session:
            self.session['response_status'] = response_status
            self.session['response_text'] = response_text

        if self.debug_mode:
            print "DEBUG: response status is %d, full response is" % response_status
            print response_text

        # Bad Request gives an error in text, not JSON
        if response_status == 400:
            self._relay_error(response_status, response_text)

        if response_status == 201:
            # 201 Created means we get the response as a Location: header
            if 'location' not in response.msg:
                self._relay_error(response_status, "Received 201 Created response but there's no Location: header. Response text is %s" % response_text)
            return response.msg['location']

        # 422 is "unprocessable entity" but more details are given in the JS response
        # so we should use that instead
        if response_status != 200 and response_status != 422:
            self._relay_error(response_status, response.reason + " " + response_text)

        js = None
        if response_text == '':
            return ''

        if response_status == 422:
            self._relay_error(response_status, response_text)

        js = json.JSONDecoder().decode(response_text)

        if response_status == 422:
            if 'message' in js:
                if 'code' in js:
                    code = js['code']
                else:
                    code = response_status
                self._relay_error(code, js['message'])
            else:
                # if we didn't get a JSON payload (eg Create RFP), just report the whole response
                self._relay_error(response_status, response_text)

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
                "Bad Request. The parameters you provided did not validate. Full response: %s" % reason)
        elif error_code == 401:
            raise PATSException(
                "%s (Possibly invalid API key %s)" % (reason, self.api_key))
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
    organisation_id = ''        # '35-IDSDKAD-7'
    agency_group_id = ''        # 'pats3'
    user_id = ''                # 'brenddlo'
    campaign_name = ''          # eg "BQ Monday test campaign 1"
    external_id = ''            # eg "BQMONDAYTEST1"
    start_date = ''             # eg "2015-02-01"
    end_date = ''               # eg "2015-02-28"
    advertiser_code = ''        # code of advertiser, eg "DEM"
    media_mix = []  # eg { "Media": [ { "MediaMix": "Online" }, { "MediaMix": "Print" } ] }
    campaign_budget = 0         # eg 1000000
    multi_currency = False      # flag that campaign can take non-GBP currencies

    def __init__(self, *args, **kwargs):
        self.organisation_id = kwargs.get('organisation_id', '')
        self.agency_group_id = kwargs.get('agency_group_id', '')
        self.user_id = kwargs.get('user_id', '')
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
        self.multi_currency = kwargs.get('multi_currency', False)
        self.external_id = kwargs.get('external_id', '')

    def dict_repr(self):
        dict = {
            "campaignName": self.campaign_name,
            "startDate": self.start_date.strftime("%Y-%m-%d"),
            "endDate": self.end_date.strftime("%Y-%m-%d"),
            "advertiser": self.advertiser_code,
            # update MediaBudget below
            "externalDetails": {
                "externalId": self.external_id
            },
            "multiCurrency": self.multi_currency
        }
        #if self.campaign_budget and (self.print_campaign_budget or self.digital_campaign_budget):
        #    raise PATSException("Campaign can't have both individual budgets and a campaign budget")
        # we want to end up with either
        # "MediaBudget": { "Medias": { "Media": [ { "MediaMix": "Online" }, {"MediaMix": "Print" } ] }, "CampaignBudget": 50000 }
        # or
        # "MediaBudget": { "Medias": { "Media": [ { "MediaMix": "Online", "Budget": 50000.00 } ] } }
        media_budget = {}
        if self.campaign_budget and self.campaign_budget > 0:
            media_budget.update({
                "campaignBudget": self.campaign_budget,
            })
        medias = []
        if self.print_campaign:
            print_campaign = {"mediaMix": "Print"}
            if self.print_campaign_budget and int(self.print_campaign_budget) > 0:
                print_campaign.update({"budget": self.print_campaign_budget})
            medias.append(print_campaign)
        if self.digital_campaign:
            digital_campaign = {"mediaMix": "Online"}
            if self.digital_campaign_budget  and int(self.digital_campaign_budget) > 0:
                digital_campaign.update({"budget": self.digital_campaign_budget})
            medias.append(digital_campaign)
        media_budget.update({ "medias": { "media": medias } })
        dict.update({'mediaBudget': media_budget})
        return dict
        
class LineItem(JSONSerializable):
    """
    Updated for 2016.1
    """
    id = None # PATS-generated ID for the line item
    externalId = None # Third-party ID for the line item
    referenceId = None # "ID used to link the line item to another line item that exists on a different resource (for example, a proposal, order, order revision, or product catalog), that the current line item is based on or related to in some way."
    lineNumber = None # read only.
    name = None # Name for the line item
    buyType = None # Display or Fee for digital. Magazine, Newspaper, Supplement, Print Fee for print
    buyCategory = None # Based on buyType - see list of values below
    packageType = None # (digital only?) must be Standalone Package Roadblock or Child for digital - or Standalone for print
    section = None # "Sport",
    subsection = None # "Football",
    units = 0
    unitType = None # must be "Actions" "Clicks" "Impressions" "Viewed Impressions" or "N/A" for digital, or "Columns by cms", "Insert" "NA" for print
    costMethod = None # "CPM", etc - see docs
    supplierPlacementParentReference = None # to group items together across orders (eg AccessOne)
    campaignId = None # Mediaocean campaign ID
    comments = None
    rate = 0.0 # dd.dddd,
    cost = 0.0 # dddd.dddd, (= units * rate based on costmethod, eg CPM is / 1000)
    mediaProperty = "" # site or publication

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
        self.id = self.getvar('id', None, args, kwargs)
        self.externalId = self.getvar('externalId', None, args, kwargs)
        self.referenceId = self.getvar('referenceId', None, args, kwargs)
        self.lineNumber = self.getvar('lineNumber', None, args, kwargs)
        self.name = self.getvar('name', '', args, kwargs)
        self.buyType = self.getvar('buyType', '', args, kwargs)
        self.buyCategory = self.getvar('buyCategory', '', args, kwargs)
        self.packageType = self.getvar('packageType', '', args, kwargs)
        self.section = self.getvar('section', '', args, kwargs)
        self.subsection = self.getvar('subsection', '', args, kwargs)
        self.unitType = self.getvar('unitType', None, args, kwargs)
        self.units = self.getvar('units', 0, args, kwargs)
        self.costMethod = self.getvar('costMethod', None, args, kwargs)
        self.rate = self.getvar('rate', 0.0, args, kwargs)
        self.cost = self.getvar('cost', 0.0, args, kwargs)
        self.comments = self.getvar('comments', '', args, kwargs)
        self.campaignId = self.getvar('campaignId', None, args, kwargs)
        self.supplierPlacementParentReference = self.getvar('supplierPlacementParentReference', None, args, kwargs)
        self.mediaProperty = self.getvar('mediaProperty', None, args, kwargs)

    def getPackageType(self):
        return None

    def dict_repr(self):
        dict = {
            "externalId": self.externalId,
            "name": self.name,
            "packageType": self.packageType,
            "comments": self.comments,
            "supplierPlacementParentReference": self.supplierPlacementParentReference,
            "mediaProperty": self.mediaProperty
        }
        packageType = self.getPackageType()
        if packageType != "Roadblock" and packageType != "Package":
            dict.update({
                "buyType": self.buyType,
                "buyCategory": self.buyCategory
            })
        if packageType != "Child":
            dict.update({
                "unitType": self.unitType,
                "costMethod": self.costMethod,
                "cost": round(self.cost,2),
                "units": self.units,
            })
            if self.buyType != "Print Fee": #  and self.buyType != "Fee":
                dict.update({
                    "rate": round(self.rate,4),
                })
        if self.id:
            dict.update({
                "id": self.id
            })
        if self.campaignId:
            dict.update({
                "campaignId": self.campaignId
            })
        if self.lineNumber:
            dict.update({
                "lineNumber": self.lineNumber,
            })
        if self.referenceId:
            dict.update({
                "referenceId": self.referenceId,
            })
        if self.buyType != "Print Fee" and self.buyType != "Fee":
            dict.update({
                "section": self.section,
                "subsection": self.subsection
            })
        return dict

class LineItemPrint(LineItem):
    # print only parameters
    color = None # must be "4 colour", "Black and White" or "Mono"
    coverDate = None
    saleDate = None
    position = None # could merge into generic?
    region = None

    # size : {
    size_type = None # "type of print size" - eg "cms"
    size_units =None # - no of units, eg for 25 x 4 would be 100
    size_columns = None # number of columns, eg for 25 x 4 would be 4
    # }

    # publication = None # duplicates mediaProperty?
    positionGuaranteed = None # optional - must be true or false
    includeInDigitalEdition = None # optional - must be true or false

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

    def __init__(self, *args, **kwargs):
        super(LineItemPrint, self).__init__(*args, **kwargs)
        # self.publication = self.getvar('publication', '', args, kwargs)
        self.size_type = self.getvar('size_type', '', args, kwargs)
        self.size_units = self.getvar('size_units', '', args, kwargs)
        self.size_columns = self.getvar('size_columns', '', args, kwargs)
        self.color = self.getvar('color', '', args, kwargs)
        self.coverDate = self.getvar('coverDate', '', args, kwargs)
        self.saleDate = self.getvar('saleDate', '', args, kwargs)
        self.position = self.getvar('position', '', args, kwargs)
        self.region = self.getvar('region', '', args, kwargs)
        self.positionGuaranteed = self.getvar('positionGuaranteed', False, args, kwargs)
        self.includeInDigitalEdition = self.getvar('includeInDigitalEdition', False, args, kwargs)

        # validation
        if self.buyCategory not in self.possible_buy_categories_print:
            raise PATSException("Placement %s: Buy Category %s not valid." % (self.name, self.buyCategory))
        if not self.saleDate and self.buyType != 'Print Fee':
            raise PATSException("Placement %s: saleDate is required" % (self.name))
        #if self.unitType == "Insert" and self.buyCategory != "Inserts":
        #    raise PATSException("For unitType Insert, buyCategory %s is not valid (must be Inserts)." % self.buyCategory)

    def dict_repr(self):
        dict = super(LineItemPrint, self).dict_repr()
        dict.update({
            'coverDate': self.coverDate.strftime("%Y-%m-%d"),
        })
        if self.buyType != "Print Fee":
            dict.update({
                'color': self.color,
                'size' : {
                    'type': self.size_type,
                },
                'saleDate': self.saleDate.strftime("%Y-%m-%d"),
                'positionGuaranteed': self.positionGuaranteed,
                'includeInDigitalEdition': self.includeInDigitalEdition,
                'position': self.position,
                'region': self.region
            })
            if self.size_units:
                dict['size'].update({
                    'units': self.size_units,
                    'columns': self.size_columns
                })
        return dict

class LineItemDigital(LineItem):
    # digital only
    parentExternalId = None # optional ID used to link a child line item with its parent package header. 
    primaryPlacement = None # true or false
    servedBy = None
    dimensions = None
    position = None
    target = None
    creativeType = None
    flightStartDate = None
    flightEndDate = None
    flighting = None # [ { month, year, units }]

    # for validation
    # see http://developer.mediaocean.com/docs/buyer_orders/Buyer_orders_ref#buy_categories
    possible_buy_categories_digital = [
        'Ad Serving', 'Ad Verification', 'Data', 'Mobile',
        'Privacy Icon', 'Production', 'Research', 'Search',
        'Sponsorship', 'Tax', 'Technology', 'Viewability',
        'Other',
        # confusion - buyer-side has "Display" and seller side has "Display Standard"
        # among other differences...
        'Standard', 'Rich Media', 'Mobile', 'Video',
        'Package','Roadblock', 'Interstitial','In-Game',
        'Social', 'Sponsorship', 'Tablet', 'Text',
        'Custom-Other'
    ]
    possible_servedby = [
        'Site',
        '3rd party',
        'Other'
    ]

    possible_package_types = [
        'Package',
        'Roadblock',
        'Child',
        'Standalone'
    ]

    possible_creative_types = [
        'GIF',
        'Flash',
        'Rich Media',
        'Other'
    ]
    def __init__(self, *args, **kwargs):
        super(LineItemDigital, self).__init__(*args, **kwargs)

        self.flightStartDate = self.getvar('flightStartDate', '', args, kwargs)
        self.flightEndDate = self.getvar('flightEndDate', '', args, kwargs)
        self.parentExternalId = self.getvar('parentExternalId', None, args, kwargs)
        self.primaryPlacement = self.getvar('primaryPlacement', False, args, kwargs)
        self.dimensions = self.getvar('dimensions', '', args, kwargs)
        self.position = self.getvar('position', '', args, kwargs)
        self.servedBy = self.getvar('servedBy', None, args, kwargs)
        self.target = self.getvar('target', None, args, kwargs)
        self.creativeType = self.getvar('creativeType', None, args, kwargs)
        self.flighting = self.getvar('flighting', None, args, kwargs)

        # validation
        #if self.servedBy not in self.possible_servedby:
        #    raise PATSException("Placement %s: servedBy %s not valid." % (self.name, self.servedBy))
        if self.buyCategory not in self.possible_buy_categories_digital and self.packageType != "Package" and self.packageType != "Roadblock":
            raise PATSException("Placement %s: Buy Category %s not valid." % (self.name, self.buyCategory))
        #if self.creativeType not in self.possible_creative_types and self.packageType != "Package":
        #    raise PATSException("Placement %s: creativeType %s not valid." % (self.name, self.creativeType))
        # We have groupName for revisions but packageName for proposals...
        #if self.packageType in ('Package', 'Roadblock', 'Child') and self.groupName == None:
        #    raise PATSException("Placement %s: Group Name required for package type %s" % (self.name, self.packageType))

    def getPackageType(self):
        return self.packageType

    def dict_repr(self):
        dict = super(LineItemDigital, self).dict_repr()
        dict.update({
            "primaryPlacement": self.primaryPlacement
        })
        if self.getPackageType() != "Package" and self.getPackageType() != "Roadblock":
            dict.update({
                "servedBy": self.servedBy,
                "target": self.target,
                "creativeType": self.creativeType,
            })
        if self.buyType != "Fee" and self.packageType != "Roadblock" and self.packageType != "Package":
            dict.update({
                "dimensions": self.dimensions,
                "position": self.position
            })
        if self.getPackageType() == "Child":
            dict.update({
                "parentExternalId": self.parentExternalId
            })
        else:
            # not a package child so it has a flight start and end date
            if isinstance(self.flightStartDate, datetime.date):
                dict.update({
                    "flightStartDate": self.flightStartDate.strftime("%Y-%m-%d"),
                    "flightEndDate": self.flightEndDate.strftime("%Y-%m-%d"),
                })
            else:
                # this is the case when we're turning a proposal into an order - we just have YYYY-MM-DD dates
                dict.update({
                    "flightStartDate": self.flightStartDate,
                    "flightEndDate": self.flightEndDate
                })
        if self.flighting:
            dict.update({
                "flighting": self.flighting
            })
        return dict

class InsertionOrderLineItemDigital(LineItemDigital):
    pass

class ProposalLineItemDigital(LineItemDigital):
    pass

class InsertionOrderLineItemPrint(LineItemPrint):
    pass

class ProposalLineItemPrint(LineItemPrint):
    pass
