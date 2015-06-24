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
PATS Python library - Seller side - Brendan Quinn Dec 2014

Based on Mediaocean PATS API documented at https://developer.mediaocean.com/
"""

from collections import OrderedDict
from httplib import HTTPSConnection
import json
import os
import re
import string
from urllib import urlencode
from .core import PATSAPIClient, PATSException, JSONSerializable

PUBLISHER_API_DOMAIN = 'demo-publishers.api.mediaocean.com'

class PATSSeller(PATSAPIClient):
    vendor_id = None

    def __init__(self, vendor_id=None, api_key=None, debug_mode=False):
        """
        Create a new seller-side PATS API object.

        Parameters:
        - vendor_id (required) : ID of the vendor (publisher) whose catalogue
          you are updating.
        - api_key (required) : API Key with seller access
        """
        super(PATSSeller, self).__init__(api_key, debug_mode)
        if vendor_id == None:
            raise PATSException("Vendor (aka publisher) ID is required")
        self.vendor_id = vendor_id

    def save_product_data(self, data=None): 
        """
        Save a new or updated product to a vendor's product catalogue.

        Parameters:
        - data (required) : Payload of the product(s) you are updating.
        """
        js = self._send_request(
            "POST",
            PUBLISHER_API_DOMAIN,
            "/vendors/%s/products/" % self.vendor_id,
            { 'Accept': 'application/vnd.mediaocean.catalog-v1+json' },
            json.dumps(data)
        )
        if js['validationResults']:
            raise PATSException("Product ID "+js['validationResults'][0]['productId']+": error is "+js['validationResults'][0]['message'])
        productId = js['products'][0]['productPublicId']
        return js

    def save_product(self, product_id, product_name, image_encoded,
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
                      "startDate":product_start_date.strftime("%Y-%m-%d"),
                      "endDate":product_end_date.strftime("%Y-%m-%d"),
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

        return self.save_product_data(data)

    def get_agency_by_id(self, agency_id=None, user_id=None, name=None, last_updated_date=None):
        """
        As a seller, view detail about the specified agency.
        BROKEN - bug no PATS-880
        """
        #if agency_id == None:
        #    raise PATSException("Agency ID is required")
        #if user_id == None:
        #    raise PATSException("User ID is required")

        extra_headers = {
            'Accept': 'application/vnd.mediaocean.security-v1+json',
            'X-MO-User-ID': user_id
        }
        path = '/agencies?agencyId=%s' % agency_id
        if last_updated_date:
            path += "&lastUpdatedDate="+last_updated_date.strftime("%Y-%m-%d")
        if name:
            path += "&name="+name
        js = self._send_request(
            "GET",
            PUBLISHER_API_DOMAIN,
            path,
            extra_headers
        )
        # TODO: Parse the response and return something more intelligible
        return js

    def get_agency_by_name(self, agency_name=None, user_id=None, last_updated_date=None):
        """
        As a seller, view detail about the specified agency.
        BROKEN - bug no PATS-880
        """
        if agency_name == None:
            raise PATSException("Agency name string is required")
        if user_id == None:
            raise PATSException("User ID is required")

        extra_headers = {
            'Accept': 'application/vnd.mediaocean.security-v1+json',
            'X-MO-User-ID': user_id
        }
        path = '/agencies?name=%s' % agency_name
        js = self._send_request(
            "GET",
            PUBLISHER_API_DOMAIN,
            path,
            extra_headers
        )
        # TODO: Parse the response and return something more intelligible
        return js

    def view_orders(self, start_date=None, end_date=None):
        """
        As a seller, view all order revisions that I have created.
        (Seems like an odd thing to want to do, this was supposed to be "view orders"
        but that doesn't actually exist yet!)
        """
        if start_date == None:
            raise PATSException("Start date is required")

        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v1+json'
        }

        path = '/vendors/%s/orders' % self.vendor_id
        if start_date and end_date:
            # not sure if you can have one or the other on its own?
            path += "?startDate=%s&endDate=%s" % (
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )
        js = self._send_request(
            "GET",
            PUBLISHER_API_DOMAIN,
            path,
            extra_headers
        )
        # TODO: Parse the response and return something more intelligible
        return js

    def view_order_detail(self, order_id=None, version=None):
        """
        As a seller, view detail of an order version.
        """
        if order_id == None:
            raise PATSException("order ID is required")
        if version == None:
            raise PATSException("version is required")
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v1+json'
        }
        js = self._send_request(
            "GET",
            PUBLISHER_API_DOMAIN,
            '/vendors/%s/orders/%s?version=%s' % (self.vendor_id, order_id, version),
            extra_headers
        )
        # TODO: Parse the response and return something more intelligible
        return js

    def view_order_history(self, order_id=None, full=False):
        """
        As a seller, view the full history (ie all old versions) of an order.
        """
        if order_id == None:
            raise PATSException("order ID is required")
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v1+json'
        }
        path = '/vendors/%s/orders/%s/history' % (self.vendor_id, order_id)
        if full:
            path += "?full=true"
        js = self._send_request(
            "GET",
            PUBLISHER_API_DOMAIN,
            path,
            extra_headers
        )
        return js
        
    def send_order_revision(self, order_id=None):
        # TODO - docs being released on 9 March apparently...
        if order_id == None:
            raise PATSException("order ID is required")
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v1+json'
        }
        pass

    def respond_to_order(self, user_id=None, order_id=None, status=None, comments=None):
        """
        As a seller, Accept or Reject an order from a buyer.
        """
        if user_id == None:
            raise PATSException("User ID (seller email) is required")
        if order_id == None:
            raise PATSException("Order ID is required")
        if status == None or status not in ("Accepted", "Rejected"):
            raise PATSException("status (\"Accepted\" or \"Rejected\") is required")
        if comments == None or comments == "":
            raise PATSException("comments are required for accepting or rejecting an order")

        extra_headers = {
            'X-MO-User-Id': user_id,
            'Accept': 'application/vnd.mediaocean.order-v1+json'
        }
        data = {
            "status": status,
            "comments": comments
        }

        js = self._send_request(
            "PUT",
            PUBLISHER_API_DOMAIN,
            '/vendors/%s/orders/%s/respond' % (self.vendor_id, order_id),
            extra_headers,
            json.dumps(data)
        )
        # Should parse the response and return something more intelligible
        return js

    def view_rfps(self, start_date=None, end_date=None):
        """
        As a seller, view all RFPs from buyers.
        """
        extra_headers = {
            # this will probably change to "rfps" soon to be consistent with other headers
            'Accept': 'application/vnd.mediaocean.rfp-v1+json'
        }
        path = '/vendors/%s/rfps?' % self.vendor_id
        if start_date:
            path += "startDate=%s" % start_date.strftime("%Y-%m-%d")
        if end_date:
            path += "&endDate=%s" % end_date.strftime("%Y-%m-%d")
        js = self._send_request(
            "GET",
            PUBLISHER_API_DOMAIN,
            path,
            extra_headers
        )
        # TODO: Parse the response and return something more intelligible
        return js

    def view_proposals(self, rfp_id=None):
        """
        As a seller, show all existing proposals in response to a buyer's RFP.
        """
        if rfp_id == None:
            raise PATSException("RFP ID is required")

        extra_headers = {
            'Accept': 'application/vnd.mediaocean.proposal-v1+json'
        }

        js = self._send_request(
            "GET",
            PUBLISHER_API_DOMAIN,
            "/vendors/%s/rfps/%s/proposals" % (self.vendor_id, rfp_id),
            extra_headers
        )
        # TODO: Parse the response and return something more intelligible
        return js

    def send_proposal(self, rfp_id=None, proposal_external_id=None, comments=None, digital_line_items=None, print_line_items=None, attachments=None):
        """
        As a seller, send a proposal in response to a buyer's RFP.
        """

        digital_line_items_obj = []
        if digital_line_items:
            for line_item in digital_line_items:
                digital_line_items_obj.append(line_item.dict_repr())
        print_line_items_obj = []
        if print_line_items:
            for line_item in print_line_items:
                print_line_items_obj.append(line_item.dict_repr())

        data = {
            "rfpPublicId": rfp_id,
            "proposal": {
                "proposalExternalId": proposal_external_id,
                "comments" : comments,
                "digitalLineItems": digital_line_items_obj,
                "printLineItems": print_line_items_obj,
                "attachments" : attachments
            }
        }

        extra_headers = {
            'Accept': 'application/vnd.mediaocean.proposal-v1+json'
        }

        js = self._send_request(
            "POST",
            PUBLISHER_API_DOMAIN,
            "/vendors/%s/proposals" % self.vendor_id,
            extra_headers,
            json.dumps(data)
        )
        if 'validationResult' in js and js['validationResult']['validationFailedDto'] != None:
            errorStr = "Create proposal failed:\n"
            for type in js['validationResult']:
                errors = js['validationResult'][type]
                if errors:
                    errorStr += type + ":\n"
                    for lineno in errors:
                        errorStr += "  line "+lineno+":\n"
                        for fielderror in errors[lineno]:
                            errorStr += "    " + fielderror['fieldName'] + ": " + fielderror['message'] + "\n"
            raise PATSException(errorStr)
        return js

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
    units = None
    subMediaType = None
    unitType = None
    rate = None
    costMethod = None

    def __init__(self, *args, **kwargs):
        self.lineItemExternalId = kwargs.get('lineItemExternalId', '')
        self.productId = kwargs.get('productId', '')
        self.productName = kwargs.get('productName', '')
        self.section = kwargs.get('section', '')
        self.subsection = kwargs.get('subsection', '')
        self.units = kwargs.get('units', '')
        self.subMediaType = kwargs.get('subMediaType', '')
        self.unitType = kwargs.get('unitType', '')
        self.rate = kwargs.get('rate', '')
        self.costMethod = kwargs.get('costMethod', '')

    def dict_repr(self):
        dict = {
            # called "externalPlacementId" for orders
            "lineItemExternalId":self.lineItemExternalId,
            # same in orders
            "productId":self.productId,
            "productName": self.productName,
            "section":self.section,
            "subsection":self.subsection,
            "units":self.units,
            "subMediaType":self.subMediaType,
            "unitType":self.unitType,
            "rate":self.rate,
            "costMethod":self.costMethod,
        }
        return dict

class ProposalLineItemDigital(ProposalLineItem):
    """
    Again, this shouldn't be necessary - get rid of it ASAP!
    """
    site = None
    buyCategory = None
    dimensionsAndPosition = None
    flightStart = None
    flightEnd = None

    # for validation
    possible_buy_categories_online = [
        'Display Standard', 'Rich Media', 'Mobile', 'Video', 'Package','Roadblock',
        'Interstitial','In-Game', 'Social', 'Sponsorship', 'Tablet', 'Text', 'Custom-Other'
    ]

    def __init__(self, *args, **kwargs):
        super(ProposalLineItemDigital, self).__init__(*args, **kwargs)
        self.site = kwargs.get('site', '')
        self.buyCategory = kwargs.get('buyCategory', '')
        self.dimensionsAndPosition = kwargs.get('dimensionsAndPosition', '')
        self.flightStart = kwargs.get('flightStart', '')
        self.flightEnd = kwargs.get('flightEnd', '')
        #if self.buyCategory not in self.possible_buy_categories_online:
        #    raise PATSException("Buy Category %s not valid." % self.buyCategory)

    def dict_repr(self, *args, **kwargs):
        dict = super(ProposalLineItemDigital, self).dict_repr(*args, **kwargs)
        dict.update({
            "site":self.site,
            "buyCategory":self.buyCategory,
            "dimensionsAndPosition":self.dimensionsAndPosition,
            "flightStart":self.flightStart.strftime("%Y-%m-%d"),
            "flightEnd":self.flightEnd.strftime("%Y-%m-%d")
        })
        return dict

class ProposalLineItemPrint(ProposalLineItem):
    pass