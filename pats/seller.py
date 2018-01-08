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
import json
import os
import re
import string
from .core import PATSAPIClient, PATSException, JSONSerializable, Product

PUBLISHER_API_DOMAIN = 'demo-publishers.api.mediaocean.com'

class PATSSeller(PATSAPIClient):
    vendor_id = None
    user_id = None

    def __init__(self, vendor_id=None, api_key=None, user_id=None, debug_mode=False, raw_mode=False, session=None):
        """
        Create a new seller-side PATS API object.

        Parameters:
        - vendor_id (required) : ID of the vendor (publisher) on whose behalf you are making the call.
        - user_id (required) : Email of a valid user who is making the request
        - api_key (required) : API Key with seller access
        - debug_mode (boolean) : Output full details of HTTP requests and responses
        - raw_mode (boolean) : Store output of request (as 'curl' equivalent) and
                               response (JSON payload) when making requests
        - session (optional) : User session in which to write curl and response objects in raw mode
        """
        super(PATSSeller, self).__init__(api_key, debug_mode, raw_mode, session)
        if vendor_id == None:
            raise PATSException("Vendor (aka publisher) ID is required")
        self.vendor_id = vendor_id

        if user_id == None:
            raise PATSException("User ID (email address) is required")
        self.user_id = user_id

    def save_product_data(self, data=None): 
        """
        Save a new or updated product to a vendor's product catalogue.

        Parameters:
        - data (required) : Payload of the product(s) you are updating.

        http://developer.mediaocean.com/docs/read/catalog_api/Save_digital_products_to_catalog
        http://developer.mediaocean.com/docs/read/catalog_api/Save_print_products_to_catalog
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

        return self.save_product_data(data)

    def get_media_property_details(self, user_id=None, organisation_id=None):
        """
        New in 2016.3 - get media property fields

        https://developer.mediaocean.com/docs/read/catalog_api/Get_media_property_details
        """
        if organisation_id == None:
            organisation_id = self.vendor_id
        if user_id == None:
            user_id = self.user_id
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.catalog-v1+json',
            'X-MO-User-ID': user_id,
            'X-MO-Organization-ID': self.vendor_id,
            'X-MO-App': 'pats'
        }
        # a publisher can query another publisher's properties if they are allowed
        path = '/vendors/%s/mediaproperties/fields' % organisation_id
        js = self._send_request(
            "GET",
            PUBLISHER_API_DOMAIN,
            path,
            extra_headers
        )
        return js

    def update_media_property_fields(self, user_id=None, organisation_id=None, media_property_id=None, field_family=None, payload=None):
        """
        New in 2016.3 - update media property fields (for a given field family)

        https://developer.mediaocean.com/docs/catalog_api/Update_media_property_seller
        """
        if organisation_id == None:
            organisation_id = self.vendor_id
        if media_property_id == None:
            raise PATSException("media_property_id is required")
        if field_family == None:
            raise PATSException("field_family is required")
        if user_id == None:
            user_id = self.user_id
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.catalog-v1+json',
            'X-MO-User-ID': user_id,
            'X-MO-Organization-ID': self.vendor_id,
            'X-MO-App': 'pats'
        }
        # can a publisher update another publisher's properties if they want...? TODO check permissions
        path = '/vendors/%s/mediaproperties/%s/%s' % (organisation_id, media_property_id, field_family)
        js = self._send_request(
            "PUT",
            PUBLISHER_API_DOMAIN,
            path,
            extra_headers,
            json.dumps(payload)
        )
        return js

    def list_products(self, user_id=None, organisation_id=None):
        """
        New in 2016.3 - get products for seller

        https://developer.mediaocean.com/docs/catalog_api/Get_products_seller
        """
        # "organisation_id" is the one being requested - technically one vendor could
        # request products from another vendor
        if organisation_id == None:
            organisation_id = self.vendor_id
        if user_id == None:
            user_id = self.user_id
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.catalog-v1+json',
            'X-MO-User-ID': user_id,
            'X-MO-Organization-ID': self.vendor_id,
            'X-MO-App': 'pats'
        }
        # a publisher can query another publisher's properties if they want...
        path = '/vendors/%s/products' % organisation_id
        js = self._send_request(
            "GET",
            PUBLISHER_API_DOMAIN,
            path,
            extra_headers
        )
        return js

    def create_product(self, user_id=None, organisation_id=None, product=None, products=None):
        """
        New in 2016.3 - create product for seller

        https://developer.mediaocean.com/docs/catalog_api/Create_products_seller

        Can pass either "product" (a single Product) or "products" (an array of Products)
        """
        if organisation_id == None:
            organisation_id = self.vendor_id
        if user_id == None:
            user_id = self.user_id
        if type(product) != Product:
            user_id = self.user_id
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.catalog-v1+json',
            'X-MO-User-ID': user_id,
            'X-MO-Organization-ID': self.vendor_id,
            'X-MO-App': 'pats'
        }
        # the product data to be updated
        data = ''
        if product:
            data = [ product.dict_repr() ]
        elif products:
            data = products.dict_repr()
        else:
            raise PATSException('Either a single "product" or an array of "products" is required')

        path = '/vendors/%s/products' % (organisation_id)

        js = self._send_request(
            "POST",
            PUBLISHER_API_DOMAIN,
            path,
            extra_headers,
            json.dumps(data)
        )
        # this method returns 200 OK for anything :-( Raised bug PATS-1248
        # success looks like: [{"index":0,"status":"SUCCESS","id":"874a21af-6cef-42e4-933e-c57a3162c9cb"}]
        # failure looks like: [{"index":0,"status":"FAILURE","errors":[{"field":"mediaPropertyId","key":"productMediaPropertyIdInvalid_validation_message"}]}]
        # so we have to catch errors ourselves...
        if js[0]['status'] == "FAILURE":
            error_string = "Error: "
            errors = []
            for error in js[0]['errors']:
                error_string = ''
                if 'field' in error:
                    error_string += error['field']+": "
                error_string += error['key']
                errors.append(error_string)
            full_error_string = ','.join(errors)
            raise PATSException(full_error_string)
        else:
            return js[0]['id']

    def update_product(self, user_id=None, organisation_id=None, product_id=None, product=None):
        """
        New in 2016.3 - update product for seller

        https://developer.mediaocean.com/docs/catalog_api/Update_product_seller
        """
        if organisation_id == None:
            organisation_id = self.vendor_id
        if user_id == None:
            user_id = self.user_id
        if product_id == None:
            raise PATSException("Product ID is required")
        if type(product) != Product:
            user_id = self.user_id
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.catalog-v1+json',
            'X-MO-User-ID': user_id,
            'X-MO-Organization-ID': self.vendor_id,
            'X-MO-App': 'pats'
        }
        # the product data to be updated
        data = product.dict_repr()

        # a publisher can query another publisher's properties if they want...
        path = '/vendors/%s/products/%s' % (organisation_id, product_id)

        js = self._send_request(
            "PUT",
            PUBLISHER_API_DOMAIN,
            path,
            extra_headers,
            json.dumps(data)
        )
        return js

    def get_buyers(self, user_id=None, agency_id=None, name=None, last_updated_date=None):
        """
        As a seller user, list the details of all agencies I can receive orders from.

        http://developer.mediaocean.com/docs/read/organization_api/Get_agency
        """
        if user_id == None:
            user_id = self.user_id
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.security-v1+json',
            'X-MO-Organization-Id': self.vendor_id,
            'X-MO-User-ID': user_id
        }
        path = '/agencies?'
        if agency_id:
            path += "agencyId=%s" % agency_id
        if name:
            path += "&name=%s" % name
        if last_updated_date:
            path += "&updatedAfter=%s" % last_updated_date
        js = self._send_request(
            "GET",
            PUBLISHER_API_DOMAIN,
            path,
            extra_headers
        )
        return js

    def list_orders(self, since_date=None, page_size=25, page=1):
        """
        As a seller, view all orders that are available to me.
        Now using v2 API which gives custom fields (eg copy splits)

        http://developer.mediaocean.com/docs/read/seller_orders/Find_orders_seller
        """
        if since_date == None:
            raise PATSException("Since date is required")

        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v2+json',
            'X-MO-Organization-Id': self.vendor_id,
            'X-MO-User-Id': self.user_id,
            'X-MO-App': 'pats'
        }

        path = '/orders?since=%s&size=%s&page=%s' % (since_date.strftime("%Y-%m-%d"), page_size, page)
        js = self._send_request(
            "GET",
            PUBLISHER_API_DOMAIN,
            path,
            extra_headers
        )
        # TODO: Parse the response and return something more intelligible
        return js

    def list_all_orders(self, since_date=None):
        """
        Loop over the list_orders method until we definitely have all orders in an array
        """
        page_size = 25
        page = 1
        full_json_list = []
        remaining_content = True 
        while (remaining_content):
            partial_json_list = self.list_orders(since_date=since_date, page_size=page_size, page=page)
            full_json_list.extend(partial_json_list)
            page = page + 1
            remaining_content = (len(partial_json_list) == page_size)

        return full_json_list

    def list_order_versions(self, campaign_id=None, order_id=None, user_id=None, vendor_id=None):
        """
        As a seller, view a list of all versions of an order
        Now using v2 of the API which gives custom fields eg copy splits

        http://developer.mediaocean.com/docs/seller_orders/List_order_versions_seller
        """
        if campaign_id == None:
            raise PATSException("Campaign ID is required")
        if order_id == None:
            raise PATSException("Order ID is required")
        if user_id == None:
            user_id = self.user_id
        if vendor_id == None:
            vendor_id = self.vendor_id
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v2+json',
            'X-MO-Organization-Id': vendor_id,
            'X-MO-User-Id': self.user_id,
            'X-MO-App': 'pats'
        }
        js = self._send_request(
            "GET",
            PUBLISHER_API_DOMAIN,
            '/orders/%s/versions' % order_id,
            extra_headers
        )
        return js

    def view_order_version_detail(self, campaign_id=None, order_id=None, version=None):
        """
        As a seller, view detail of a particular (major) version of an order.

        http://developer.mediaocean.com/docs/read/seller_orders/Get_order_version_details_seller
        """
        if campaign_id == None:
            raise PATSException("Campaign ID is required")
        if order_id == None:
            raise PATSException("Order ID is required")
        if version == None:
            raise PATSException("Version is required")
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v2+json',
            'X-MO-Organization-Id': self.vendor_id,
            'X-MO-User-Id': self.user_id,
            'X-MO-App': 'pats'
        }
        js = self._send_request(
            "GET",
            PUBLISHER_API_DOMAIN,
            #'/vendors/%s/orders/%s?version=%s' % (self.vendor_id, order_id, version),
            '/orders/%s/versions/%s' % (order_id, version),
            extra_headers
        )
        return js

    def list_order_revisions(self, campaign_id=None, order_id=None, version=None, user_id=None, vendor_id=None):
        """
        As a seller, view a list of all revisions of a given version of an order

        http://developer.mediaocean.com/docs/seller_orders/List_order_revs_seller
        """
        #if campaign_id == None:
        #    raise PATSException("Campaign ID is required")
        if order_id == None:
            raise PATSException("Order ID is required")
        if version == None:
            raise PATSException("Order version is required")
        if user_id == None:
            user_id = self.user_id
        if vendor_id == None:
            vendor_id = self.vendor_id
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v2+json',
            'X-MO-Organization-Id': vendor_id,
            'X-MO-User-Id': self.user_id,
            'X-MO-App': 'pats'
        }
        js = self._send_request(
            "GET",
            PUBLISHER_API_DOMAIN,
            '/orders/%s/versions/%s/revisions' % (order_id, version),
            extra_headers
        )
        return js

    def view_order_revision_detail(self, order_id=None, version=None, revision=None):
        """
        As a seller, view detail of a particular revision of a version of an order.
        Now using v2 of the API which returns custom fields eg copy splits.

        https://developer.mediaocean.com/docs/read/seller_orders/Get_order_rev_details_seller
        """
        if order_id == None:
            raise PATSException("Order ID is required")
        if version == None:
            raise PATSException("Version is required")
        if revision == None:
            raise PATSException("Revision is required")
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v2+json',
            'X-MO-Organization-Id': self.vendor_id,
            'X-MO-User-Id': self.user_id,
            'X-MO-App': 'pats'
        }
        js = self._send_request(
            "GET",
            PUBLISHER_API_DOMAIN,
            '/orders/%s/versions/%s/revisions/%s' % (order_id, version, revision),
            extra_headers
        )
        return js

    def list_order_events(self, order_id=None):
        """
        As a seller, view the event history (ie all changes) of an order.
        Now using v2 of the API which returns custom fields eg copy splits.

        full (True/False): if True, returns the complete order history including all line items for each version.

        http://developer.mediaocean.com/docs/read/seller_orders/Get_order_events_seller
        """
        if order_id == None:
            raise PATSException("order ID is required")
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v2+json',
            'X-MO-Organization-Id': self.vendor_id,
            'X-MO-User-ID': self.user_id,
            'X-MO-App': 'pats'
        }
        path = '/orders/%s/events' % order_id
        js = self._send_request(
            "GET",
            PUBLISHER_API_DOMAIN,
            path,
            extra_headers
        )
        return js

    def get_order_attachment(self, vendor_id=None, user_id=None, order_id=None, attachment_id=None):
        """
        Get an attachment for an order (including the PDF of the order itself).
        Now using v2 of the API which returns custom fields eg copy splits (although what does that mean for attachments?!)

        https://developer.mediaocean.com/docs/read/seller_orders/Get_order_attachment_seller
        """
        if vendor_id==None:
            vendor_id=self.vendor_id # default but can be overridden
        if user_id == None:
            user_id = self.user_id
        if order_id == None:
            raise PATSException("Order ID is required")
        if attachment_id == None:
            raise PATSException("Attachment ID is required")
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v2+json',
            'X-MO-Organization-Id': vendor_id,
            'X-MO-User-Id': user_id,
            'X-MO-App': 'pats'
        }
        js = self._send_request(
            "GET",
            PUBLISHER_API_DOMAIN,
            "/orders/%s/attachments/%s" % (order_id, attachment_id),
            extra_headers
        )
        return js
        
    def send_order_revision(self, order_id=None, version=None, user_id=None, comment=None,
                            print_line_items=None, digital_line_items=None, barter_detail=None):
        """
        Send a revision (ie a proposed new version) of an order back to the buyer.
        Must always be in response to a sent order.
        order_id: order that is being revised ("public ID" eg O-KVG)
        barter_detail: new barter detail, if different.
        user_id: seller username who is sending the revision
        print_line_items / digital_line_items (one only):
            array of InsertionOrderLineItemPrint or InsertionOrderLineItemDigital objects.

        http://developer.mediaocean.com/docs/read/seller_orders/Send_order_revision_seller
        """
        if order_id == None:
            raise PATSException("order ID is required")
        if version == None:
            raise PATSException("version is required")

        data = {
            'comment': comment
        }
        if barter_detail:
            data.update({
                "barterDetail": barter_detail
            })
        digital_line_items_obj = []
        if digital_line_items:
            for line_item in digital_line_items:
                digital_line_items_obj.append(line_item.dict_repr())
            data.update({
                "digitalLineItems": digital_line_items_obj
            })
        print_line_items_obj = []
        if print_line_items:
            for line_item in print_line_items:
                print_line_items_obj.append(line_item.dict_repr())
            data.update({
                "printLineItems": print_line_items_obj
            })

        return self.send_order_revision_raw(order_id=order_id, version=version, user_id=user_id, data=data)

    def send_order_revision_raw(self, vendor_id=None, order_id=None, version=None, user_id=None, data=None):
        """
        Send a revision (ie a proposed new version) of an order back to the buyer.
        Must always be in response to a sent order.
        Now using v2 of the API which allows custom fields eg copy splits.

        Paramaters:
        order_id: the order to which this revision is being sent (always the most recent version)
        user_id (optional): the PATS username for the user sending the revision.
        data: raw payload of order contents, including line items.

        http://developer.mediaocean.com/docs/read/seller_orders/Send_order_revision_seller
        """
        if vendor_id==None:
            vendor_id=self.vendor_id # default but can be overridden
        if order_id == None:
            raise PATSException("Order ID is required")
        if version == None:
            raise PATSException("version is required")
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v2+json'
        }
        if user_id:
            extra_headers.update({
                'X-MO-User-Id': user_id,
                'X-MO-Organization-Id': vendor_id,
                'X-MO-App': 'pats'
            })

        path = '/orders/%s/versions/%s/revisions?operation=send' % (order_id, version)

        # send request - as it returns 201 Created on success, _send_request parses out the Location header and returns the full location
        order_uri = self._send_request(
            "POST",
            PUBLISHER_API_DOMAIN,
            path,
            extra_headers,
            json.dumps(data)
        )
        match = re.search('https?://(.+)?/orders/(.+?)/versions/(.+?)/revisions/(.+?)$', order_uri)
        revision_id = None
        if match:
            revision_number = int(match.group(4))
        return revision_number

    def respond_to_order(self, user_id=None, order_id=None, version=None, response=None, comment=None,
                         email=None, title=None, phone=None, signature=None):
        """
        As a seller, Accept or Reject an order from a buyer.
        Uses v2 of the API but that doesn't actualy seem to be different for this endpoint.

        https://developer.mediaocean.com/docs/seller_orders/Respond_to_order_seller
        https://developer.mediaocean.com/docs/seller_orders/Seller_orders_ref#order_response
        """
        if user_id == None:
            raise PATSException("User ID (seller email) is required")
        if order_id == None:
            raise PATSException("Order ID is required")
        if response == None or response not in ("accept", "reject"):
            raise PATSException("response (\"accept\" or \"reject\") is required")
        if comment == None or comment == "":
            raise PATSException("comment is required for accepting or rejecting an order")

        extra_headers = {
            'X-MO-User-Id': user_id,
            'X-MO-Organization-Id': self.vendor_id,
            'Accept': 'application/vnd.mediaocean.order-v2+json',
            'X-MO-App': 'pats'
        }
        data = {
            "comment": comment
        }
        if email:
            data.update({
                'email': email
            })
        if title:
            data.update({
                'title': title
            })
        if phone:
            data.update({
                'phone': phone
            })
        if signature:
            data.update({
                'signature': signature
            })

        js = self._send_request(
            "POST",
            PUBLISHER_API_DOMAIN,
            '/orders/%s/versions/%s?operation=%s' % (order_id, version, response),
            extra_headers,
            json.dumps(data)
        )
        return js

    def compare_order_versions(self, user_id=None, order_id=None, majorVersion=None, minorVersion=None):
        """
        Return difference between the specified version and the previous version.
        Note that this API is still on order-v1.

        https://developer.mediaocean.com/docs/read/seller_orders/Compare_order_seller
        """
        if user_id == None:
            raise PATSException("User ID (seller email) is required")
        if order_id == None:
            raise PATSException("Order ID is required")
        if vendor_id == None:
            vendor_id = self.vendor_id
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v1+json',
            'X-MO-Organization-Id': vendor_id,
            'X-MO-User-Id': self.user_id,
            'X-MO-App': 'pats'
        }
        path = '/orders/%s?operation=compareToPrevious' % order_id
        if start_date:
            path += "startDate=%s" % start_date.strftime("%Y-%m-%d")
        if end_date:
            path += "&endDate=%s" % end_date.strftime("%Y-%m-%d")

    def list_rfps(self, start_date=None, end_date=None, page_size=None, page=None):
        """
        As a seller, view all RFPs from buyers.
        Uses v2 of the API which includes custom columns such as copySplit.

        https://developer.mediaocean.com/docs/read/seller_proposals/Find_RFPs
        """
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.rfp-v2+json',
            'X-MO-Organization-Id': self.vendor_id,
            'X-MO-User-Id': self.user_id,
            'X-MO-App': 'pats'
        }
        path = '/rfps?' 
        if start_date:
            path += "startDate=%s" % start_date.strftime("%Y-%m-%d")
        if end_date:
            path += "&endDate=%s" % end_date.strftime("%Y-%m-%d")
        if page_size:
            path += "&page_size=%s" % page_size
        if page:
            path += "&page=%s" % page
        js = self._send_request(
            "GET",
            PUBLISHER_API_DOMAIN,
            path,
            extra_headers
        )
        return js

    def list_all_rfps(self, start_date=None, end_date=None):
        """
        Loop over the list_rfps method until we definitely have all RFPs in an array
        """
        page_size = 25
        page = 1
        full_json_list = []
        remaining_content = True
        while (remaining_content):
            partial_json_list = self.list_rfps(start_date=start_date, end_date=end_date, page_size=page_size, page=page)
            full_json_list.extend(partial_json_list)
            page = page + 1
            remaining_content = (len(partial_json_list) == page_size)

        return full_json_list

    def find_proposals(self, blah):
        # https://developer.mediaocean.com/docs/read/seller_proposals/Find_proposals
        # TODO
        pass

    def list_proposals(self, rfp_id=None):
        """
        As a seller, show all existing proposals in response to a buyer's RFP.
        Uses v2 of the API which allows custom fields such as copySplit.

        https://developer.mediaocean.com/docs/read/seller_proposals/List_proposals
        """
        if rfp_id == None:
            raise PATSException("RFP ID is required")

        extra_headers = {
            'Accept': 'application/vnd.mediaocean.proposal-v2+json',
            'X-MO-Organization-Id': self.vendor_id,
            'X-MO-User-Id': self.user_id,
            'X-MO-App': 'pats'
        }

        js = self._send_request(
            "GET",
            PUBLISHER_API_DOMAIN,
            "/rfps/%s/proposals" % rfp_id,
            extra_headers
        )
        return js

    def view_proposal(self, rfp_id=None, proposal_id=None):
        """
        As a seller, show the detail of one proposal in response to a buyer's RFP.
        Uses v2 of the API which allows custom fields such as copySplit.

        https://developer.mediaocean.com/docs/read/seller_proposals/Get_proposal_details
        """
        if rfp_id == None:
            raise PATSException("RFP ID is required")
        if proposal_id == None:
            raise PATSException("Proposal ID is required")

        extra_headers = {
            'Accept': 'application/vnd.mediaocean.proposal-v2+json',
            'X-MO-Organization-Id': self.vendor_id,
            'X-MO-User-Id': self.user_id,
            'X-MO-App': 'pats'
        }

        js = self._send_request(
            "GET",
            PUBLISHER_API_DOMAIN,
            "/proposals/%s" % proposal_id,
            extra_headers
        )
        return js

    def view_proposal_events(self, blah):
        # TODO
        # https://developer.mediaocean.com/docs/read/seller_proposals/Get_proposal_events
        pass

    def send_proposal_line_item_message(self, blah):
        # TODO
        # https://developer.mediaocean.com/docs/read/seller_proposals/Send_proposal_line_item_message
        pass

    def get_proposal_line_item_message(self, blah):
        # TODO
        # https://developer.mediaocean.com/docs/read/seller_proposals/Get_proposal_lineitem_messages
        pass

    def send_supplier_delivery_stats(self, blah):
        # TODO
        # https://developer.mediaocean.com/docs/read/seller_orders/Send_supplier_delivery_seller
        pass

    def get_supplier_delivery_status(self, blah):
        # TODO
        # https://developer.mediaocean.com/docs/read/seller_orders/Supplier_delivery_status_seller
        pass

    def view_rfp_detail(self, organization_id=None, user_id=None, rfp_id=None):
        """
        Get a single RFP using its public ID.
        Using v2 of the API which allows for custom fields such as copySplit.

        https://developer.mediaocean.com/docs/read/seller_proposals/Get_RFP_details
        """
        if rfp_id is None:
            raise PATSException("RFP ID is required")
        if user_id == None:
            user_id = self.user_id
        if organization_id is None:
            organization_id = self.vendor_id
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.rfp-v2+json',
            'X-MO-Organization-ID': organization_id,
            'X-MO-User-Id': user_id,
            'X-MO-App': 'pats'
        }
        js = self._send_request(
            "GET",
            PUBLISHER_API_DOMAIN,
            "/rfps/%s" % rfp_id,
            extra_headers
        )
        return js

    def get_rfp_attachment(self, organization_id=None, user_id=None, rfp_id=None, attachment_id=None):
        """
        Retrieve an attachment to an RFP based on its ID.
        Uses v2 of the API which allows for custom fields such as copySplit.

        https://developer.mediaocean.com/docs/read/seller_proposals/Get_RFP_attachment
        """
        if rfp_id == None:
            raise PATSException("RFP ID is required")
        if attachment_id == None:
            raise PATSException("Attachment ID is required")
        if user_id == None:
            user_id = self.user_id
        if organization_id is None:
            organization_id = self.vendor_id
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.rfp-v2+json',
            'X-MO-Organization-ID': organization_id,
            'X-MO-User-Id': user_id,
            'X-MO-App': 'pats'
        }

        js = self._send_request(
            "GET",
            PUBLISHER_API_DOMAIN,
            "/rfps/%s/attachments/%s" % (rfp_id, attachment_id),
            extra_headers
        )
        return js

    def send_proposal(self, user_id=None, rfp_id=None, proposal_id=None, proposal_external_id=None,
        currency_code=None, proposal_comments=None,
        author_name=None, agency_user_email=None, agency_id=None, advertiser_name=None,
        digital_line_items=None, print_line_items=None, attachments=None
        ):
        """
        As a seller, send a proposal in response to a buyer's RFP.

        rfp_id: ID of the RFP you are responding to (can be None for a seller-initiated proposal)
        proposal_id (optional): Will treat this action as "re-sending" a new version of an existing proposal
        proposal_external_id: A new, unique ID to assign to the proposal
        proposal_comments: A text message sent to the buyer along with the proposal
        digital_line_items: Digital line items to be sent as part of proposal
        print_line_items: Print line items to be sent as part of proposal
        (Note that unlike orders, proposals can have both print and digital line items)
        attachments (optional): Data for any files to be attached to the proposal

        https://developer.mediaocean.com/docs/read/seller_proposals/Send_proposal
        https://developer.mediaocean.com/docs/read/seller_proposals/Send_seller_initiated_proposal
        https://developer.mediaocean.com/docs/read/seller_proposals/Revise_proposal
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
            "externalId": proposal_external_id,
            "vendorId": self.vendor_id,
            "authorName": author_name,
            "comments" : proposal_comments,
            "digitalLineItems": digital_line_items_obj,
            "printLineItems": print_line_items_obj,
            "agencyUserEmail": agency_user_email,
            "agencyId": agency_id,
            "advertiserName": advertiser_name,
            "campaignId": None,
            "attachments" : attachments
        }
        if currency_code:
            data.update({
                "currencyCode" : currency_code,
            })

        return self.send_proposal_raw(user_id=user_id, vendor_id=self.vendor_id, rfp_id=rfp_id, proposal_id=proposal_id, data=data)

    def send_proposal_raw(self, user_id=None, vendor_id=None, rfp_id=None, proposal_id=None, data=None):
        """
        As a seller, send a proposal in response to a buyer's RFP using a raw payload
        Used directly by API tester app.

        rfp_id: ID of the RFP you are responding to
        proposal_id (optional): Will treat this action as "re-sending" a new version of an existing proposal

        https://developer.mediaocean.com/docs/read/seller_proposals/Send_proposal
        https://developer.mediaocean.com/docs/read/seller_proposals/Revise_proposal
        """
        if user_id == None:
            user_id = self.user_id
        if vendor_id == None:
            raise PATSException("Vendor (aka publisher) ID is required")
        #if rfp_id == None and proposal_id == None:
        #    raise PATSException("Either RFP ID (for a new proposal) or Proposal ID (for a proposal revision) is required")
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.proposal-v2+json',
            'X-MO-Organization-Id': vendor_id,
            'X-MO-User-Id': user_id,
            'X-MO-App': 'pats'
        }

        path = ''
        if proposal_id:
            path = "/proposals/%s" % proposal_id
        elif rfp_id:
            path = "/rfps/%s/proposals" % rfp_id
        else:
            # seller-initiated proposal
            path = "/proposals"

        proposal_uri = self._send_request(
            "PUT" if proposal_id else "POST",
            PUBLISHER_API_DOMAIN,
            path,
            extra_headers,
            json.dumps(data)
        )

        match = re.search('https?://(.+)?/proposals/(.+?)$', proposal_uri)
        new_proposal_id = None
        if match:
            new_proposal_id = match.group(2)
        if proposal_id and not new_proposal_id:
            new_proposal_id = proposal_id
        return new_proposal_id

    def view_proposal_detail(self, organization_id=None, user_id=None, proposal_id=None):
        """
        Get a single proposal using its public ID.
        Uses v2 of the API which allows custom fields such as copySplit.

        https://developer.mediaocean.com/docs/read/seller_proposals/Get_proposal_details
        """
        if proposal_id is None:
            raise PATSException("Proposal ID is required")
        if user_id == None:
            user_id = self.user_id
        if organization_id is None:
            organization_id = self.vendor_id
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.proposal-v2+json',
            'X-MO-Organization-ID': organization_id,
            'X-MO-User-Id': user_id,
            'X-MO-App': 'pats'
        }
        js = self._send_request(
            "GET",
            PUBLISHER_API_DOMAIN,
            "/proposals/%s" % proposal_id,
            extra_headers
        )
        return js

    def get_proposal_attachment(self, user_id=None, vendor_id=None, proposal_id=None, attachment_id=None):
        """
        Get contents of proposal attachment based on the proposal ID.
        Uses v2 of the API which allows custom fields such as copySplit.

        https://developer.mediaocean.com/docs/read/seller_proposals/Get_proposal_attachment
        """
        if user_id is None:
            user_id = self.user_id
        if vendor_id is None:
            vendor_id = self.vendor_id
        if proposal_id is None:
            raise PATSException("Proposal ID is required")
        if attachment_id is None:
            raise PATSException("Attachment ID is required")
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.proposal-v2+json',
            'X-MO-Organization-ID': vendor_id,
            'X-MO-User-Id': user_id,
            'X-MO-App': 'pats'
        }
        js = self._send_request(
            "GET",
            PUBLISHER_API_DOMAIN,
            "/proposals/%s/attachments/%s" % (proposal_id, attachment_id),
            extra_headers
        )
        return js

