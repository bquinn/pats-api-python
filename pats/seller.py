
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
from .core import PATSAPIClient

PUBLISHER_API_DOMAIN = 'demo-publishers.api.mediaocean.com'

class PATSSeller(PATSAPIClient):
    vendor_id = None

    def __init__(self, vendor_id=None, api_key=None):
        """
        Create a new seller-side PATS API object.

        Parameters:
        - vendor_id (required) : ID of the vendor (publisher) whose catalogue
          you are updating.
        - api_key (required) : API Key with seller access
        """
        super(PATSSeller, self).__init__(api_key)
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

    def view_orders(self, start_date=None, end_date=None):
        """
        As a seller, view all orders received from buyers.
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

    def view_order_detail(self, order_id=None):
        """
        As a seller, view all orders received from buyers.
        """
        if order_id == None:
            raise PATSException("order ID is required")
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v1+json'
        }
        js = self._send_request(
            "GET",
            PUBLISHER_API_DOMAIN,
            '/vendors/%s/orders/%s/history' % (self.vendor_id, order_id),
            extra_headers
        )
        # TODO: Parse the response and return something more intelligible
        return js

    def view_rfps(self, start_date=None, end_date=None):
        """
        As a seller, view all RFPs from buyers.
        """
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.rfps-v1+json'
        }
        path = '/vendors/%s/rfps' % self_vendor_id
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

    def view_proposals(self, rfp_id=None):
        """
        As a seller, show all existing proposals in response to a buyer's RFP.
        """
        if rfp_id == None:
            raise PATSException("RFP ID is required")

        extra_headers = {
            'Accept': 'application/vnd.mediaocean.proposals-v1+json'
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

        if kwargs.get('digital_line_items'):
            digital_line_items = []
            for line_item in kwargs['digital_line_items']:
                digital_line_items.append(line_item.dict_repr())
        if kwargs.get('print_line_items'):
            print_line_items = []
            for line_item in kwargs['print_line_items']:
                print_line_items.append(line_item.dict_repr())

        data = {
            "rfpPublicId": rfp_id,
            "vendorPublicId" : self.vendor_id,
            "proposalExternalId":proposal_external_id,
            "proposal": {
                "proposalExternalId": proposal_external_id, # why is this included twice??
                "comments" : comments,
                "digitalLineItems": digital_line_items,
                "printLineItems": print_line_items,
                "attachments" : attachments
            }
        }

        extra_headers = {
            'Accept': 'application/vnd.mediaocean.proposals-v1+json'
        }

        js = self._send_request(
            "POST",
            PUBLISHER_API_DOMAIN,
            "/vendors/%s/rfps/%s/proposals" % (self.vendor_id, rfp_id),
            extra_headers,
            data
        )
        # TODO: Parse the response and return something more intelligible
        return js

